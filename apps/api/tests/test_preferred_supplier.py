"""Human preference contracts, persistence, ownership, and serialized shortlist rules."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event, current_thread
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, event, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from sourcepilot.main import app
from sourcepilot.persistence.database import get_database_session
from sourcepilot.persistence.models import (
    AIRun,
    DemoSession,
    Project,
    ProjectSupplier,
    Requirement,
    RequirementEvaluationRecord,
    Supplier,
)
from sourcepilot.projects.decision import (
    PreferredSupplierNotShortlistedError,
    validate_preferred_supplier,
)
from sourcepilot.projects.schemas import PreferredSupplierRequest
from sourcepilot.projects.service import update_preferred_supplier
from sourcepilot.session.settings import DEMO_SESSION_COOKIE_NAME
from sourcepilot.suppliers.schemas import UpdateSupplierReviewRequest
from sourcepilot.suppliers.seed import seed_suppliers
from sourcepilot.suppliers.service import update_supplier_review
from tests.database_test_support import (
    alembic_config,
    create_test_engine,
    persistence_test_database_url_from_environment,
    reset_test_database,
)
from tests.test_comparison_snapshot import confirm_manual, setup_project


@pytest.fixture(scope="module")
def database_url() -> str:
    return persistence_test_database_url_from_environment()


@pytest.fixture(scope="module")
def engine(database_url: str) -> Iterator[Engine]:
    value = create_test_engine(database_url)
    yield value
    value.dispose()


@pytest.fixture
def client(engine: Engine, database_url: str) -> Iterator[TestClient]:
    reset_test_database(database_url)
    with Session(engine) as session:
        seed_suppliers(session)
        session.commit()

    def override() -> Iterator[Session]:
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_database_session] = override
    try:
        with TestClient(app, raise_server_exceptions=False) as value:
            assert value.post("/demo-session").status_code == 204
            yield value
    finally:
        app.dependency_overrides.clear()
        reset_test_database(database_url)


@pytest.mark.parametrize("action,shortlisted,allowed", [
    ("clear", False, True), ("retain", False, True),
    ("replace", True, True), ("replace", False, False),
])
def test_decision_rule(action: str, shortlisted: bool, allowed: bool) -> None:
    stored = uuid4()
    supplied = None if action == "clear" else stored if action == "retain" else uuid4()
    if allowed:
        validate_preferred_supplier(supplied, current_supplier_id=stored, shortlisted=shortlisted)
    else:
        with pytest.raises(PreferredSupplierNotShortlistedError):
            validate_preferred_supplier(supplied, current_supplier_id=stored, shortlisted=shortlisted)


def test_select_replace_clear_and_project_responses(client: TestClient) -> None:
    project_id, ids = setup_project(client)
    path = f"/projects/{project_id}/preferred-supplier"
    for supplier_id in (ids[0], ids[2], ids[2]):
        saved = client.put(path, json={"supplier_id": supplier_id, "decision_notes": "  My choice  "})
        assert saved.status_code == 200, saved.text
        assert saved.json()["preferred_supplier_id"] == supplier_id
        assert saved.json()["preferred_supplier_name"]
        assert saved.json()["decision_notes"] == "My choice"
        assert saved.json()["stage"] == "QUOTES"
        read = client.get(f"/projects/{project_id}").json()
        listed = client.get("/projects").json()[0]
        renamed = client.patch(f"/projects/{project_id}", json={"name": "New name"}).json()
        for response in (read, listed, renamed):
            assert response["preferred_supplier_id"] == supplier_id
            assert response["preferred_supplier_name"] == saved.json()["preferred_supplier_name"]
            assert response["decision_notes"] == "My choice"
    for _ in range(2):
        cleared = client.put(path, json={"supplier_id": None}).json()
        assert cleared["preferred_supplier_id"] is None
        assert cleared["preferred_supplier_name"] is None
        assert cleared["decision_notes"] == "My choice"


@pytest.mark.parametrize("notes,expected", [(None, None), ("  ", None), ("  Revised  ", "Revised")])
def test_retained_choice_notes_after_shortlist_and_candidate_removal(
    client: TestClient, engine: Engine, notes: str | None, expected: str | None,
) -> None:
    project_id, ids = setup_project(client)
    path = f"/projects/{project_id}/preferred-supplier"
    assert client.put(path, json={"supplier_id": ids[0], "decision_notes": "Original"}).status_code == 200
    assert client.patch(f"/projects/{project_id}/suppliers/{ids[0]}", json={"dismissed": True}).status_code == 200
    saved = client.put(path, json={"supplier_id": ids[0], "decision_notes": notes})
    assert saved.status_code == 200, saved.text
    assert saved.json()["decision_notes"] == expected
    with Session(engine) as session:
        session.execute(delete(ProjectSupplier).where(
            ProjectSupplier.project_id == UUID(project_id), ProjectSupplier.supplier_id == UUID(ids[0]),
        ))
        session.commit()
    retained = client.put(path, json={"supplier_id": ids[0], "decision_notes": "Candidate gone"})
    assert retained.status_code == 200, retained.text
    assert client.get(f"/projects/{project_id}").json()["decision_notes"] == "Candidate gone"
    assert client.put(path, json={"supplier_id": ids[2]}).status_code == 200
    assert client.put(path, json={"supplier_id": None}).status_code == 200


@pytest.mark.parametrize("kind", ["unknown", "catalog", "foreign", "removed", "dismissed"])
def test_new_selection_rejected_atomically(client: TestClient, engine: Engine, kind: str) -> None:
    project_id, ids = setup_project(client)
    path = f"/projects/{project_id}/preferred-supplier"
    assert client.put(path, json={"supplier_id": ids[0], "decision_notes": "Keep"}).status_code == 200
    if kind == "unknown":
        other = str(uuid4())
    elif kind in {"catalog", "foreign"}:
        with Session(engine) as session:
            candidate_ids = select(ProjectSupplier.supplier_id).where(ProjectSupplier.project_id == UUID(project_id))
            other = str(session.scalars(select(Supplier.id).where(Supplier.id.not_in(candidate_ids))).first())
            if kind == "foreign":
                owner = session.get(Project, UUID(project_id))
                assert owner is not None
                foreign_session = DemoSession(opaque_token="foreign", expires_at=datetime.now(UTC) + timedelta(hours=1))
                foreign = Project(demo_session=foreign_session, name="Other", original_request="Other")
                session.add(foreign)
                session.flush()
                session.add(ProjectSupplier(project_id=foreign.id, supplier_id=UUID(other), shortlisted=True, evaluated_against_brief_revision=0))
                session.commit()
    else:
        other = ids[1]
        change = {"dismissed": True} if kind == "dismissed" else {"shortlisted": False}
        assert client.patch(f"/projects/{project_id}/suppliers/{other}", json=change).status_code == 200
    rejected = client.put(path, json={"supplier_id": other, "decision_notes": "Overwrite"})
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["error"]["code"] == "PREFERRED_SUPPLIER_NOT_SHORTLISTED"
    read = client.get(f"/projects/{project_id}").json()
    assert read["preferred_supplier_id"] == ids[0]
    assert read["decision_notes"] == "Keep"


def test_only_shortlist_flag_is_decision_eligibility(client: TestClient, engine: Engine) -> None:
    project_id, ids = setup_project(client)
    # This deliberately inconsistent database row is outside supported M2 mutations.
    # M5 must not introduce an independent dismissal, stage, quote, or requirement gate.
    with Session(engine) as session:
        item = session.get(ProjectSupplier, (UUID(project_id), UUID(ids[0])))
        project = session.get(Project, UUID(project_id))
        assert item is not None and project is not None
        item.dismissed = True
        project.stage = "BRIEF"
        session.commit()
    saved = client.put(f"/projects/{project_id}/preferred-supplier", json={"supplier_id": ids[0]})
    assert saved.status_code == 200, saved.text


@pytest.mark.parametrize("status", ["DOES_NOT_MEET", "UNKNOWN", "CONFLICT"])
def test_required_findings_do_not_block_human_selection(
    client: TestClient, engine: Engine, status: str,
) -> None:
    project_id, ids = setup_project(client)
    with Session(engine) as session:
        finding = session.scalars(select(RequirementEvaluationRecord).join(
            Requirement, Requirement.id == RequirementEvaluationRecord.requirement_id,
        ).where(
            RequirementEvaluationRecord.project_id == UUID(project_id),
            RequirementEvaluationRecord.supplier_id == UUID(ids[0]),
            Requirement.importance == "REQUIRED",
        )).first()
        assert finding is not None
        finding.status = status
        session.commit()
    result = client.put(f"/projects/{project_id}/preferred-supplier", json={"supplier_id": ids[0]})
    assert result.status_code == 200, result.text
    assert result.json()["preferred_supplier_id"] == ids[0]


def test_notes_without_a_supplier_and_null_creation_defaults(client: TestClient) -> None:
    created = client.post("/projects", json={"name": "Pending", "original_request": "Source"}).json()
    assert created["preferred_supplier_id"] is None
    assert created["preferred_supplier_name"] is None
    assert created["decision_notes"] is None
    path = f"/projects/{created['id']}/preferred-supplier"
    assert client.put(path, json={"supplier_id": None, "decision_notes": "Still reviewing"}).status_code == 200
    assert client.put(path, json={"supplier_id": None}).json()["decision_notes"] == "Still reviewing"
    assert client.put(path, json={"supplier_id": None, "decision_notes": None}).json()["decision_notes"] is None


@pytest.mark.parametrize("body", [{}, {"supplier_id": "invalid"}, {"supplier_id": None, "stage": "DECISION"}, {"supplier_id": None, "decision_notes": "x" * 10001}])
def test_invalid_payload(client: TestClient, body: dict[str, object]) -> None:
    project_id = client.post("/projects", json={"name": "Empty", "original_request": "Source"}).json()["id"]
    result = client.put(f"/projects/{project_id}/preferred-supplier", json=body)
    assert result.status_code == 422
    assert client.get(f"/projects/{project_id}").json()["preferred_supplier_id"] is None


def test_session_isolation_expiry_and_missing_project(client: TestClient, engine: Engine) -> None:
    project_id, ids = setup_project(client)
    path = f"/projects/{project_id}/preferred-supplier"
    cookie = client.cookies.get(DEMO_SESSION_COOKIE_NAME)
    assert cookie is not None
    client.cookies.clear()
    assert client.put(path, json={"supplier_id": None}).status_code == 401
    assert client.post("/demo-session").status_code == 204
    assert client.put(path, json={"supplier_id": ids[0]}).status_code == 404
    assert client.put(f"/projects/{uuid4()}/preferred-supplier", json={"supplier_id": None}).status_code == 404
    client.cookies.clear()
    client.cookies.set(DEMO_SESSION_COOKIE_NAME, cookie)
    with Session(engine) as session:
        owner = session.scalar(select(DemoSession).where(DemoSession.opaque_token == cookie))
        assert owner is not None
        owner.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()
    assert client.put(path, json={"supplier_id": None}).status_code == 401


def test_decision_does_not_mutate_comparison_quotes_or_runs(client: TestClient, engine: Engine) -> None:
    project_id, ids = setup_project(client)
    quote_ids = [confirm_manual(client, project_id, supplier_id) for supplier_id in ids[:2]]
    before = client.post(f"/projects/{project_id}/comparison/generate").json()
    quotes = [client.get(f"/quotes/{quote_id}").json() for quote_id in quote_ids]
    with Session(engine) as session:
        runs = session.scalar(select(func.count()).select_from(AIRun))
    path = f"/projects/{project_id}/preferred-supplier"
    # Supplier C has no confirmed quote and is absent from the snapshot.
    assert client.put(path, json={"supplier_id": ids[2]}).status_code == 200
    assert client.put(path, json={"supplier_id": ids[2], "decision_notes": "Notes"}).status_code == 200
    assert client.put(path, json={"supplier_id": None}).status_code == 200
    assert client.get(f"/projects/{project_id}/comparison").json() == before
    assert [client.get(f"/quotes/{quote_id}").json() for quote_id in quote_ids] == quotes
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(AIRun)) == runs


def test_migration_and_preference_integrity(client: TestClient, engine: Engine, database_url: str) -> None:
    project_id, ids = setup_project(client)
    config = alembic_config(database_url)
    command.downgrade(config, "0014_comparisons")
    command.upgrade(config, "head")
    read = client.get(f"/projects/{project_id}").json()
    assert read["preferred_supplier_id"] is None and read["decision_notes"] is None
    assert client.put(f"/projects/{project_id}/preferred-supplier", json={"supplier_id": ids[0], "decision_notes": "Saved"}).status_code == 200
    with engine.connect() as connection:
        assert connection.execute(text("SELECT preferred_supplier_id, decision_notes FROM projects WHERE id=:id"), {"id": UUID(project_id)}).one() == (UUID(ids[0]), "Saved")
    with Session(engine) as session:
        with pytest.raises(IntegrityError):
            session.execute(delete(Supplier).where(Supplier.id == UUID(ids[0])))
            session.commit()
        session.rollback()
        with pytest.raises(IntegrityError):
            session.execute(text("UPDATE projects SET preferred_supplier_id=:supplier WHERE id=:id"), {"supplier": uuid4(), "id": UUID(project_id)})
            session.commit()
        session.rollback()
        owner = session.get(Project, UUID(project_id))
        assert owner is not None
        session.execute(delete(DemoSession).where(DemoSession.id == owner.demo_session_id))
        session.commit()
        assert session.scalar(select(Project.id).where(Project.id == UUID(project_id))) is None


def test_selection_reads_membership_after_competing_mutation(client: TestClient, engine: Engine) -> None:
    project_id, ids = setup_project(client)
    first_locked, second_waiting, release = Event(), Event(), Event()

    def before(conn: object, cursor: object, statement: str, parameters: object, context: object, executemany: bool) -> None:
        if "FROM projects" in statement and "FOR UPDATE" in statement and current_thread().name.endswith("_1"):
            second_waiting.set()

    def after(conn: object, cursor: object, statement: str, parameters: object, context: object, executemany: bool) -> None:
        if "FROM projects" in statement and "FOR UPDATE" in statement and current_thread().name.endswith("_0"):
            first_locked.set()
            assert release.wait(10)

    def mutate() -> None:
        with Session(engine) as session:
            project = session.get(Project, UUID(project_id))
            assert project is not None
            update_supplier_review(session, project, UUID(ids[0]), UpdateSupplierReviewRequest(shortlisted=False))
            session.commit()

    def choose() -> None:
        with Session(engine) as session:
            project = session.get(Project, UUID(project_id))
            # Preload the old member to expose stale identity-map bugs.
            assert session.get(ProjectSupplier, (UUID(project_id), UUID(ids[0]))) is not None
            assert project is not None
            with pytest.raises(PreferredSupplierNotShortlistedError):
                update_preferred_supplier(session, project, PreferredSupplierRequest(supplier_id=UUID(ids[0]), decision_notes="Rejected"))
            session.rollback()

    event.listen(engine, "before_cursor_execute", before)
    event.listen(engine, "after_cursor_execute", after)
    try:
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="decision-race") as pool:
            first = pool.submit(mutate)
            assert first_locked.wait(10)
            second = pool.submit(choose)
            try:
                assert second_waiting.wait(10)
            finally:
                release.set()
            first.result(timeout=10)
            second.result(timeout=10)
    finally:
        release.set()
        event.remove(engine, "before_cursor_execute", before)
        event.remove(engine, "after_cursor_execute", after)
    read = client.get(f"/projects/{project_id}").json()
    assert read["preferred_supplier_id"] is None and read["decision_notes"] is None
