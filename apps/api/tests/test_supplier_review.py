"""Persisted supplier review and brief-revision integration tests."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from threading import Event, current_thread
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from sourcepilot.main import app
from sourcepilot.persistence.database import get_database_session
from sourcepilot.persistence.models import (
    Project,
    ProjectSupplier,
    RequirementEvaluationRecord,
    SupplierCapability,
)
from sourcepilot.suppliers.schemas import UpdateSupplierReviewRequest
from sourcepilot.suppliers.seed import seed_suppliers
from sourcepilot.suppliers.service import (
    ShortlistApprovalError,
    approve_shortlist,
    list_project_suppliers,
    update_supplier_review,
)
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


def create_project(client: TestClient) -> str:
    response = client.post(
        "/projects", json={"name": "Bags", "original_request": "Source cosmetic bags."}
    )
    assert response.status_code == 201
    return response.json()["id"]


def brief_payload(*, category: str = "cosmetic travel bag", quantity: int = 2000) -> dict[str, object]:
    return {
        "product_name": "Cosmetic bag", "category": category, "quantity": quantity,
        "destination": "Sydney", "delivery_target": {"kind": "DATE", "date": "2027-01-01"},
        "target_unit_price": None,
        "requirements": [
            {"kind": "MATERIAL", "importance": "REQUIRED", "expected_value": {"value": "recycled polyester"}},
            {"kind": "CAPABILITY", "importance": "REQUIRED", "expected_value": {"capability_key": "CUSTOM_BRANDING", "value": True}},
            {"kind": "CERTIFICATION", "importance": "PREFERRED", "expected_value": {"value": "grs"}},
        ],
    }


def approve(client: TestClient, project_id: str, revision: int) -> None:
    response = client.post(
        f"/projects/{project_id}/brief/approve", json={"expected_brief_revision": revision}
    )
    assert response.status_code == 200, response.text


def test_discovery_persists_requirement_results_and_separates_derived_context(
    client: TestClient, engine: Engine,
) -> None:
    project_id = create_project(client)
    assert client.get(f"/projects/{project_id}/suppliers").json()["suppliers"] == []
    blocked = client.post(f"/projects/{project_id}/suppliers/discover")
    assert blocked.status_code == 409
    edited = client.patch(f"/projects/{project_id}/brief", json=brief_payload()).json()
    approve(client, project_id, edited["brief_revision"])
    discovered = client.post(f"/projects/{project_id}/suppliers/discover")
    assert discovered.status_code == 200, discovered.text
    listed = client.get(f"/projects/{project_id}/suppliers").json()
    assert len(listed["suppliers"]) == 5
    assert all(not item["stale"] for item in listed["suppliers"])
    assert all(len(item["evaluations"]) == 3 for item in listed["suppliers"])
    assert all(item["derived_context"][0]["kind"] == "MOQ" for item in listed["suppliers"])
    sunrise = next(item for item in listed["suppliers"] if item["name"] == "Sunrise Textile Lab")
    assert next(item for item in sunrise["evaluations"] if item["kind"] == "CERTIFICATION")["status"] == "CONFLICT"
    assert sunrise["evidence"]
    with Session(engine) as session:
        project_suppliers = list(session.scalars(
            select(ProjectSupplier).where(ProjectSupplier.project_id == UUID(project_id))
        ))
        evaluations = list(session.scalars(
            select(RequirementEvaluationRecord).where(RequirementEvaluationRecord.project_id == UUID(project_id))
        ))
    assert len(project_suppliers) == 5
    assert {item.evaluated_against_brief_revision for item in project_suppliers} == {edited["brief_revision"]}
    assert len(evaluations) == 15
    assert all(item.requirement_id is not None for item in evaluations)


def test_staleness_refresh_and_disappeared_candidate_state(
    client: TestClient, engine: Engine,
) -> None:
    project_id = create_project(client)
    edited = client.patch(f"/projects/{project_id}/brief", json=brief_payload()).json()
    approve(client, project_id, edited["brief_revision"])
    assert client.post(f"/projects/{project_id}/suppliers/discover").status_code == 200
    listed = client.get(f"/projects/{project_id}/suppliers").json()["suppliers"]
    lost = listed[0]
    returning = listed[1]
    assert client.patch(
        f"/projects/{project_id}/suppliers/{lost['id']}",
        json={"shortlisted": True, "notes": "Remove after category change"},
    ).status_code == 200
    assert client.patch(
        f"/projects/{project_id}/suppliers/{returning['id']}",
        json={"dismissed": True, "notes": "Keep if returned"},
    ).status_code == 200
    updated = client.patch(
        f"/projects/{project_id}/brief", json=brief_payload(quantity=3000)
    ).json()
    stale = client.get(f"/projects/{project_id}/suppliers").json()
    assert all(item["stale"] and item["evaluations"] == [] and item["derived_context"] == [] for item in stale["suppliers"])
    assert next(item for item in stale["suppliers"] if item["id"] == lost["id"])["notes"] == "Remove after category change"
    if not stale["brief_approved"]:
        approve(client, project_id, updated["brief_revision"])
    assert client.post(f"/projects/{project_id}/suppliers/discover").status_code == 200
    fresh = client.get(f"/projects/{project_id}/suppliers").json()
    assert all(not item["stale"] for item in fresh["suppliers"])
    assert next(item for item in fresh["suppliers"] if item["id"] == returning["id"])["notes"] == "Keep if returned"

    changed = client.patch(
        f"/projects/{project_id}/brief", json=brief_payload(category="home textile pouch")
    ).json()
    if changed["status"] != "APPROVED":
        approve(client, project_id, changed["brief_revision"])
    assert client.post(f"/projects/{project_id}/suppliers/discover").status_code == 200
    after = client.get(f"/projects/{project_id}/suppliers").json()["suppliers"]
    assert [item["name"] for item in after] == ["Coastal Home Textiles"]
    with Session(engine) as session:
        removed = session.get(ProjectSupplier, (UUID(project_id), UUID(lost["id"])))
    assert removed is None
    assert client.patch(f"/projects/{project_id}/suppliers/{lost['id']}", json={"notes": "No"}).status_code == 404

    restored_brief = client.patch(
        f"/projects/{project_id}/brief", json=brief_payload()
    ).json()
    if restored_brief["status"] != "APPROVED":
        approve(client, project_id, restored_brief["brief_revision"])
    assert client.post(f"/projects/{project_id}/suppliers/discover").status_code == 200
    reappeared = next(
        item for item in client.get(f"/projects/{project_id}/suppliers").json()["suppliers"]
        if item["id"] == lost["id"]
    )
    assert reappeared["notes"] is None
    assert not reappeared["shortlisted"]
    assert not reappeared["dismissed"]


def test_review_is_scoped_and_exclusive(client: TestClient) -> None:
    project_id = create_project(client)
    edited = client.patch(f"/projects/{project_id}/brief", json=brief_payload()).json()
    approve(client, project_id, edited["brief_revision"])
    assert client.post(f"/projects/{project_id}/suppliers/discover").status_code == 200
    supplier_id = client.get(f"/projects/{project_id}/suppliers").json()["suppliers"][0]["id"]
    selected = client.patch(f"/projects/{project_id}/suppliers/{supplier_id}", json={"shortlisted": True}).json()
    assert selected["suppliers"][0]["shortlisted"]
    dismissed = client.patch(f"/projects/{project_id}/suppliers/{supplier_id}", json={"dismissed": True}).json()
    assert dismissed["suppliers"][0]["dismissed"]
    assert not dismissed["suppliers"][0]["shortlisted"]
    assert client.patch(f"/projects/{project_id}/suppliers/{uuid4()}", json={"notes": "No"}).status_code == 404
    with TestClient(app, raise_server_exceptions=False) as other:
        assert other.post("/demo-session").status_code == 204
        assert other.get(f"/projects/{project_id}/suppliers").status_code == 404
        assert other.patch(f"/projects/{project_id}/suppliers/{supplier_id}", json={"notes": "No"}).status_code == 404


def test_listing_refreshes_a_project_loaded_before_a_brief_edit(
    client: TestClient, engine: Engine,
) -> None:
    project_id = create_project(client)
    edited = client.patch(f"/projects/{project_id}/brief", json=brief_payload()).json()
    approve(client, project_id, edited["brief_revision"])
    assert client.post(f"/projects/{project_id}/suppliers/discover").status_code == 200

    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        old_revision = project.brief_revision
        changed = client.patch(
            f"/projects/{project_id}/brief", json=brief_payload(quantity=3000)
        ).json()
        assert changed["brief_revision"] > old_revision

        listed = list_project_suppliers(session, project)
        assert listed.brief_revision == changed["brief_revision"]
        assert all(item.stale and not item.evaluations for item in listed.suppliers)
        session.commit()


def test_review_update_uses_locked_revision_after_a_brief_edit(
    client: TestClient, engine: Engine,
) -> None:
    project_id = create_project(client)
    edited = client.patch(f"/projects/{project_id}/brief", json=brief_payload()).json()
    approve(client, project_id, edited["brief_revision"])
    assert client.post(f"/projects/{project_id}/suppliers/discover").status_code == 200
    supplier_id = client.get(f"/projects/{project_id}/suppliers").json()["suppliers"][0]["id"]

    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        old_revision = project.brief_revision
        changed = client.patch(
            f"/projects/{project_id}/brief", json=brief_payload(quantity=3000)
        ).json()
        assert changed["brief_revision"] > old_revision

        listed = update_supplier_review(
            session, project, UUID(supplier_id), UpdateSupplierReviewRequest(notes="Still relevant")
        )
        assert listed.brief_revision == changed["brief_revision"]
        assert all(item.stale and not item.evaluations for item in listed.suppliers)
        reviewed = next(item for item in listed.suppliers if item.id == UUID(supplier_id))
        assert reviewed.notes == "Still relevant"
        session.commit()


def test_shortlist_approval_count_and_explicit_stage_transition(client: TestClient) -> None:
    project_id = create_project(client)
    endpoint = f"/projects/{project_id}/shortlist/approve"
    assert client.post(endpoint).status_code == 409
    edited = client.patch(f"/projects/{project_id}/brief", json=brief_payload()).json()
    approve(client, project_id, edited["brief_revision"])
    assert client.post(f"/projects/{project_id}/suppliers/discover").status_code == 200
    suppliers = client.get(f"/projects/{project_id}/suppliers").json()["suppliers"]
    assert client.post(endpoint).status_code == 409
    for item in suppliers[:4]:
        selected = client.patch(
            f"/projects/{project_id}/suppliers/{item['id']}", json={"shortlisted": True}
        )
        assert selected.status_code == 200
    too_many = client.post(endpoint)
    assert too_many.status_code == 409
    assert too_many.json()["error"]["code"] == "SHORTLIST_NOT_READY"
    assert client.get(f"/projects/{project_id}").json()["stage"] == "SUPPLIERS"

    client.patch(f"/projects/{project_id}/suppliers/{suppliers[3]['id']}", json={"shortlisted": False})
    approved = client.post(endpoint)
    assert approved.status_code == 200
    assert approved.json()["shortlist_approved"]
    assert client.get(f"/projects/{project_id}").json()["stage"] == "QUOTES"
    assert client.post(endpoint).status_code == 200

    # A review note does not change approval; removing one selected supplier does.
    client.patch(f"/projects/{project_id}/suppliers/{suppliers[0]['id']}", json={"notes": "Reviewed"})
    assert client.get(f"/projects/{project_id}").json()["stage"] == "QUOTES"
    removed = client.patch(
        f"/projects/{project_id}/suppliers/{suppliers[0]['id']}", json={"shortlisted": False}
    )
    assert not removed.json()["shortlist_approved"]
    assert client.get(f"/projects/{project_id}").json()["stage"] == "SUPPLIERS"
    assert client.post(endpoint).status_code == 200  # Two suppliers are valid.
    client.patch(f"/projects/{project_id}/suppliers/{suppliers[1]['id']}", json={"shortlisted": False})
    assert client.post(endpoint).status_code == 200  # One supplier is valid.


def test_unchanged_brief_approval_retry_preserves_approved_shortlist(client: TestClient) -> None:
    project_id = create_project(client)
    edited = client.patch(f"/projects/{project_id}/brief", json=brief_payload()).json()
    revision = edited["brief_revision"]
    approve(client, project_id, revision)
    assert client.post(f"/projects/{project_id}/suppliers/discover").status_code == 200
    supplier_id = client.get(f"/projects/{project_id}/suppliers").json()["suppliers"][0]["id"]
    client.patch(f"/projects/{project_id}/suppliers/{supplier_id}", json={"shortlisted": True})
    assert client.post(f"/projects/{project_id}/shortlist/approve").status_code == 200
    before = client.get(f"/projects/{project_id}/brief").json()

    retry = client.post(
        f"/projects/{project_id}/brief/approve", json={"expected_brief_revision": revision}
    )
    assert retry.status_code == 200
    assert retry.json() == before
    assert client.get(f"/projects/{project_id}").json()["stage"] == "QUOTES"
    listed = client.get(f"/projects/{project_id}/suppliers").json()
    assert listed["shortlist_approved"]
    assert [item["id"] for item in listed["suppliers"] if item["shortlisted"]] == [supplier_id]


def test_dismiss_restore_requires_explicit_reapproval(client: TestClient) -> None:
    project_id = create_project(client)
    edited = client.patch(f"/projects/{project_id}/brief", json=brief_payload()).json()
    approve(client, project_id, edited["brief_revision"])
    client.post(f"/projects/{project_id}/suppliers/discover")
    supplier_id = client.get(f"/projects/{project_id}/suppliers").json()["suppliers"][0]["id"]
    supplier_url = f"/projects/{project_id}/suppliers/{supplier_id}"
    client.patch(supplier_url, json={"shortlisted": True})
    endpoint = f"/projects/{project_id}/shortlist/approve"
    assert client.post(endpoint).json()["shortlist_approved"]

    dismissed = client.patch(supplier_url, json={"dismissed": True}).json()
    assert dismissed["suppliers"][0]["dismissed"]
    assert not dismissed["suppliers"][0]["shortlisted"]
    assert not dismissed["shortlist_approved"]
    assert client.get(f"/projects/{project_id}").json()["stage"] == "SUPPLIERS"
    restored = client.patch(supplier_url, json={"dismissed": False}).json()
    assert not restored["shortlist_approved"]
    assert not restored["suppliers"][0]["shortlisted"]
    assert client.post(endpoint).status_code == 409
    client.patch(supplier_url, json={"shortlisted": True})
    assert client.get(f"/projects/{project_id}").json()["stage"] == "SUPPLIERS"
    assert client.post(endpoint).json()["shortlist_approved"]
    assert client.get(f"/projects/{project_id}").json()["stage"] == "QUOTES"


def test_brief_edit_requires_refresh_before_shortlist_reapproval(client: TestClient) -> None:
    project_id = create_project(client)
    edited = client.patch(f"/projects/{project_id}/brief", json=brief_payload()).json()
    approve(client, project_id, edited["brief_revision"])
    client.post(f"/projects/{project_id}/suppliers/discover")
    supplier_id = client.get(f"/projects/{project_id}/suppliers").json()["suppliers"][0]["id"]
    client.patch(f"/projects/{project_id}/suppliers/{supplier_id}", json={"shortlisted": True})
    endpoint = f"/projects/{project_id}/shortlist/approve"
    assert client.post(endpoint).status_code == 200
    changed = client.patch(f"/projects/{project_id}/brief", json=brief_payload(quantity=2500)).json()
    assert client.get(f"/projects/{project_id}").json()["stage"] == "SUPPLIERS"
    assert client.post(endpoint).status_code == 409
    if changed["status"] != "APPROVED":
        approve(client, project_id, changed["brief_revision"])
    client.post(f"/projects/{project_id}/suppliers/discover")
    assert client.post(endpoint).status_code == 200


def test_shortlist_approval_is_session_scoped(client: TestClient) -> None:
    project_id = create_project(client)
    with TestClient(app, raise_server_exceptions=False) as other:
        assert other.post("/demo-session").status_code == 204
        assert other.post(f"/projects/{project_id}/shortlist/approve").status_code == 404


def test_rediscovery_revokes_approval_if_selected_candidate_disappears(
    client: TestClient, engine: Engine,
) -> None:
    project_id = create_project(client)
    edited = client.patch(f"/projects/{project_id}/brief", json=brief_payload()).json()
    approve(client, project_id, edited["brief_revision"])
    client.post(f"/projects/{project_id}/suppliers/discover")
    supplier_id = client.get(f"/projects/{project_id}/suppliers").json()["suppliers"][0]["id"]
    client.patch(f"/projects/{project_id}/suppliers/{supplier_id}", json={"shortlisted": True})
    assert client.post(f"/projects/{project_id}/shortlist/approve").status_code == 200

    with Session(engine) as session:
        category = session.scalar(select(SupplierCapability).where(
            SupplierCapability.supplier_id == UUID(supplier_id),
            SupplierCapability.capability_kind == "PRODUCT_CATEGORY",
        ))
        assert category is not None
        category.value = "different category"
        session.commit()
    assert client.post(f"/projects/{project_id}/suppliers/discover").status_code == 200
    listed = client.get(f"/projects/{project_id}/suppliers").json()
    assert not listed["shortlist_approved"]
    assert supplier_id not in {item["id"] for item in listed["suppliers"]}
    assert client.get(f"/projects/{project_id}").json()["stage"] == "SUPPLIERS"


@pytest.mark.parametrize("first_action", ["change", "approve"])
def test_overlapping_shortlist_change_and_approval_preserve_valid_stage(
    client: TestClient, engine: Engine,
    first_action: str,
) -> None:
    project_id = create_project(client)
    edited = client.patch(f"/projects/{project_id}/brief", json=brief_payload()).json()
    approve(client, project_id, edited["brief_revision"])
    client.post(f"/projects/{project_id}/suppliers/discover")
    supplier_id = client.get(f"/projects/{project_id}/suppliers").json()["suppliers"][0]["id"]
    client.patch(f"/projects/{project_id}/suppliers/{supplier_id}", json={"shortlisted": True})
    first_locked = Event()
    second_entered_lock = Event()
    release_first = Event()

    def before_lock(conn: object, cursor: object, statement: str, parameters: object,
                    context: object, executemany: bool) -> None:
        if ("FROM projects" in statement and "FOR UPDATE" in statement
                and current_thread().name.endswith("_1")):
            second_entered_lock.set()

    def after_lock(conn: object, cursor: object, statement: str, parameters: object,
                   context: object, executemany: bool) -> None:
        if ("FROM projects" in statement and "FOR UPDATE" in statement
                and current_thread().name.endswith("_0") and not first_locked.is_set()):
            first_locked.set()
            assert release_first.wait(10), "First operation was not released"

    def run_action(action: str) -> str:
        with Session(engine) as session:
            project = session.get(Project, UUID(project_id))
            assert project is not None
            if action == "change":
                update_supplier_review(
                    session, project, UUID(supplier_id),
                    UpdateSupplierReviewRequest(shortlisted=False),
                )
            else:
                try:
                    approve_shortlist(session, project)
                except ShortlistApprovalError:
                    return "rejected"
            session.commit()
            return "committed"

    event.listen(engine, "before_cursor_execute", before_lock)
    event.listen(engine, "after_cursor_execute", after_lock)
    try:
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="shortlist-race") as pool:
            first = pool.submit(run_action, first_action)
            assert first_locked.wait(10), "First operation did not acquire the project lock"
            second = pool.submit(run_action, "approve" if first_action == "change" else "change")
            try:
                assert second_entered_lock.wait(10), "Second operation did not overlap the lock"
            finally:
                release_first.set()
            assert first.result(timeout=10) == "committed"
            assert second.result(timeout=10) == (
                "rejected" if first_action == "change" else "committed"
            )
    finally:
        release_first.set()
        event.remove(engine, "before_cursor_execute", before_lock)
        event.remove(engine, "after_cursor_execute", after_lock)

    listed = client.get(f"/projects/{project_id}/suppliers").json()
    assert not listed["shortlist_approved"]
    assert not any(item["shortlisted"] for item in listed["suppliers"])
    assert client.get(f"/projects/{project_id}").json()["stage"] == "SUPPLIERS"
