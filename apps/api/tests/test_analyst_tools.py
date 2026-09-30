"""M2-U5 supplier tool contracts, scoping, staleness, and trace tests."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from sourcepilot.ai.analyst_tools import (
    AnalystToolContext,
    AnalystToolRuntime,
    EvaluationAvailability,
    SupplierEvidenceResult,
    SupplierSnapshot,
    ToolError,
    ToolErrorCode,
    get_supplier_evidence,
    get_supplier_snapshot,
)
from sourcepilot.main import app
from sourcepilot.persistence.database import get_database_session
from sourcepilot.persistence.models import DemoSession, Project, ProjectSupplier, Supplier
from sourcepilot.suppliers.seed import seed_suppliers
from tests.database_test_support import (
    create_test_engine,
    persistence_test_database_url_from_environment,
    reset_test_database,
)


@pytest.fixture(scope="module")
def database_url() -> str:
    return persistence_test_database_url_from_environment()


@pytest.fixture(scope="module")
def engine(database_url: str) -> Iterator[Engine]:
    test_engine = create_test_engine(database_url)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def client(engine: Engine, database_url: str) -> Iterator[TestClient]:
    reset_test_database(database_url)
    with Session(engine) as session:
        seed_suppliers(session)
        session.commit()
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_database_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_database_session] = override_database_session
    with TestClient(app, raise_server_exceptions=False) as value:
        assert value.post("/demo-session").status_code == 204
        yield value
    app.dependency_overrides.clear()
    reset_test_database(database_url)


def _discovered_project(client: TestClient, engine: Engine) -> tuple[UUID, UUID, UUID]:
    created = client.post(
        "/projects", json={"name": "Bags", "original_request": "Source cosmetic bags."}
    )
    assert created.status_code == 201
    project_id = UUID(created.json()["id"])
    edited = client.patch(f"/projects/{project_id}/brief", json={
        "product_name": "Cosmetic bag",
        "category": "cosmetic travel bag",
        "quantity": 2000,
        "destination": "Sydney",
        "delivery_target": {"kind": "DATE", "date": "2027-01-01"},
        "target_unit_price": None,
        "requirements": [
            {"kind": "MATERIAL", "importance": "REQUIRED",
             "expected_value": {"value": "recycled polyester"}},
            {"kind": "CERTIFICATION", "importance": "PREFERRED",
             "expected_value": {"value": "grs"}},
            {"kind": "CAPABILITY", "importance": "REQUIRED",
             "expected_value": {"capability_key": "CUSTOM_BRANDING", "value": True}},
        ],
    })
    assert edited.status_code == 200
    approved = client.post(
        f"/projects/{project_id}/brief/approve",
        json={"expected_brief_revision": edited.json()["brief_revision"]},
    )
    assert approved.status_code == 200
    assert client.post(f"/projects/{project_id}/suppliers/discover").status_code == 200
    suppliers = client.get(f"/projects/{project_id}/suppliers").json()["suppliers"]
    supplier_id = UUID(next(value["id"] for value in suppliers if value["evidence"]))
    with Session(engine) as session:
        project = session.get(Project, project_id)
        assert project is not None
        demo_session_id = project.demo_session_id
    return demo_session_id, project_id, supplier_id


def _runtime(
    demo_session_id: UUID, project_id: UUID, supplier_ids: frozenset[UUID],
    *, max_tool_calls: int = 6,
) -> AnalystToolRuntime:
    return AnalystToolRuntime(AnalystToolContext(
        demo_session_id=demo_session_id,
        project_id=project_id,
        permitted_supplier_ids=supplier_ids,
        max_tool_calls=max_tool_calls,
    ))


def _assert_error(code: ToolErrorCode, call: object) -> None:
    assert callable(call)
    with pytest.raises(ToolError) as captured:
        call()
    assert captured.value.code == code


def test_snapshot_evidence_staleness_and_absence(client: TestClient, engine: Engine) -> None:
    demo_session_id, project_id, supplier_id = _discovered_project(client, engine)
    runtime = _runtime(demo_session_id, project_id, frozenset({supplier_id}), max_tool_calls=7)
    with Session(engine) as session:
        before = session.get(ProjectSupplier, (project_id, supplier_id))
        assert before is not None
        original_revision = before.evaluated_against_brief_revision
        snapshot = get_supplier_snapshot(session, runtime, supplier_id)
        assert isinstance(snapshot, SupplierSnapshot)
        assert snapshot.evaluation_availability == EvaluationAvailability.CURRENT
        assert snapshot.evaluations
        assert snapshot.current_brief_revision == original_revision
        all_evidence = get_supplier_evidence(session, runtime, supplier_id)
        assert isinstance(all_evidence, SupplierEvidenceResult)
        assert all_evidence.evidence
        assert all(item.id for item in all_evidence.evidence)
        claim_key = all_evidence.evidence[0].claim_key
        filtered = get_supplier_evidence(session, runtime, supplier_id, (claim_key,))
        assert filtered.evidence
        assert all(item.claim_key == claim_key for item in filtered.evidence)
        assert get_supplier_evidence(session, runtime, supplier_id, ("missing",)).evidence == []
        assert not session.dirty and not session.new and not session.deleted

    with Session(engine) as session:
        project = session.get(Project, project_id)
        assert project is not None
        project.brief_revision += 1
        session.commit()
    with Session(engine) as session:
        stale = get_supplier_snapshot(session, runtime, supplier_id)
        assert stale.evaluation_availability == EvaluationAvailability.STALE
        assert stale.evaluations == []
        assert stale.evaluated_against_brief_revision == original_revision
        assert stale.current_brief_revision == original_revision + 1
        assert get_supplier_evidence(session, runtime, supplier_id).evidence

    with Session(engine) as session:
        candidate = session.get(ProjectSupplier, (project_id, supplier_id))
        assert candidate is not None
        candidate.evaluated_against_brief_revision = original_revision + 1
        candidate.evaluations.clear()
        session.commit()
    with Session(engine) as session:
        absent = get_supplier_snapshot(session, runtime, supplier_id)
        assert absent.evaluation_availability == EvaluationAvailability.ABSENT
        assert absent.evaluations == []
        assert absent.current_brief_revision == absent.evaluated_against_brief_revision
    assert runtime.successful_call_count == 7
    assert [event.outcome for event in runtime.trace] == ["SUCCESS"] * 7


def test_scoping_and_candidate_revalidation(client: TestClient, engine: Engine) -> None:
    demo_session_id, project_id, supplier_id = _discovered_project(client, engine)
    another_supplier_id = UUID(next(
        value["id"] for value in client.get(f"/projects/{project_id}/suppliers").json()["suppliers"]
        if UUID(value["id"]) != supplier_id
    ))
    other = client.post(
        "/projects", json={"name": "Other", "original_request": "Other request"}
    )
    assert other.status_code == 201
    other_project_id = UUID(other.json()["id"])
    with TestClient(app, raise_server_exceptions=False) as other_client:
        assert other_client.post("/demo-session").status_code == 204
        other_session_project = other_client.post(
            "/projects", json={"name": "Other session", "original_request": "Other request"}
        )
        assert other_session_project.status_code == 201
    with Session(engine) as session:
        other_session_project_record = session.get(
            Project, UUID(other_session_project.json()["id"])
        )
        assert other_session_project_record is not None
        other_demo_session_id = other_session_project_record.demo_session_id
    runtime = _runtime(demo_session_id, project_id, frozenset({supplier_id}))
    with Session(engine) as session:
        _assert_error(ToolErrorCode.NOT_ALLOWED, lambda: get_supplier_snapshot(
            session, runtime, uuid4()
        ))
        _assert_error(ToolErrorCode.NOT_ALLOWED, lambda: get_supplier_snapshot(
            session, runtime, another_supplier_id
        ))
        _assert_error(ToolErrorCode.NOT_ALLOWED, lambda: get_supplier_evidence(
            session, _runtime(demo_session_id, other_project_id, frozenset({supplier_id})),
            supplier_id,
        ))
        _assert_error(ToolErrorCode.NOT_ALLOWED, lambda: get_supplier_snapshot(
            session, _runtime(other_demo_session_id, project_id, frozenset({supplier_id})),
            supplier_id,
        ))
    with Session(engine) as session:
        candidate = session.get(ProjectSupplier, (project_id, supplier_id))
        assert candidate is not None
        session.delete(candidate)
        session.commit()
    with Session(engine) as session:
        _assert_error(ToolErrorCode.NOT_ALLOWED, lambda: get_supplier_snapshot(
            session, runtime, supplier_id
        ))
        _assert_error(ToolErrorCode.NOT_ALLOWED, lambda: get_supplier_evidence(
            session, runtime, supplier_id
        ))
    with Session(engine) as session:
        demo_session = session.get(DemoSession, demo_session_id)
        assert demo_session is not None
        demo_session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()
    with Session(engine) as session:
        _assert_error(ToolErrorCode.NOT_ALLOWED, lambda: get_supplier_snapshot(
            session, runtime, supplier_id
        ))
    assert runtime.successful_call_count == 0
    assert [event.outcome for event in runtime.trace] == [
        "NOT_ALLOWED", "NOT_ALLOWED", "NOT_ALLOWED", "NOT_ALLOWED", "NOT_ALLOWED"
    ]


def test_deleted_permitted_supplier_is_not_found(client: TestClient, engine: Engine) -> None:
    demo_session_id, project_id, supplier_id = _discovered_project(client, engine)
    runtime = _runtime(demo_session_id, project_id, frozenset({supplier_id}))
    with Session(engine) as session:
        supplier = session.get(Supplier, supplier_id)
        assert supplier is not None
        session.delete(supplier)
        session.commit()
    with Session(engine) as session:
        _assert_error(ToolErrorCode.NOT_FOUND, lambda: get_supplier_snapshot(
            session, runtime, supplier_id
        ))
        _assert_error(ToolErrorCode.NOT_FOUND, lambda: get_supplier_evidence(
            session, runtime, supplier_id
        ))
    assert runtime.successful_call_count == 0
    assert [event.outcome for event in runtime.trace] == ["NOT_FOUND", "NOT_FOUND"]
    assert all(event.successful_call_count == 0 for event in runtime.trace)


def test_tools_preserve_pending_orm_edits_and_revalidate_persisted_state(
    client: TestClient, engine: Engine,
) -> None:
    demo_session_id, project_id, supplier_id = _discovered_project(client, engine)
    runtime = _runtime(demo_session_id, project_id, frozenset({supplier_id}))
    with Session(engine) as session:
        project = session.get(Project, project_id)
        supplier = session.get(Supplier, supplier_id)
        candidate = session.get(ProjectSupplier, (project_id, supplier_id))
        assert project is not None and supplier is not None and candidate is not None
        persisted_revision = project.brief_revision
        persisted_name = supplier.name
        project.demo_session_id = uuid4()
        project.brief_revision = persisted_revision + 2
        supplier.name = "Pending supplier name"
        candidate.project_id = uuid4()
        candidate.evaluated_against_brief_revision = persisted_revision + 1
        pending = {project, supplier, candidate}

        snapshot = get_supplier_snapshot(session, runtime, supplier_id)
        assert snapshot.name == persisted_name
        assert snapshot.current_brief_revision == persisted_revision
        assert snapshot.evaluated_against_brief_revision == persisted_revision
        assert snapshot.evaluation_availability == EvaluationAvailability.CURRENT
        assert get_supplier_evidence(session, runtime, supplier_id).evidence
        assert set(session.dirty) == pending
        assert not session.new and not session.deleted
        assert project.demo_session_id != demo_session_id
        assert project.brief_revision == persisted_revision + 2
        assert supplier.name == "Pending supplier name"
        assert candidate.project_id != project_id
        assert candidate.evaluated_against_brief_revision == persisted_revision + 1

        with Session(engine) as other_session:
            demo_session = other_session.get(DemoSession, demo_session_id)
            assert demo_session is not None
            demo_session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            other_session.commit()
        _assert_error(ToolErrorCode.NOT_ALLOWED, lambda: get_supplier_snapshot(
            session, runtime, supplier_id
        ))
        _assert_error(ToolErrorCode.NOT_ALLOWED, lambda: get_supplier_evidence(
            session, runtime, supplier_id
        ))
        assert set(session.dirty) == pending
        assert project.demo_session_id != demo_session_id
        assert supplier.name == "Pending supplier name"
        assert candidate.project_id != project_id
    assert runtime.successful_call_count == 2
    assert [event.outcome for event in runtime.trace] == [
        "SUCCESS", "SUCCESS", "NOT_ALLOWED", "NOT_ALLOWED"
    ]


def test_configurable_success_budget_and_trace(client: TestClient, engine: Engine) -> None:
    demo_session_id, project_id, supplier_id = _discovered_project(client, engine)
    with pytest.raises(ValueError):
        AnalystToolContext(demo_session_id, project_id, frozenset({supplier_id}), 0)
    default = AnalystToolContext(demo_session_id, project_id, frozenset({supplier_id}))
    assert default.max_tool_calls == 6
    assert default.permitted_quote_ids == frozenset()
    positional = AnalystToolContext(demo_session_id, project_id, frozenset({supplier_id}), 2)
    assert positional.max_tool_calls == 2
    assert positional.permitted_quote_ids == frozenset()
    allowed_quotes = {uuid4()}
    immutable = AnalystToolContext(
        demo_session_id, project_id, frozenset({supplier_id}),
        permitted_quote_ids=frozenset(allowed_quotes),
    )
    allowed_quotes.add(uuid4())
    assert len(immutable.permitted_quote_ids) == 1
    runtime = _runtime(demo_session_id, project_id, frozenset({supplier_id}), max_tool_calls=2)
    with Session(engine) as session:
        _assert_error(ToolErrorCode.NOT_ALLOWED, lambda: get_supplier_snapshot(
            session, runtime, uuid4()
        ))
        assert runtime.successful_call_count == 0
        get_supplier_snapshot(session, runtime, supplier_id)
        get_supplier_evidence(session, runtime, supplier_id)
        _assert_error(ToolErrorCode.LIMIT_REACHED, lambda: get_supplier_snapshot(
            session, runtime, supplier_id
        ))
        assert not session.dirty and not session.new and not session.deleted
    assert runtime.successful_call_count == 2
    assert [event.outcome for event in runtime.trace] == [
        "NOT_ALLOWED", "SUCCESS", "SUCCESS", "LIMIT_REACHED"
    ]
    assert [event.successful_call_count for event in runtime.trace] == [0, 1, 2, 2]
