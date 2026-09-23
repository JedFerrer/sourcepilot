from sqlalchemy.orm import Session

from sourcepilot.briefs.domain import BriefStatus
from sourcepilot.briefs.readiness import (
    BriefReadinessResult,
    ReadinessRequirement,
    evaluate_brief_readiness,
)
from sourcepilot.persistence.models import Brief, Project, Requirement


def increment_brief_revision(database_session: Session, project: Project) -> Project:
    """Advance the internal revision when a later brief-editing use case requires it."""
    project.brief_revision += 1
    database_session.flush()
    return project


def recalculate_brief_readiness(
    database_session: Session, brief: Brief, requirements: list[Requirement]
) -> BriefReadinessResult:
    """Persist computed readiness for an unapproved Brief only."""
    if any(
        requirement.project_id != brief.project_id
        or (
            brief.project_id is None
            and (brief.project is None or requirement.project is not brief.project)
        )
        for requirement in requirements
    ):
        raise ValueError("all requirements must belong to the brief's project")

    result = evaluate_brief_readiness(
        product_name=brief.product_name,
        category=brief.category,
        quantity=brief.quantity,
        destination=brief.destination,
        delivery_target=brief.delivery_target,
        requirements=tuple(
            ReadinessRequirement(kind=item.kind, expected_value=item.expected_value)
            for item in requirements
        ),
    )
    if brief.status != BriefStatus.APPROVED:
        brief.status = result.status.value
        database_session.flush()
    return result
