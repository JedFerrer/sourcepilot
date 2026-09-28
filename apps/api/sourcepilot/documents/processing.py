"""Guarded lightweight background attempts for stored PDF quotes."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, event, select
from sqlalchemy.orm import Session

from sourcepilot.ai.client import OpenAIResponsesClient, StructuredModelClient
from sourcepilot.ai.quote_extractor import (
    QuoteExtraction,
    extract_quote_document,
    validate_source_references,
)
from sourcepilot.documents.parse_service import parse_and_persist_document
from sourcepilot.documents.settings import DocumentSettings, document_settings_from_environment
from sourcepilot.documents.storage import DocumentStorage, storage_from_settings
from sourcepilot.persistence.database import application_session_factory
from sourcepilot.persistence.models import (
    DemoSession,
    DocumentBlock,
    Project,
    Quote,
    QuoteDocument,
    QuoteFieldEvidence,
    QuoteValue,
)
from sourcepilot.quotes.domain import (
    QUOTE_FIELD_KEYS,
    QuoteValueOrigin,
    validate_quote_value_provenance,
)

logger = logging.getLogger(__name__)


def _current_attempt(session: Session, document_id: UUID, attempt: int) -> DemoSession | None:
    document = session.get(QuoteDocument, document_id)
    if (document is None or not document.is_active or document.processing_status != "PROCESSING"
            or document.processing_attempts != attempt):
        return None
    quote = session.get(Quote, document.quote_id)
    if quote is None or quote.entry_type != "PDF" or quote.status != "PROCESSING":
        return None
    project = session.get(Project, quote.project_id)
    if project is None:
        return None
    owner = session.get(DemoSession, project.demo_session_id)
    if owner is None:
        return None
    return owner


def _locked_active_attempt(
    session: Session, document_id: UUID, attempt: int,
) -> tuple[Quote, QuoteDocument] | None:
    identity = session.get(QuoteDocument, document_id)
    if identity is None:
        return None
    quote = session.scalar(select(Quote).where(Quote.id == identity.quote_id)
                           .with_for_update().execution_options(populate_existing=True))
    if quote is None or quote.entry_type != "PDF" or quote.status != "PROCESSING":
        return None
    document = session.scalar(select(QuoteDocument).where(QuoteDocument.id == document_id)
                              .with_for_update().execution_options(populate_existing=True))
    if (document is None or document.quote_id != quote.id or not document.is_active
            or document.processing_status != "PROCESSING"
            or document.processing_attempts != attempt):
        return None
    return quote, document


def _finish_success(
    session_factory: Callable[[], Session], document_id: UUID, attempt: int,
    extraction: QuoteExtraction,
) -> None:
    with session_factory() as session, session.begin():
        current = _locked_active_attempt(session, document_id, attempt)
        if current is None:
            return
        quote, document = current
        blocks = session.scalars(
            select(DocumentBlock).where(DocumentBlock.quote_document_id == document.id)
        ).all()
        block_by_reference = {
            f"p{block.page_number}-b{block.block_number}": block for block in blocks
        }
        if not block_by_reference:
            raise ValueError("PDF draft has no validated document blocks.")
        validate_source_references(extraction, set(block_by_reference))
        session.execute(delete(QuoteValue).where(QuoteValue.quote_id == quote.id))
        session.flush()
        for key in sorted(QUOTE_FIELD_KEYS):
            field = getattr(extraction.fields, key)
            value = field.extracted_value if field.state == "KNOWN" else None
            validate_quote_value_provenance(
                field_key=key, current_value=value,
                current_origin=QuoteValueOrigin.AI_EXTRACTED, ai_extracted_value=value,
            )
            record = QuoteValue(
                quote_id=quote.id, field_key=key, current_value=value,
                ai_extracted_value=value, current_origin=QuoteValueOrigin.AI_EXTRACTED.value,
                uncertainty=field.uncertainty,
            )
            associations = (
                [(reference, field.extracted_value) for reference in field.source_block_ids]
                if field.state == "KNOWN" else
                [(reference, alternative.value)
                 for alternative in field.conflicting_values
                 for reference in alternative.source_block_ids]
                if field.state == "CONFLICT" else
                [(reference, None) for reference in field.source_block_ids]
            )
            for reference, evidence_value in associations:
                block = block_by_reference[reference]
                if block.quote_document_id != document.id or document.quote_id != quote.id:
                    raise ValueError("Quote evidence belongs to another document or quote.")
                record.evidence.append(QuoteFieldEvidence(
                    block=block, evidence_value=evidence_value,
                ))
            session.add(record)
        completed_at = datetime.now(UTC)
        quote.status = "NEEDS_REVIEW"
        document.processing_status = "NEEDS_REVIEW"
        document.processing_completed_at = completed_at
        document.evidence_capture_version = 1
        document.last_error = None
        session.flush()


def _finish_failure(
    session_factory: Callable[[], Session], document_id: UUID, attempt: int,
    failure: str,
) -> None:
    with session_factory() as session, session.begin():
        current = _locked_active_attempt(session, document_id, attempt)
        if current is None:
            return
        quote, document = current
        quote.status = "FAILED"
        document.processing_status = "FAILED"
        document.processing_completed_at = datetime.now(UTC)
        document.last_error = failure


def process_pdf_quote(
    document_id: UUID, attempt: int, *, session_factory: Callable[[], Session],
    storage: DocumentStorage, settings: DocumentSettings,
    client_factory: Callable[[], StructuredModelClient],
) -> None:
    """Process one committed attempt; failures never leave partial draft values."""
    with session_factory() as session:
        owner = _current_attempt(session, document_id, attempt)
    if owner is None:
        return
    try:
        parse_and_persist_document(
            session_factory, document_id, storage=storage, settings=settings,
            expected_attempt=attempt,
        )
        with session_factory() as session:
            if _current_attempt(session, document_id, attempt) is None:
                return
            # Structured extraction commits its AIRun several times. Guard each
            # commit in that transaction, including completion after model work.
            def guard_trace_write(active_session: Session) -> None:
                with active_session.no_autoflush:
                    if _locked_active_attempt(active_session, document_id, attempt) is None:
                        raise StalePdfAttemptError("PDF attempt was superseded.")

            event.listen(session, "before_commit", guard_trace_write)
            extraction, _ = extract_quote_document(
                session, demo_session=owner, document_id=document_id, client=client_factory(),
            )
        if extraction is None:
            raise ValueError("Quote extraction did not produce a valid draft.")
        _finish_success(session_factory, document_id, attempt, extraction)
    except Exception as error:  # noqa: BLE001 - background failures must become durable FAILED state
        logger.warning("PDF quote processing failed for document %s (%s)", document_id, type(error).__name__)
        try:
            _finish_failure(session_factory, document_id, attempt, "PROCESSING_FAILED")
        except Exception:
            logger.exception("Could not persist failed PDF quote processing for document %s", document_id)


class StalePdfAttemptError(RuntimeError):
    """A queued or running worker no longer owns the PDF attempt."""


def run_pdf_quote_processing(document_id: UUID, attempt: int) -> None:
    """Production background entry point for one immutable document attempt."""
    factory = application_session_factory()
    try:
        settings = document_settings_from_environment()
        storage = storage_from_settings(settings)
    except Exception as error:  # noqa: BLE001 - configuration failures need terminal state too
        logger.warning("PDF quote processing setup failed for document %s (%s)", document_id, type(error).__name__)
        _finish_failure(factory, document_id, attempt, "PROCESSING_FAILED")
        return
    process_pdf_quote(
        document_id, attempt, session_factory=factory,
        storage=storage, settings=settings,
        client_factory=OpenAIResponsesClient.from_environment,
    )
