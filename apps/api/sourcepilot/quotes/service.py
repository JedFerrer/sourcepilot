"""Internal quote creation with project-candidate eligibility checks."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from sourcepilot.persistence.models import Project, ProjectSupplier, Quote
from sourcepilot.quotes.domain import QuoteEntryType, QuoteStatus


class QuoteCandidateNotShortlistedError(ValueError):
    """The supplier is not currently shortlisted for this project."""


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
