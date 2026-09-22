from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from sourcepilot.persistence.models import DemoSession, Project
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
