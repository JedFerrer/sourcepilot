"""Quote creation and the initial manual review lifecycle."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, object_session, selectinload

from sourcepilot.persistence.models import (
    DocumentBlock,
    Project,
    ProjectSupplier,
    Quote,
    QuoteDocument,
    QuoteFieldEvidence,
    QuoteValue,
)
from sourcepilot.quotes.domain import (
    QUOTE_FIELD_KEYS,
    QuoteEntryType,
    QuoteStatus,
    QuoteValueOrigin,
    validate_quote_value_provenance,
)
from sourcepilot.quotes.schemas import (
    QuoteConflictResponse,
    QuoteEvidenceResponse,
    QuoteFieldResponse,
    QuoteProcessingResponse,
    QuoteResponse,
)


class QuoteCandidateNotShortlistedError(ValueError):
    """The supplier is not currently shortlisted for this project."""


class QuoteWorkflowError(ValueError):
    """A manual quote operation is unavailable in its current state."""


def create_quote(
    database_session: Session, *, project_id: UUID, supplier_id: UUID,
    entry_type: QuoteEntryType, status: QuoteStatus = QuoteStatus.NEEDS_REVIEW,
    notes: str | None = None,
) -> Quote:
    """Create a quote for a shortlisted candidate without applying a stage guard."""
    project = database_session.scalars(
        select(Project).where(Project.id == project_id).with_for_update()
    ).one_or_none()
    if project is None:
        raise QuoteCandidateNotShortlistedError("Project candidate does not exist.")
    candidate = database_session.get(ProjectSupplier, (project_id, supplier_id))
    if candidate is None or not candidate.shortlisted or candidate.dismissed:
        raise QuoteCandidateNotShortlistedError("Supplier is not shortlisted for this project.")
    quote = Quote(
        project_id=project_id, supplier_id=supplier_id, entry_type=entry_type.value,
        status=status.value, notes=notes,
    )
    database_session.add(quote)
    database_session.flush()
    return quote


def quote_snapshots(database_session: Session, quotes: Sequence[Quote]) -> list[QuoteResponse]:
    """Load PDF citations across quotes in bounded queries before serializing them."""
    pdf_quotes = [quote for quote in quotes if quote.entry_type == QuoteEntryType.PDF]
    documents = (database_session.scalars(
        select(QuoteDocument).where(QuoteDocument.quote_id.in_([quote.id for quote in pdf_quotes]))
    ).all() if pdf_quotes else [])
    documents_by_quote: dict[UUID, list[QuoteDocument]] = {}
    for document in documents:
        documents_by_quote.setdefault(document.quote_id, []).append(document)
    pdf_values = [value for quote in pdf_quotes for value in quote.values]
    associations = (database_session.scalars(
        select(QuoteFieldEvidence).where(
            QuoteFieldEvidence.quote_value_id.in_([value.id for value in pdf_values])
        )
    ).all() if pdf_values else [])
    blocks = (database_session.scalars(
        select(DocumentBlock).where(
            DocumentBlock.id.in_({item.document_block_id for item in associations})
        )
    ).all() if associations else [])
    blocks_by_id = {block.id: block for block in blocks}
    evidence_by_value: dict[UUID, list[QuoteFieldEvidence]] = {}
    for association in associations:
        evidence_by_value.setdefault(association.quote_value_id, []).append(association)

    def snapshot(quote: Quote) -> QuoteResponse:
        quote_documents = documents_by_quote.get(quote.id, [])
        document_ids = {document.id for document in quote_documents}
        evidence_captured = any(document.evidence_capture_version is not None
                                for document in quote_documents)

        def field_snapshot(value: QuoteValue) -> QuoteFieldResponse:
            evidence: list[QuoteEvidenceResponse] = []
            for association in sorted(
                evidence_by_value.get(value.id, []),
                key=lambda item: (blocks_by_id[item.document_block_id].page_number,
                                  blocks_by_id[item.document_block_id].block_number,
                                  str(item.evidence_value)),
            ):
                block = blocks_by_id[association.document_block_id]
                if block.quote_document_id not in document_ids:
                    raise ValueError("Quote evidence belongs to another document.")
                evidence.append(QuoteEvidenceResponse(
                    block_id=f"p{block.page_number}-b{block.block_number}",
                    page=block.page_number, block_text=block.text,
                    evidence_value=association.evidence_value,
                ))
            groups: list[QuoteConflictResponse] = []
            if value.ai_extracted_value is None:
                for item in evidence:
                    if item.evidence_value is None:
                        continue
                    group = next((candidate for candidate in groups
                                  if type(candidate.value) is type(item.evidence_value)
                                  and candidate.value == item.evidence_value), None)
                    if group is None:
                        groups.append(QuoteConflictResponse(value=item.evidence_value, evidence=[item]))
                    else:
                        group.evidence.append(item)
            review_state = (
                "CONFLICT" if len(groups) >= 2 else
                "KNOWN" if value.ai_extracted_value is not None else
                "UNAVAILABLE" if quote.entry_type == QuoteEntryType.PDF
                and not evidence_captured and not evidence else
                "UNKNOWN"
            )
            return QuoteFieldResponse(
                current_value=value.current_value, current_origin=value.current_origin,
                ai_extracted_value=value.ai_extracted_value, uncertainty=value.uncertainty,
                review_state=review_state,
                evidence=evidence, conflicting_values=groups if len(groups) >= 2 else [],
            )

        return QuoteResponse(
            id=quote.id, project_id=quote.project_id, supplier_id=quote.supplier_id,
            entry_type=quote.entry_type, status=quote.status, revision=quote.revision,
            confirmed_at=quote.confirmed_at, notes=quote.notes,
            values={value.field_key: field_snapshot(value) for value in quote.values},
            processing=(QuoteProcessingResponse(
                status=quote_documents[0].processing_status,
                attempts=quote_documents[0].processing_attempts,
                started_at=quote_documents[0].processing_started_at,
                completed_at=quote_documents[0].processing_completed_at,
                failure="PROCESSING_FAILED" if quote_documents[0].processing_status == "FAILED" else None,
            ) if quote.entry_type == QuoteEntryType.PDF and quote_documents else None),
        )

    return [snapshot(quote) for quote in quotes]


def quote_snapshot(quote: Quote) -> QuoteResponse:
    """Expose current values without treating a draft as confirmed evidence."""
    database_session = object_session(quote)
    if database_session is None:
        raise ValueError("Quote must be attached to a session.")
    return quote_snapshots(database_session, [quote])[0]


def list_quotes(database_session: Session, project_id: UUID) -> list[QuoteResponse]:
    quotes = database_session.scalars(
        select(Quote).where(Quote.project_id == project_id).order_by(Quote.created_at, Quote.id)
        .options(selectinload(Quote.values))
    ).all()
    return quote_snapshots(database_session, quotes)


def _require_quotes_stage(project: Project) -> None:
    if project.stage != "QUOTES":
        raise QuoteWorkflowError("Approve the shortlist before working with quotes.")


def _require_shortlisted(database_session: Session, quote: Quote) -> None:
    candidate = database_session.get(ProjectSupplier, (quote.project_id, quote.supplier_id))
    if candidate is None or not candidate.shortlisted or candidate.dismissed:
        raise QuoteWorkflowError("Supplier is not currently shortlisted for this project.")


def create_manual_quote(
    database_session: Session, project: Project, supplier_id: UUID,
    values: dict[str, object | None], notes: str | None,
) -> QuoteResponse:
    locked_project = database_session.scalars(
        select(Project).where(Project.id == project.id).with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    _require_quotes_stage(locked_project)
    if database_session.scalar(select(Quote.id).where(
        Quote.project_id == project.id, Quote.supplier_id == supplier_id,
    )) is not None:
        raise QuoteWorkflowError("A quote already exists for this supplier.")
    quote = create_quote(
        database_session, project_id=project.id, supplier_id=supplier_id,
        entry_type=QuoteEntryType.MANUAL, notes=notes,
    )
    for key in sorted(QUOTE_FIELD_KEYS):
        value = values.get(key)
        validate_quote_value_provenance(
            field_key=key, current_value=value,
            current_origin=QuoteValueOrigin.USER_ENTERED, ai_extracted_value=None,
        )
        quote.values.append(QuoteValue(
            field_key=key, current_value=value,
            current_origin=QuoteValueOrigin.USER_ENTERED.value, ai_extracted_value=None,
        ))
    database_session.flush()
    return quote_snapshot(quote)


def edit_manual_quote(
    database_session: Session, quote: Quote, values: dict[str, object | None],
    *, notes_provided: bool, notes: str | None,
) -> QuoteResponse:
    project = database_session.scalars(
        select(Project).where(Project.id == quote.project_id).with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    _require_quotes_stage(project)
    _require_shortlisted(database_session, quote)
    if quote.entry_type != QuoteEntryType.MANUAL or quote.status != QuoteStatus.NEEDS_REVIEW:
        raise QuoteWorkflowError("Only manual quotes awaiting review can be edited.")
    by_key = {value.field_key: value for value in quote.values}
    for key, current in values.items():
        validate_quote_value_provenance(
            field_key=key, current_value=current,
            current_origin=QuoteValueOrigin.USER_ENTERED, ai_extracted_value=None,
        )
        record = by_key.get(key)
        if record is None:
            record = QuoteValue(
                field_key=key, current_value=current,
                current_origin=QuoteValueOrigin.USER_ENTERED.value,
            )
            quote.values.append(record)
        else:
            record.current_value = current
    if notes_provided:
        quote.notes = notes
    database_session.flush()
    return quote_snapshot(quote)


def edit_pdf_quote(
    database_session: Session, quote: Quote, values: dict[str, object | None],
    *, notes_provided: bool, notes: str | None,
) -> QuoteResponse:
    """Correct only a PDF draft's current facts; original extraction stays intact."""
    project = database_session.scalars(
        select(Project).where(Project.id == quote.project_id).with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    _require_quotes_stage(project)
    _require_shortlisted(database_session, quote)
    if quote.entry_type != QuoteEntryType.PDF or quote.status != QuoteStatus.NEEDS_REVIEW:
        raise QuoteWorkflowError("Only PDF quotes awaiting review can be corrected.")
    by_key = {value.field_key: value for value in quote.values}
    for key, current in values.items():
        record = by_key.get(key)
        if record is None:
            raise QuoteWorkflowError("PDF draft is missing a normalized field.")
        origin = (QuoteValueOrigin.AI_EXTRACTED if current == record.ai_extracted_value
                  else QuoteValueOrigin.USER_CORRECTED)
        validate_quote_value_provenance(
            field_key=key, current_value=current, current_origin=origin,
            ai_extracted_value=record.ai_extracted_value,
        )
        record.current_value = current
        record.current_origin = origin.value
    if notes_provided:
        quote.notes = notes
    database_session.flush()
    return quote_snapshot(quote)


def confirm_manual_quote(database_session: Session, quote: Quote) -> QuoteResponse:
    project = database_session.scalars(
        select(Project).where(Project.id == quote.project_id).with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    _require_quotes_stage(project)
    _require_shortlisted(database_session, quote)
    if quote.entry_type != QuoteEntryType.MANUAL or quote.status != QuoteStatus.NEEDS_REVIEW:
        raise QuoteWorkflowError("Only manual quotes awaiting review can be confirmed.")
    quote.status = QuoteStatus.CONFIRMED.value
    quote.confirmed_at = datetime.now(UTC)
    database_session.flush()
    return quote_snapshot(quote)
