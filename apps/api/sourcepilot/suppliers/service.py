"""Approved-Brief supplier discovery use case."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from sourcepilot.briefs.domain import BriefStatus
from sourcepilot.briefs.workflow import project_requirements
from sourcepilot.persistence.models import Brief, Project
from sourcepilot.suppliers.repository import suppliers_in_category
from sourcepilot.suppliers.retrieval import (
    RetrievalRequirement,
    candidate_facts,
    normalize_category,
    order_candidates,
)
from sourcepilot.suppliers.schemas import (
    CandidateCapabilityResponse,
    DiscoverSuppliersResponse,
    SupplierCandidateResponse,
)


class DiscoveryNotReadyError(ValueError):
    pass


def discover_suppliers(
    database_session: Session, *, project_id: UUID
) -> DiscoverSuppliersResponse:
    """Select current catalog candidates for a locked, approved project Brief."""
    project = database_session.scalars(
        select(Project)
        .where(Project.id == project_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    brief = database_session.get(Brief, project.id)
    if (
        brief is None
        or brief.status != BriefStatus.APPROVED
        or brief.category is None
        or brief.quantity is None
    ):
        raise DiscoveryNotReadyError("Approve the Brief before discovering suppliers.")

    requirements = project_requirements(database_session, project.id)
    suppliers = suppliers_in_category(database_session, normalize_category(brief.category))
    ordered_ids = order_candidates(
        [
            candidate_facts(
                supplier.id,
                supplier.name,
                supplier.general_moq,
                [(item.capability_kind, item.value) for item in supplier.capabilities],
            )
            for supplier in suppliers
        ],
        requirements=[
            RetrievalRequirement(item.kind, item.expected_value) for item in requirements
        ],
        quantity=brief.quantity,
    )
    by_id = {supplier.id: supplier for supplier in suppliers}
    return DiscoverSuppliersResponse(
        brief_revision=project.brief_revision,
        suppliers=[
            SupplierCandidateResponse(
                id=by_id[supplier_id].id,
                name=by_id[supplier_id].name,
                country=by_id[supplier_id].country,
                description=by_id[supplier_id].description,
                capabilities=[
                    CandidateCapabilityResponse(kind=item.capability_kind, value=item.value)
                    for item in by_id[supplier_id].capabilities
                ],
                general_moq=by_id[supplier_id].general_moq,
                general_lead_time_days=by_id[supplier_id].general_lead_time_days,
                indicative_price_amount=(
                    str(by_id[supplier_id].indicative_price_amount)
                    if by_id[supplier_id].indicative_price_amount is not None
                    else None
                ),
                indicative_price_currency=by_id[supplier_id].indicative_price_currency,
            )
            for supplier_id in ordered_ids
        ],
    )
