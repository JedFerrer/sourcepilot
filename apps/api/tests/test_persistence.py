from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import Engine, delete, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sourcepilot.persistence.models import DemoSession, Project, Requirement
from tests.conftest import database_session_for_engine
from tests.database_test_support import (
    create_test_engine,
    persistence_test_database_url_from_environment,
    reset_test_database,
)


@pytest.fixture(scope="module")
def test_database_url() -> str:
    return persistence_test_database_url_from_environment()


@pytest.fixture(scope="module")
def test_engine(test_database_url: str) -> Iterator[Engine]:
    engine = create_test_engine(test_database_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(autouse=True)
def reset_persistence_database(test_database_url: str) -> Iterator[None]:
    reset_test_database(test_database_url)
    yield
    reset_test_database(test_database_url)


@pytest.fixture
def database_session(test_engine: Engine) -> Iterator[Session]:
    yield from database_session_for_engine(test_engine)


def make_demo_session(token: str = "token-a") -> DemoSession:
    now = datetime.now(UTC)
    return DemoSession(
        opaque_token=token,
        last_seen_at=now,
        expires_at=now + timedelta(hours=24),
    )


def test_migration_smoke_creates_only_current_application_tables(test_engine: Engine) -> None:
    with test_engine.connect() as connection:
        current_revisions = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()

    assert current_revisions == ["0005_supplier_catalog"]

    table_names = set(inspect(test_engine).get_table_names())

    assert {
        "demo_sessions", "projects", "ai_runs", "briefs", "requirements",
        "suppliers", "supplier_capabilities", "supplier_evidence",
    }.issubset(table_names)
    assert table_names - {
        "demo_sessions",
        "projects",
        "ai_runs",
        "briefs",
        "requirements",
        "suppliers",
        "supplier_capabilities",
        "supplier_evidence",
        "alembic_version",
    } == set()

    demo_session_unique_constraints = [
        constraint
        for constraint in inspect(test_engine).get_unique_constraints("demo_sessions")
        if constraint["column_names"] == ["opaque_token"]
    ]

    assert len(demo_session_unique_constraints) == 1

    project_columns = {column["name"]: column for column in inspect(test_engine).get_columns("projects")}
    brief_columns = {column["name"]: column for column in inspect(test_engine).get_columns("briefs")}
    requirement_columns = {column["name"]: column for column in inspect(test_engine).get_columns("requirements")}

    assert not project_columns["brief_revision"]["nullable"]
    assert project_columns["brief_revision"]["default"] == "0"
    assert brief_columns["quantity"]["nullable"]
    assert brief_columns["delivery_target"]["nullable"]
    assert brief_columns["target_unit_price"]["nullable"]
    assert "IN_PROGRESS" in str(brief_columns["status"]["default"])
    assert requirement_columns["importance"]["nullable"]


def test_nullable_importance_preserves_existing_rows_through_upgrade(
    test_engine: Engine, test_database_url: str
) -> None:
    from alembic import command
    from tests.database_test_support import alembic_config

    config = alembic_config(test_database_url)
    command.downgrade(config, "0003_brief_requirement_domain")
    with Session(test_engine) as session:
        project = Project(
            demo_session=make_demo_session(),
            name="Existing",
            original_request="Source bags.",
        )
        session.add(project)
        session.flush()
        project_id = project.id
        requirement = Requirement(
            project_id=project_id,
            kind="MATERIAL",
            importance="REQUIRED",
            expected_value={"value": "Cotton"},
        )
        session.add(requirement)
        session.commit()
        requirement_id = requirement.id

    command.upgrade(config, "head")
    with Session(test_engine) as session:
        preserved = session.get(Requirement, requirement_id)
        assert preserved is not None
        assert preserved.project_id == project_id
        assert preserved.importance == "REQUIRED"
        assert preserved.expected_value == {"value": "cotton"}
        session.add(
            Requirement(
                project_id=project_id,
                kind="MATERIAL",
                importance=None,
                expected_value={"value": "Polyester"},
            )
        )
        session.commit()
        values = set(
            session.scalars(
                select(Requirement.importance).where(Requirement.project_id == project_id)
            ).all()
        )
        assert values == {"REQUIRED", None}
    with pytest.raises(RuntimeError, match="Resolve unknown requirement importance"):
        command.downgrade(config, "0003_brief_requirement_domain")


def test_project_brief_revision_defaults_to_zero(database_session: Session) -> None:
    project = Project(
        demo_session=make_demo_session(),
        name="New project",
        original_request="Source travel bags.",
    )
    database_session.add(project)
    database_session.commit()
    database_session.expire_all()

    reloaded = database_session.get(Project, project.id)
    assert reloaded is not None
    assert reloaded.brief_revision == 0


def test_project_persists_with_its_demo_session(database_session: Session) -> None:
    demo_session = make_demo_session()
    project = Project(
        demo_session=demo_session,
        name="Recycled Cosmetic Travel Bag",
        original_request="Source 2,000 recycled cosmetic travel bags.",
    )
    database_session.add(project)
    database_session.commit()
    project_id = project.id
    database_session.expire_all()

    reloaded = database_session.get(Project, project_id)

    assert reloaded is not None
    assert reloaded.demo_session_id == demo_session.id
    assert reloaded.demo_session.opaque_token == "token-a"
    assert reloaded.stage == "BRIEF"


def test_project_requires_an_existing_demo_session(database_session: Session) -> None:
    project = Project(
        demo_session_id=uuid4(),
        name="Unowned project",
        original_request="This must fail.",
    )
    database_session.add(project)

    with pytest.raises(IntegrityError):
        database_session.commit()
    database_session.rollback()


def test_demo_session_token_is_unique(database_session: Session) -> None:
    database_session.add(make_demo_session("same-token"))
    database_session.commit()
    database_session.add(make_demo_session("same-token"))

    with pytest.raises(IntegrityError):
        database_session.commit()
    database_session.rollback()


def test_deleting_a_demo_session_cascades_to_its_projects(database_session: Session) -> None:
    demo_session = make_demo_session()
    project = Project(
        demo_session=demo_session,
        name="Cascaded project",
        original_request="This project should be deleted with its session.",
    )
    database_session.add(project)
    database_session.commit()
    project_id = project.id

    database_session.execute(delete(DemoSession).where(DemoSession.id == demo_session.id))
    database_session.commit()
    database_session.expire_all()

    assert database_session.get(Project, project_id) is None


def test_database_is_reset_between_tests(database_session: Session) -> None:
    assert database_session.query(DemoSession).count() == 0
    assert database_session.query(Project).count() == 0
