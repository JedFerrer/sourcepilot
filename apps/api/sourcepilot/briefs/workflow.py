"""Project-scoped Brief reading, analysis persistence, and manual editing."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from sourcepilot.ai.brief_interpreter import ExtractedBrief, interpret_project_request
from sourcepilot.ai.client import StructuredModelClient
from sourcepilot.briefs.domain import BriefStatus, RequirementImportance, RequirementKind
from sourcepilot.briefs.readiness import (
    ReadinessRequirement,
    evaluate_brief_readiness,
)
from sourcepilot.briefs.schemas import (
    AnalyzeBriefResponse,
    BriefResponse,
    EditBriefRequest,
    MissingFieldResponse,
    RequirementResponse,
)
from sourcepilot.briefs.service import increment_brief_revision, recalculate_brief_readiness
from sourcepilot.persistence.models import Brief, DemoSession, Project, Requirement


class BriefConflictError(ValueError):
    pass


class BriefEditError(ValueError):
    pass


class BriefAnalysisUnavailableError(RuntimeError):
    pass


def project_requirements(database_session: Session, project_id: UUID) -> list[Requirement]:
    return list(
        database_session.scalars(
            select(Requirement)
            .where(Requirement.project_id == project_id)
            .order_by(Requirement.id)
        )
    )


def meaningful_brief_content(
    *,
    product_name: str | None,
    category: str | None,
    quantity: int | None,
    destination: str | None,
    delivery_target: object,
    target_unit_price: object,
    requirements: Sequence[object],
) -> bool:
    """One content definition shared by Analyze and edit/revision decisions."""
    return any(
        (
            isinstance(value, str) and bool(value.strip())
            if field in {"product_name", "category", "destination"}
            else value is not None
        )
        for field, value in (
            ("product_name", product_name),
            ("category", category),
            ("quantity", quantity),
            ("destination", destination),
            ("delivery_target", delivery_target),
            ("target_unit_price", target_unit_price),
        )
    ) or bool(requirements)


def can_analyze(project: Project, brief: Brief | None, requirements: list[Requirement]) -> bool:
    return project.brief_revision == 0 and not meaningful_brief_content(
        product_name=brief.product_name if brief else None,
        category=brief.category if brief else None,
        quantity=brief.quantity if brief else None,
        destination=brief.destination if brief else None,
        delivery_target=brief.delivery_target if brief else None,
        target_unit_price=brief.target_unit_price if brief else None,
        requirements=requirements,
    )


def brief_snapshot(
    project: Project, brief: Brief | None, requirements: list[Requirement]
) -> BriefResponse:
    readiness = evaluate_brief_readiness(
        product_name=brief.product_name if brief else None,
        category=brief.category if brief else None,
        quantity=brief.quantity if brief else None,
        destination=brief.destination if brief else None,
        delivery_target=brief.delivery_target if brief else None,
        requirements=tuple(
            ReadinessRequirement(kind=item.kind, expected_value=item.expected_value)
            for item in requirements
        ),
    )
    return BriefResponse(
        product_name=brief.product_name if brief else None,
        category=brief.category if brief else None,
        quantity=brief.quantity if brief else None,
        destination=brief.destination if brief else None,
        delivery_target=brief.delivery_target if brief else None,
        target_unit_price=str(brief.target_unit_price) if brief and brief.target_unit_price else None,
        requirements=[
            RequirementResponse(
                id=item.id,
                kind=RequirementKind(item.kind),
                importance=RequirementImportance(item.importance) if item.importance else None,
                expected_value=item.expected_value,
                notes=item.notes,
            )
            for item in requirements
        ],
        status=brief.status if brief and brief.status == BriefStatus.APPROVED else readiness.status.value,
        missing_fields=[
            MissingFieldResponse(field_key=item.field_key, reason=item.reason)
            for item in readiness.missing_fields
        ],
        brief_revision=project.brief_revision,
        can_analyze=can_analyze(project, brief, requirements),
    )


def _brief_values(brief: Brief | None) -> tuple[object, ...]:
    if brief is None:
        return (None, None, None, None, None, None)
    return (
        brief.product_name,
        brief.category,
        brief.quantity,
        brief.destination,
        brief.delivery_target,
        brief.target_unit_price,
    )


def _requirement_values(item: Requirement) -> tuple[object, ...]:
    return (item.kind, item.importance, item.expected_value, item.notes)


def edit_brief(
    database_session: Session, project: Project, payload: EditBriefRequest
) -> BriefResponse:
    project = database_session.scalars(
        select(Project)
        .where(Project.id == project.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    brief = database_session.get(Brief, project.id)
    if brief is not None and brief.status == BriefStatus.APPROVED:
        raise BriefConflictError("Approved Brief editing belongs to a later workflow step.")
    existing = project_requirements(database_session, project.id)
    existing_by_id = {item.id: item for item in existing}
    seen_ids: set[UUID] = set()
    for item in payload.requirements:
        if item.id is not None:
            if item.id in seen_ids or item.id not in existing_by_id:
                raise BriefEditError("Requirement does not belong to this Brief or is repeated.")
            seen_ids.add(item.id)

    new_values = (
        payload.product_name,
        payload.category,
        payload.quantity,
        payload.destination,
        payload.delivery_target,
        Decimal(payload.target_unit_price) if payload.target_unit_price is not None else None,
    )
    before_meaningful = meaningful_brief_content(
        product_name=brief.product_name if brief else None,
        category=brief.category if brief else None,
        quantity=brief.quantity if brief else None,
        destination=brief.destination if brief else None,
        delivery_target=brief.delivery_target if brief else None,
        target_unit_price=brief.target_unit_price if brief else None,
        requirements=existing,
    )
    after_meaningful = meaningful_brief_content(
        product_name=payload.product_name,
        category=payload.category,
        quantity=payload.quantity,
        destination=payload.destination,
        delivery_target=payload.delivery_target,
        target_unit_price=payload.target_unit_price,
        requirements=payload.requirements,
    )
    changed = before_meaningful != after_meaningful or _brief_values(brief) != new_values
    if len(existing) != len(payload.requirements):
        changed = True
    for item in payload.requirements:
        if item.id is None:
            changed = True
        else:
            old = existing_by_id[item.id]
            if _requirement_values(old) != (
                item.kind.value,
                item.importance.value if item.importance else None,
                item.expected_value,
                item.notes,
            ):
                changed = True

    if not changed:
        return brief_snapshot(project, brief, existing)

    if brief is None:
        brief = Brief(project_id=project.id)
        database_session.add(brief)
    (
        brief.product_name,
        brief.category,
        brief.quantity,
        brief.destination,
        brief.delivery_target,
        brief.target_unit_price,
    ) = new_values
    for old in existing:
        if old.id not in seen_ids:
            database_session.delete(old)
    for item in payload.requirements:
        if item.id is None:
            database_session.add(
                Requirement(
                    project_id=project.id,
                    kind=item.kind.value,
                    importance=item.importance.value if item.importance else None,
                    expected_value=item.expected_value,
                    notes=item.notes,
                )
            )
        else:
            old = existing_by_id[item.id]
            old.kind = item.kind.value
            old.importance = item.importance.value if item.importance else None
            old.expected_value = item.expected_value
            old.notes = item.notes
    database_session.flush()
    current = project_requirements(database_session, project.id)
    recalculate_brief_readiness(database_session, brief, current)
    increment_brief_revision(database_session, project)
    return brief_snapshot(project, brief, current)


def persist_extraction(
    database_session: Session, project: Project, extracted: ExtractedBrief
) -> BriefResponse:
    brief = database_session.get(Brief, project.id)
    current = project_requirements(database_session, project.id)
    if not can_analyze(project, brief, current):
        raise BriefConflictError("This Brief already has saved content. Analyze cannot replace it.")
    mapped = [
        Requirement(
            project_id=project.id,
            kind=RequirementKind.INFORMATIONAL.value,
            importance=RequirementImportance.INFORMATIONAL.value,
            expected_value={"subject": item.subject.value, "text": item.text},
        )
        for item in extracted.attributes
    ] + [
        Requirement(
            project_id=project.id,
            kind=item.kind.value,
            importance=item.importance.value if item.importance else None,
            expected_value=item.expected_value.model_dump(exclude_none=True),
        )
        for item in extracted.requirements
    ]
    if not meaningful_brief_content(
        product_name=extracted.product_name,
        category=extracted.category,
        quantity=extracted.quantity,
        destination=extracted.destination,
        delivery_target=extracted.delivery_target,
        target_unit_price=extracted.target_unit_price,
        requirements=mapped,
    ):
        return brief_snapshot(project, brief, current)

    if brief is None:
        brief = Brief(project_id=project.id)
        database_session.add(brief)
    brief.product_name = extracted.product_name
    brief.category = extracted.category
    brief.quantity = extracted.quantity
    brief.destination = extracted.destination
    brief.delivery_target = (
        extracted.delivery_target.model_dump() if extracted.delivery_target else None
    )
    brief.target_unit_price = (
        Decimal(extracted.target_unit_price) if extracted.target_unit_price else None
    )
    database_session.add_all(mapped)
    database_session.flush()
    current = project_requirements(database_session, project.id)
    recalculate_brief_readiness(database_session, brief, current)
    increment_brief_revision(database_session, project)
    return brief_snapshot(project, brief, current)


def analyze_project_brief(
    database_session: Session,
    *,
    demo_session: DemoSession,
    project: Project,
    client_factory: Callable[[], StructuredModelClient],
) -> AnalyzeBriefResponse:
    """Guard a model call, then recheck under a lock before saving its draft."""
    brief = database_session.get(Brief, project.id)
    if not can_analyze(project, brief, project_requirements(database_session, project.id)):
        raise BriefConflictError("This Brief already has saved content. Analyze cannot replace it.")
    try:
        client = client_factory()
        extracted, _ = interpret_project_request(
            database_session,
            demo_session=demo_session,
            project_id=project.id,
            client=client,
        )
    except RuntimeError as error:
        raise BriefAnalysisUnavailableError("Brief analysis is unavailable.") from error
    if extracted is None:
        raise BriefAnalysisUnavailableError("Brief analysis is unavailable.")

    database_session.expire_all()
    refreshed = database_session.scalars(
        select(Project)
        .where(Project.id == project.id, Project.demo_session_id == demo_session.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one_or_none()
    if refreshed is None:
        raise BriefConflictError("Project is no longer available.")
    result = persist_extraction(database_session, refreshed, extracted)
    return AnalyzeBriefResponse(**result.model_dump(), ambiguities=extracted.ambiguities)
