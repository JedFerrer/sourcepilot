"""Read-only application projection of the existing five-stage workflow."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from sourcepilot.briefs.domain import BriefStatus
from sourcepilot.briefs.workflow import brief_snapshot
from sourcepilot.comparison.service import (
    active_quote_revisions_by_project,
    comparison_is_stale,
    comparison_prerequisite,
)
from sourcepilot.persistence.models import Comparison, Project, ProjectSupplier
from sourcepilot.projects.schemas import (
    ProjectResponse,
    WorkflowAction,
    WorkflowNextAction,
    WorkflowReason,
    WorkflowStage,
    WorkflowSummary,
)
from sourcepilot.suppliers.service import supplier_evaluation_is_stale


def project_responses(database_session: Session, projects: list[Project]) -> list[ProjectResponse]:
    """Batch owned projects' inputs; never select stored comparison payloads."""
    ids = [project.id for project in projects]
    if not ids:
        return []
    loaded = {project.id: project for project in database_session.scalars(
        select(Project).where(Project.id.in_(ids)).options(
            selectinload(Project.brief), selectinload(Project.requirements),
            selectinload(Project.preferred_supplier),
        )
    )}
    suppliers: dict[UUID, list[ProjectSupplier]] = {key: [] for key in ids}
    for row in database_session.scalars(
        select(ProjectSupplier).where(ProjectSupplier.project_id.in_(ids))
    ):
        suppliers[row.project_id].append(row)
    revisions = active_quote_revisions_by_project(database_session, ids)
    ranked = select(
        Comparison.project_id, Comparison.brief_revision, Comparison.quote_revision_snapshot,
        Comparison.stale,
        func.row_number().over(
            partition_by=Comparison.project_id,
            order_by=(Comparison.generated_at.desc(), Comparison.id.desc()),
        ).label("position"),
    ).where(Comparison.project_id.in_(ids)).subquery()
    comparisons = {row.project_id: row for row in database_session.execute(
        select(ranked).where(ranked.c.position == 1)
    )}
    responses = []
    for key in ids:
        project = loaded[key]
        brief = brief_snapshot(project, project.brief, project.requirements)
        rows = suppliers[key]
        selected_count = sum(row.shortlisted for row in rows)
        stale_suppliers = any(supplier_evaluation_is_stale(
            row.evaluated_against_brief_revision, project.brief_revision,
        ) for row in rows)
        confirmed_count = len(revisions[key])
        approved = brief.status == BriefStatus.APPROVED
        ready = comparison_prerequisite(
            brief_approved=approved, stage=project.stage, confirmed_count=confirmed_count,
            quantity=brief.quantity,
        ) is None
        comparison = comparisons.get(key)
        stale_comparison = comparison is not None and comparison_is_stale(
            stored_stale=comparison.stale, stage=project.stage,
            brief_revision=project.brief_revision,
            snapshot_brief_revision=comparison.brief_revision,
            quote_snapshot=comparison.quote_revision_snapshot, active_revisions=revisions[key],
        )
        stage: WorkflowStage
        action: WorkflowAction
        reason: WorkflowReason
        if not approved:
            stage = "BRIEF"
            if brief.can_analyze:
                action, reason = "ANALYZE_BRIEF", "BRIEF_ANALYSIS_AVAILABLE"
            elif brief.status != BriefStatus.READY_FOR_REVIEW:
                action, reason = "COMPLETE_BRIEF", "BRIEF_INCOMPLETE"
            else:
                action, reason = "APPROVE_BRIEF", "BRIEF_APPROVAL_REQUIRED"
        elif not rows:
            stage, action, reason = "SUPPLIERS", "DISCOVER_SUPPLIERS", "SUPPLIERS_NOT_DISCOVERED"
        elif stale_suppliers:
            stage, action, reason = "SUPPLIERS", "REFRESH_SUPPLIERS", "SUPPLIER_EVALUATIONS_STALE"
        elif project.stage != "QUOTES":
            stage = "SUPPLIERS"
            if selected_count == 0:
                action, reason = "REVIEW_SHORTLIST", "SHORTLIST_EMPTY"
            elif selected_count > 3:
                action, reason = "REVIEW_SHORTLIST", "SHORTLIST_OVER_LIMIT"
            else:
                action, reason = "APPROVE_SHORTLIST", "SHORTLIST_APPROVAL_REQUIRED"
        elif not ready:
            stage, action, reason = "QUOTES", "COMPLETE_QUOTES", "INSUFFICIENT_CONFIRMED_QUOTES"
        elif comparison is None:
            stage, action, reason = "COMPARISON", "GENERATE_COMPARISON", "COMPARISON_NOT_GENERATED"
        elif stale_comparison:
            stage, action, reason = "COMPARISON", "REGENERATE_COMPARISON", "COMPARISON_STALE"
        elif project.preferred_supplier_id is None:
            stage, action, reason = "DECISION", "RECORD_PREFERENCE", "PREFERENCE_NOT_RECORDED"
        else:
            stage, action, reason = "DECISION", "MANAGE_PREFERENCE", "PREFERENCE_RECORDED"
        supplier_block: WorkflowReason | None = reason if not approved else None
        quote_block: WorkflowReason | None = (
            reason if not approved or project.stage != "QUOTES" or stale_suppliers else None
        )
        summary = WorkflowSummary(
            current_stage=stage,
            next_action=WorkflowNextAction(code=action, reason_code=reason, target_stage=stage),
            shortlist_count=selected_count, confirmed_quote_count=confirmed_count,
            comparison_ready=ready, comparison_present=comparison is not None,
            comparison_stale=stale_comparison, suppliers_stale=stale_suppliers,
            stage_prerequisites={
                "BRIEF": None, "SUPPLIERS": supplier_block, "QUOTES": quote_block,
                "COMPARISON": reason if not ready else None,
                "DECISION": "SHORTLIST_EMPTY" if selected_count == 0 else None,
            },
        )
        responses.append(ProjectResponse.model_validate({
            **{name: getattr(project, name) for name in ProjectResponse.model_fields
               if name != "workflow"}, "workflow": summary,
        }))
    return responses
