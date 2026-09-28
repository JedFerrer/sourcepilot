"""Manual quote API lifecycle and isolation tests."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event
from sqlalchemy.orm import Session, sessionmaker

from sourcepilot.main import app
from sourcepilot.persistence.database import get_database_session
from sourcepilot.quotes.domain import QUOTE_FIELD_KEYS
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


def setup_shortlist(client: TestClient, *, approve_shortlist: bool = True) -> tuple[str, str, str]:
    project = client.post("/projects", json={
        "name": "Bags", "original_request": "Source cosmetic travel bags.",
    })
    assert project.status_code == 201
    project_id = project.json()["id"]
    brief = client.patch(f"/projects/{project_id}/brief", json={
        "product_name": "Cosmetic bag", "category": "cosmetic travel bag", "quantity": 2000,
        "destination": "Sydney", "delivery_target": {"kind": "DATE", "date": "2027-01-01"},
        "target_unit_price": None,
        "requirements": [
            {"kind": "MATERIAL", "importance": "REQUIRED", "expected_value": {"value": "recycled polyester"}},
            {"kind": "CAPABILITY", "importance": "REQUIRED", "expected_value": {"capability_key": "CUSTOM_BRANDING", "value": True}},
            {"kind": "CERTIFICATION", "importance": "PREFERRED", "expected_value": {"value": "grs"}},
        ],
    })
    assert brief.status_code == 200
    approved = client.post(f"/projects/{project_id}/brief/approve", json={
        "expected_brief_revision": brief.json()["brief_revision"],
    })
    assert approved.status_code == 200
    assert client.post(f"/projects/{project_id}/suppliers/discover").status_code == 200
    suppliers = client.get(f"/projects/{project_id}/suppliers").json()["suppliers"]
    selected, other = suppliers[0]["id"], suppliers[1]["id"]
    assert client.patch(
        f"/projects/{project_id}/suppliers/{selected}", json={"shortlisted": True},
    ).status_code == 200
    if approve_shortlist:
        assert client.post(f"/projects/{project_id}/shortlist/approve").status_code == 200
    return project_id, selected, other


def test_manual_quote_create_patch_confirm_and_edit_lock(client: TestClient) -> None:
    project_id, supplier_id, _ = setup_shortlist(client)
    create = client.post(f"/projects/{project_id}/quotes/manual", json={
        "supplier_id": supplier_id, "values": {
            "quoted_quantity": 2000, "unit_price": "4.25", "currency": "usd",
            "shipping_cost": None,
        }, "notes": "Initial note",
    })
    assert create.status_code == 201, create.text
    quote = create.json()
    quote_id = quote["id"]
    assert quote["status"] == "NEEDS_REVIEW"
    assert quote["revision"] == 0
    assert quote["confirmed_at"] is None
    assert set(quote["values"]) == QUOTE_FIELD_KEYS
    assert quote["values"]["currency"]["current_value"] == "USD"
    assert quote["values"]["moq"] == {
        "current_value": None, "current_origin": "USER_ENTERED", "ai_extracted_value": None,
        "uncertainty": None, "review_state": "UNKNOWN", "evidence": [], "conflicting_values": [],
    }
    assert quote["values"]["shipping_cost"]["current_value"] is None
    assert len(client.get(f"/projects/{project_id}/quotes").json()) == 1
    assert client.get(f"/quotes/{quote_id}").json()["id"] == quote_id
    assert client.post(f"/projects/{project_id}/quotes/manual", json={
        "supplier_id": supplier_id,
    }).status_code == 409

    patched = client.patch(f"/quotes/{quote_id}", json={
        "values": {"unit_price": "4.50", "quoted_quantity": None}, "notes": None,
    })
    assert patched.status_code == 200, patched.text
    changed = patched.json()
    assert changed["values"]["unit_price"]["current_value"] == "4.50"
    assert changed["values"]["quoted_quantity"]["current_value"] is None
    assert changed["values"]["currency"]["current_value"] == "USD"
    assert changed["notes"] is None
    untouched = client.patch(f"/quotes/{quote_id}", json={"values": {}}).json()
    assert untouched["values"] == changed["values"]
    assert untouched["notes"] is None

    confirmed = client.post(f"/quotes/{quote_id}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "CONFIRMED"
    assert confirmed.json()["confirmed_at"] is not None
    assert confirmed.json()["revision"] == 0
    assert client.patch(f"/quotes/{quote_id}", json={"values": {"unit_price": "5"}}).status_code == 409
    assert client.post(f"/quotes/{quote_id}/confirm").status_code == 409
    assert client.get(f"/quotes/{quote_id}").json()["values"]["unit_price"]["current_value"] == "4.50"


def test_manual_quote_reads_do_not_query_pdf_evidence(client: TestClient, engine: Engine) -> None:
    project_id, supplier_id, _ = setup_shortlist(client)
    created = client.post(f"/projects/{project_id}/quotes/manual", json={
        "supplier_id": supplier_id, "values": {"unit_price": "4.25"},
    })
    assert created.status_code == 201
    statements: list[str] = []

    def record_query(_: object, __: object, statement: str, *args: object) -> None:
        if statement.lstrip().lower().startswith("select"):
            statements.append(statement.lower())

    event.listen(engine, "before_cursor_execute", record_query)
    try:
        assert client.get(f"/quotes/{created.json()['id']}").status_code == 200
        assert client.get(f"/projects/{project_id}/quotes").status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", record_query)
    assert not any("quote_field_evidence" in query for query in statements)
    assert not any("document_blocks" in query for query in statements)
    assert not any("quote_documents" in query for query in statements)


def test_all_unknown_confirmation_and_stage_shortlist_guards(client: TestClient) -> None:
    project_id, selected, other = setup_shortlist(client, approve_shortlist=False)
    endpoint = f"/projects/{project_id}/quotes/manual"
    assert client.post(endpoint, json={"supplier_id": selected}).status_code == 409
    assert client.post(f"/projects/{project_id}/shortlist/approve").status_code == 200
    assert client.post(endpoint, json={"supplier_id": other}).status_code == 409
    created = client.post(endpoint, json={"supplier_id": selected})
    assert created.status_code == 201, created.text
    assert all(field["current_value"] is None for field in created.json()["values"].values())
    quote_id = created.json()["id"]
    assert client.post(f"/quotes/{quote_id}/confirm").status_code == 200


def test_manual_quote_validation_and_session_isolation(client: TestClient) -> None:
    project_id, selected, _ = setup_shortlist(client)
    endpoint = f"/projects/{project_id}/quotes/manual"
    for values in ({"invented": "x"}, {"quoted_quantity": -1}, {"unit_price": "bad"}):
        assert client.post(endpoint, json={"supplier_id": selected, "values": values}).status_code == 422
    created = client.post(endpoint, json={"supplier_id": selected})
    quote_id = created.json()["id"]
    assert client.patch(f"/quotes/{quote_id}", json={"values": {"moq": 0}}).status_code == 422
    with TestClient(app, raise_server_exceptions=False) as other:
        assert other.post("/demo-session").status_code == 204
        assert other.get(f"/projects/{project_id}/quotes").status_code == 404
        assert other.post(endpoint, json={"supplier_id": selected}).status_code == 404
        assert other.get(f"/quotes/{quote_id}").status_code == 404
        assert other.patch(f"/quotes/{quote_id}", json={"values": {}}).status_code == 404
        assert other.post(f"/quotes/{quote_id}/confirm").status_code == 404


def test_confirmation_rechecks_current_shortlist(client: TestClient) -> None:
    project_id, selected, _ = setup_shortlist(client)
    created = client.post(f"/projects/{project_id}/quotes/manual", json={
        "supplier_id": selected,
    })
    assert created.status_code == 201
    quote_id = created.json()["id"]
    assert client.patch(
        f"/projects/{project_id}/suppliers/{selected}", json={"shortlisted": False},
    ).status_code == 200
    assert client.post(f"/quotes/{quote_id}/confirm").status_code == 409
    assert client.get(f"/quotes/{quote_id}").json()["status"] == "NEEDS_REVIEW"


def test_patch_rechecks_current_shortlist(client: TestClient) -> None:
    project_id, selected, other = setup_shortlist(client)
    created = client.post(f"/projects/{project_id}/quotes/manual", json={
        "supplier_id": selected, "values": {"unit_price": "4.25"}, "notes": "Original",
    })
    assert created.status_code == 201
    quote_id = created.json()["id"]
    assert client.patch(
        f"/projects/{project_id}/suppliers/{selected}", json={"shortlisted": False},
    ).status_code == 200
    assert client.patch(
        f"/projects/{project_id}/suppliers/{other}", json={"shortlisted": True},
    ).status_code == 200
    assert client.post(f"/projects/{project_id}/shortlist/approve").status_code == 200

    patched = client.patch(f"/quotes/{quote_id}", json={
        "values": {"unit_price": "5.00"}, "notes": "Changed",
    })
    assert patched.status_code == 409
    assert patched.json()["error"]["code"] == "QUOTE_NOT_EDITABLE"
    assert client.get(f"/quotes/{quote_id}").json() == created.json()


def test_patch_requires_current_quotes_stage(client: TestClient) -> None:
    project_id, selected, other = setup_shortlist(client, approve_shortlist=False)
    assert client.patch(
        f"/projects/{project_id}/suppliers/{other}", json={"shortlisted": True},
    ).status_code == 200
    assert client.post(f"/projects/{project_id}/shortlist/approve").status_code == 200
    created = client.post(f"/projects/{project_id}/quotes/manual", json={
        "supplier_id": selected, "values": {"unit_price": "4.25"},
    })
    assert created.status_code == 201
    quote_id = created.json()["id"]
    assert client.patch(
        f"/projects/{project_id}/suppliers/{other}", json={"shortlisted": False},
    ).status_code == 200

    patched = client.patch(f"/quotes/{quote_id}", json={"values": {"unit_price": "5.00"}})
    assert patched.status_code == 409
    assert patched.json()["error"]["code"] == "QUOTE_NOT_EDITABLE"
    assert client.get(f"/quotes/{quote_id}").json() == created.json()
