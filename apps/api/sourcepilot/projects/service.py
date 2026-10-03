from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from sourcepilot.persistence.models import DemoSession, Project, ProjectSupplier
from sourcepilot.projects.decision import validate_preferred_supplier
from sourcepilot.projects.schemas import PreferredSupplierRequest
from sourcepilot.session.service import project_for_resolved_demo_session


def create_project(
    database_session: Session,
    demo_session: DemoSession,
    *,
    name: str,
    original_request: str,
) -> Project:
    """Create a project owned by the active anonymous session."""
    project = Project(
        demo_session_id=demo_session.id,
        name=name,
        original_request=original_request,
    )
    database_session.add(project)
    database_session.flush()
    return project


def projects_for_demo_session(database_session: Session, demo_session: DemoSession) -> list[Project]:
    """Return only the active session's projects, most recently updated first."""
    return list(
        database_session.scalars(
            select(Project)
            .where(Project.demo_session_id == demo_session.id)
            .options(selectinload(Project.preferred_supplier))
            .order_by(desc(Project.updated_at), desc(Project.id))
        )
    )


def project_for_demo_session(
    database_session: Session, demo_session: DemoSession, project_id: UUID
) -> Project | None:
    """Return one project only when it belongs to the active session."""
    return project_for_resolved_demo_session(database_session, demo_session, project_id)


def rename_project(database_session: Session, project: Project, *, name: str) -> Project:
    """Persist a project name change for a previously authorized project."""
    project.name = name
    database_session.flush()
    return project


def update_preferred_supplier(
    database_session: Session, project: Project, payload: PreferredSupplierRequest,
) -> Project:
    """Serialize the owned decision with shortlist edits; keep all other workflow state."""
    locked_project = database_session.scalars(
        select(Project).where(
            Project.id == project.id, Project.demo_session_id == project.demo_session_id,
        ).with_for_update().execution_options(populate_existing=True)
    ).one()
    shortlisted = False
    if payload.supplier_id is not None and payload.supplier_id != locked_project.preferred_supplier_id:
        shortlisted = database_session.scalar(select(ProjectSupplier.shortlisted).where(
            ProjectSupplier.project_id == locked_project.id,
            ProjectSupplier.supplier_id == payload.supplier_id,
        )) is True
    validate_preferred_supplier(
        payload.supplier_id, current_supplier_id=locked_project.preferred_supplier_id,
        shortlisted=shortlisted,
    )
    locked_project.preferred_supplier_id = payload.supplier_id
    if "decision_notes" in payload.model_fields_set:
        locked_project.decision_notes = payload.decision_notes
    database_session.flush()
    database_session.expire(locked_project, ["preferred_supplier"])
    return locked_project
