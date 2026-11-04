"""Expire only a designated isolated E2E fixture, never through an HTTP endpoint."""
import argparse
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from sourcepilot.persistence.models import DemoSession, Project
from tests.e2e_support.database import safe_database_url

FIXTURE_NAME = "M6-U3 designated expiry fixture"


def expire_session(project_id: UUID) -> None:
    engine = create_engine(safe_database_url())
    try:
        with Session(engine) as session, session.begin():
            project = session.get(Project, project_id)
            if project is None or project.name != FIXTURE_NAME or project.stage != "BRIEF":
                raise RuntimeError("Only the designated E2E expiry project may expire its session.")
            projects = session.scalars(select(Project.id).where(
                Project.demo_session_id == project.demo_session_id)).all()
            if projects != [project_id]:
                raise RuntimeError("The expiry fixture must be the session's only project.")
            owner = session.get(DemoSession, project.demo_session_id, with_for_update=True)
            if owner is None:
                raise RuntimeError("The designated E2E session is missing.")
            owner.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id", type=UUID)
    expire_session(parser.parse_args().project_id)
