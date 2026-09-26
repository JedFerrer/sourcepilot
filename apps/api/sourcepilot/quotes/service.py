"""Quote creation and the initial manual review lifecycle."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from sourcepilot.persistence.models import Project, ProjectSupplier, Quote, QuoteValue
from sourcepilot.quotes.domain import (
    QUOTE_FIELD_KEYS,
    QuoteEntryType,
    QuoteStatus,
    QuoteValueOrigin,
    validate_quote_value_provenance,
)
from sourcepilot.quotes.schemas import QuoteFieldResponse, QuoteResponse


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


def quote_snapshot(quote: Quote) -> QuoteResponse:
    """Expose current values without treating a draft as confirmed evidence."""
    return QuoteResponse(
        id=quote.id, project_id=quote.project_id, supplier_id=quote.supplier_id,
        entry_type=quote.entry_type, status=quote.status, revision=quote.revision,
        confirmed_at=quote.confirmed_at, notes=quote.notes,
        values={value.field_key: QuoteFieldResponse(
            current_value=value.current_value, current_origin=value.current_origin,
            ai_extracted_value=value.ai_extracted_value,
        ) for value in quote.values},
    )


def list_quotes(database_session: Session, project_id: UUID) -> list[QuoteResponse]:
    quotes = database_session.scalars(
        select(Quote).where(Quote.project_id == project_id).order_by(Quote.created_at, Quote.id)
    ).all()
    return [quote_snapshot(quote) for quote in quotes]


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
