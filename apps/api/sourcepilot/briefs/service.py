from sqlalchemy.orm import Session

from sourcepilot.persistence.models import Project


def increment_brief_revision(database_session: Session, project: Project) -> Project:
    """Advance the internal revision when a later brief-editing use case requires it."""
    project.brief_revision += 1
    database_session.flush()
    return project
