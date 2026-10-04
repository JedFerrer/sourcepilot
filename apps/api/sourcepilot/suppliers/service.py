"""Approved-Brief supplier discovery use case."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from sourcepilot.briefs.domain import BriefStatus, RequirementKind
from sourcepilot.briefs.workflow import project_requirements
from sourcepilot.comparison.service import mark_comparisons_stale
from sourcepilot.persistence.models import (
    Brief,
    Project,
    ProjectSupplier,
    Quote,
    RequirementEvaluationRecord,
    Supplier,
)
from sourcepilot.quotes.domain import QuoteStatus
from sourcepilot.suppliers.evaluation import (
    EvaluationEvidence,
    EvaluationRequirement,
    SupplierEvaluationFacts,
    evaluate_supplier,
)
from sourcepilot.suppliers.repository import suppliers_in_category
from sourcepilot.suppliers.retrieval import (
    RetrievalRequirement,
    candidate_facts,
    normalize_category,
    order_candidates,
)
from sourcepilot.suppliers.schemas import (
    CandidateCapabilityResponse,
    DerivedContextResponse,
    DiscoverSuppliersResponse,
    InformationalRequirementResponse,
    RequirementEvaluationResponse,
    ReviewedSupplierResponse,
    SupplierCandidateResponse,
    SupplierEvidenceResponse,
    SupplierListResponse,
    UpdateSupplierReviewRequest,
)


class DiscoveryNotReadyError(ValueError):
    pass


class SupplierNotInProjectError(ValueError):
    pass


class ShortlistApprovalError(ValueError):
    pass


def supplier_evaluation_is_stale(evaluated_revision: int, brief_revision: int) -> bool:
    """Authoritative M2 freshness check; workflow summaries reuse it."""
    return evaluated_revision != brief_revision


def _candidate_response(supplier: Supplier) -> SupplierCandidateResponse:
    return SupplierCandidateResponse(
        id=supplier.id,
        name=supplier.name,
        country=supplier.country,
        description=supplier.description,
        capabilities=[
            CandidateCapabilityResponse(kind=item.capability_kind, value=item.value)
            for item in sorted(supplier.capabilities, key=lambda item: (item.capability_kind, item.value, str(item.id)))
        ],
        general_moq=supplier.general_moq,
        general_lead_time_days=supplier.general_lead_time_days,
        indicative_price_amount=(
            str(supplier.indicative_price_amount)
            if supplier.indicative_price_amount is not None else None
        ),
        indicative_price_currency=supplier.indicative_price_currency,
    )


def _evaluation_facts(supplier: Supplier) -> SupplierEvaluationFacts:
    return SupplierEvaluationFacts(
        capabilities=frozenset(
            (item.capability_kind, item.value) for item in supplier.capabilities
        ),
        general_moq=supplier.general_moq,
        evidence=tuple(
            EvaluationEvidence(item.id, item.claim_key, item.evidence_state)
            for item in supplier.evidence
        ),
    )


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
    existing = {
        item.supplier_id: item
        for item in database_session.scalars(
            select(ProjectSupplier).where(ProjectSupplier.project_id == project.id)
        )
    }
    removed_ids = {supplier_id for supplier_id, item in existing.items()
                   if item.shortlisted and supplier_id not in ordered_ids}
    removed_selected = bool(removed_ids)
    if removed_selected and project.stage == "QUOTES":
        project.stage = "SUPPLIERS"
    if removed_ids and database_session.scalar(select(Quote.id).where(
        Quote.project_id == project.id, Quote.supplier_id.in_(removed_ids),
        Quote.status == QuoteStatus.CONFIRMED.value,
    )) is not None:
        mark_comparisons_stale(database_session, project.id)
    for supplier_id, item in existing.items():
        if supplier_id not in ordered_ids:
            database_session.delete(item)
    database_session.flush()
    evaluation_requirements = [
        EvaluationRequirement(item.id, RequirementKind(item.kind), item.expected_value)
        for item in requirements
    ]
    for supplier_id in ordered_ids:
        supplier = by_id[supplier_id]
        item = existing.get(supplier_id)
        if item is None:
            item = ProjectSupplier(
                project_id=project.id,
                supplier_id=supplier_id,
                shortlisted=False,
                dismissed=False,
            )
            database_session.add(item)
        item.evaluated_against_brief_revision = project.brief_revision
        item.evaluations.clear()
        database_session.flush()
        evaluated = evaluate_supplier(
            evaluation_requirements,
            requested_quantity=brief.quantity,
            supplier=_evaluation_facts(supplier),
        )
        for result in evaluated.results:
            if result.requirement_id is None:
                continue
            evidence = [record for record in supplier.evidence if record.id in result.evidence_ids]
            source_types = {record.source_type for record in evidence}
            claim_keys = {record.claim_key for record in evidence}
            item.evaluations.append(
                RequirementEvaluationRecord(
                    requirement_id=result.requirement_id,
                    status=result.status.value,
                    resolved_source_type=next(iter(source_types)) if len(source_types) == 1 else None,
                    resolved_fact_reference=next(iter(claim_keys)) if len(claim_keys) == 1 else None,
                    evidence_ids=[str(value) for value in result.evidence_ids],
                )
            )
    database_session.flush()
    return DiscoverSuppliersResponse(
        brief_revision=project.brief_revision,
        suppliers=[_candidate_response(by_id[supplier_id]) for supplier_id in ordered_ids],
    )


def list_project_suppliers(database_session: Session, project: Project) -> SupplierListResponse:
    project = database_session.scalars(
        select(Project)
        .where(Project.id == project.id)
        .with_for_update(read=True)
        .execution_options(populate_existing=True)
    ).one()
    brief = database_session.get(Brief, project.id)
    requirements = {item.id: item for item in project_requirements(database_session, project.id)}
    rows = list(database_session.scalars(
        select(ProjectSupplier)
        .where(ProjectSupplier.project_id == project.id)
        .options(
            selectinload(ProjectSupplier.supplier).selectinload(Supplier.capabilities),
            selectinload(ProjectSupplier.supplier).selectinload(Supplier.evidence),
            selectinload(ProjectSupplier.evaluations),
        )
    ).all())
    rows.sort(key=lambda item: (item.supplier.name.casefold(), str(item.supplier_id)))
    reviewed: list[ReviewedSupplierResponse] = []
    for item in rows:
        supplier = item.supplier
        stale = supplier_evaluation_is_stale(item.evaluated_against_brief_revision, project.brief_revision)
        evaluations = []
        derived_context = []
        informational_requirements = []
        if not stale:
            for record in sorted(item.evaluations, key=lambda value: str(value.requirement_id)):
                requirement = requirements.get(record.requirement_id)
                if requirement is None:
                    continue
                evaluations.append(RequirementEvaluationResponse(
                    requirement_id=requirement.id,
                    kind=requirement.kind,
                    importance=requirement.importance,
                    expected_value=requirement.expected_value,
                    status=record.status,
                    evidence_ids=[UUID(value) for value in record.evidence_ids],
                ))
            informational_requirements = [
                InformationalRequirementResponse(
                    requirement_id=value.id,
                    kind=value.kind,
                    importance=value.importance,
                    expected_value=value.expected_value,
                ) for value in requirements.values()
                if value.kind not in {"MATERIAL", "CERTIFICATION", "MOQ", "CAPABILITY"}
            ]
            if brief is not None and brief.quantity is not None and not any(
                value.kind == "MOQ" for value in requirements.values()
            ):
                derived = evaluate_supplier(
                    [], requested_quantity=brief.quantity, supplier=_evaluation_facts(supplier)
                ).results[0]
                derived_context.append(DerivedContextResponse(
                    kind="MOQ", status=derived.status.value,
                    evidence_ids=list(derived.evidence_ids),
                ))
        reviewed.append(ReviewedSupplierResponse(
            **_candidate_response(supplier).model_dump(),
            shortlisted=item.shortlisted,
            dismissed=item.dismissed,
            notes=item.notes,
            evaluated_against_brief_revision=item.evaluated_against_brief_revision,
            stale=stale,
            evaluations=evaluations,
            derived_context=derived_context,
            informational_requirements=informational_requirements,
            evidence=[SupplierEvidenceResponse(
                id=value.id, claim_key=value.claim_key, source_type=value.source_type,
                source_label=value.source_label, source_reference=value.source_reference,
                evidence_text=value.evidence_text, evidence_state=value.evidence_state,
            ) for value in sorted(supplier.evidence, key=lambda value: (value.claim_key, value.source_label, str(value.id)))],
        ))
    return SupplierListResponse(
        brief_revision=project.brief_revision,
        brief_approved=brief is not None and brief.status == BriefStatus.APPROVED,
        shortlist_approved=project.stage == "QUOTES",
        suppliers=reviewed,
    )


def update_supplier_review(
    database_session: Session, project: Project, supplier_id: UUID,
    payload: UpdateSupplierReviewRequest,
) -> SupplierListResponse:
    locked_project = database_session.scalars(
        select(Project)
        .where(Project.id == project.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    item = database_session.get(ProjectSupplier, (project.id, supplier_id))
    if item is None:
        raise SupplierNotInProjectError("Supplier is not in this project candidate set.")
    was_shortlisted = item.shortlisted
    if "shortlisted" in payload.model_fields_set and payload.shortlisted is not None:
        item.shortlisted = payload.shortlisted
        if item.shortlisted:
            item.dismissed = False
    if "dismissed" in payload.model_fields_set and payload.dismissed is not None:
        item.dismissed = payload.dismissed
        if item.dismissed:
            item.shortlisted = False
    if "notes" in payload.model_fields_set:
        item.notes = payload.notes
    if was_shortlisted != item.shortlisted and locked_project.stage == "QUOTES":
        locked_project.stage = "SUPPLIERS"
    database_session.flush()
    if was_shortlisted != item.shortlisted and database_session.scalar(select(Quote.id).where(
        Quote.project_id == project.id, Quote.supplier_id == supplier_id,
        Quote.status == QuoteStatus.CONFIRMED.value,
    )) is not None:
        mark_comparisons_stale(database_session, project.id)
    return list_project_suppliers(database_session, project)


def approve_shortlist(database_session: Session, project: Project) -> SupplierListResponse:
    """Advance only a reviewed, current project shortlist through explicit approval."""
    locked_project = database_session.scalars(
        select(Project)
        .where(Project.id == project.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    brief = database_session.get(Brief, project.id)
    if brief is None or brief.status != BriefStatus.APPROVED:
        raise ShortlistApprovalError("Approve the Brief before approving a shortlist.")
    selected = list(database_session.scalars(
        select(ProjectSupplier).where(
            ProjectSupplier.project_id == project.id,
            ProjectSupplier.shortlisted.is_(True),
        )
    ))
    if not 1 <= len(selected) <= 3:
        raise ShortlistApprovalError("Select one to three suppliers before approval.")
    if any(item.dismissed for item in selected):
        raise ShortlistApprovalError("Restore dismissed suppliers before approval.")
    if any(supplier_evaluation_is_stale(item.evaluated_against_brief_revision, locked_project.brief_revision) for item in selected):
        raise ShortlistApprovalError("Re-discover and re-evaluate suppliers before approval.")
    locked_project.stage = "QUOTES"
    database_session.flush()
    return list_project_suppliers(database_session, locked_project)
