"""One initial, lightweight background attempt for a stored PDF quote."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
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


def _current_attempt(session: Session, document_id: UUID) -> tuple[UUID, DemoSession, int] | None:
    document = session.get(QuoteDocument, document_id)
    if document is None or document.processing_status != "PROCESSING":
        return None
    quote = session.get(Quote, document.quote_id)
    if quote is None or quote.status != "PROCESSING":
        return None
    project = session.get(Project, quote.project_id)
    if project is None:
        return None
    owner = session.get(DemoSession, project.demo_session_id)
    if owner is None:
        return None
    return quote.id, owner, document.processing_attempts


def _finish_success(
    session_factory: Callable[[], Session], document_id: UUID, attempt: int,
    extraction: QuoteExtraction,
) -> None:
    with session_factory() as session, session.begin():
        document = session.scalar(select(QuoteDocument).where(QuoteDocument.id == document_id)
                                  .with_for_update().execution_options(populate_existing=True))
        if document is None or document.processing_status != "PROCESSING" or document.processing_attempts != attempt:
            return
        quote = session.scalar(select(Quote).where(Quote.id == document.quote_id)
                               .with_for_update().execution_options(populate_existing=True))
        if quote is None or quote.status != "PROCESSING":
            return
        if quote.values:
            raise ValueError("PDF draft already contains quote values.")
        blocks = session.scalars(
            select(DocumentBlock).where(DocumentBlock.quote_document_id == document.id)
        ).all()
        block_by_reference = {
            f"p{block.page_number}-b{block.block_number}": block for block in blocks
        }
        if not block_by_reference:
            raise ValueError("PDF draft has no validated document blocks.")
        validate_source_references(extraction, set(block_by_reference))
        for key in sorted(QUOTE_FIELD_KEYS):
            field = getattr(extraction.fields, key)
            value = field.extracted_value if field.state == "KNOWN" else None
            validate_quote_value_provenance(
                field_key=key, current_value=value,
                current_origin=QuoteValueOrigin.AI_EXTRACTED, ai_extracted_value=value,
            )
            record = QuoteValue(
                field_key=key, current_value=value,
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
            quote.values.append(record)
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
        document = session.scalar(select(QuoteDocument).where(QuoteDocument.id == document_id)
                                  .with_for_update().execution_options(populate_existing=True))
        if document is None or document.processing_status != "PROCESSING" or document.processing_attempts != attempt:
            return
        quote = session.scalar(select(Quote).where(Quote.id == document.quote_id)
                               .with_for_update().execution_options(populate_existing=True))
        if quote is None or quote.status != "PROCESSING":
            return
        quote.status = "FAILED"
        document.processing_status = "FAILED"
        document.processing_completed_at = datetime.now(UTC)
        document.last_error = failure


def process_pdf_quote(
    document_id: UUID, *, session_factory: Callable[[], Session],
    storage: DocumentStorage, settings: DocumentSettings,
    client_factory: Callable[[], StructuredModelClient],
) -> None:
    """Process one committed attempt; failures never leave partial draft values."""
    with session_factory() as session:
        current = _current_attempt(session, document_id)
    if current is None:
        return
    _, owner, attempt = current
    try:
        parse_and_persist_document(session_factory, document_id, storage=storage, settings=settings)
        with session_factory() as session:
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


def run_pdf_quote_processing(document_id: UUID) -> None:
    """Production background entry point; the task argument is only an ID."""
    factory = application_session_factory()
    try:
        settings = document_settings_from_environment()
        storage = storage_from_settings(settings)
    except Exception as error:  # noqa: BLE001 - configuration failures need terminal state too
        logger.warning("PDF quote processing setup failed for document %s (%s)", document_id, type(error).__name__)
        with factory() as session:
            current = _current_attempt(session, document_id)
        if current is not None:
            _finish_failure(factory, document_id, current[2], "PROCESSING_FAILED")
        return
    process_pdf_quote(
        document_id, session_factory=factory,
        storage=storage, settings=settings,
        client_factory=OpenAIResponsesClient.from_environment,
    )
