"""Candidate retrieval rules and approved-Brief API boundary."""

from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from sourcepilot.main import app
from sourcepilot.persistence.database import get_database_session
from sourcepilot.suppliers.repository import suppliers_in_category
from sourcepilot.suppliers.retrieval import (
    RetrievalRequirement,
    candidate_facts,
    normalize_category,
    order_candidates,
)
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
def reset_database(database_url: str) -> Iterator[None]:
    reset_test_database(database_url)
    yield
    reset_test_database(database_url)


@pytest.fixture
def client(engine: Engine, reset_database: None) -> Iterator[TestClient]:
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_database_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_database_session] = override_database_session
    with TestClient(app, raise_server_exceptions=False) as value:
        yield value
    app.dependency_overrides.clear()


def _create_project(client: TestClient) -> str:
    assert client.post("/demo-session").status_code == 204
    response = client.post(
        "/projects",
        json={"name": "Travel bags", "original_request": "Source recycled cosmetic travel bags."},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _approved_demo_brief(client: TestClient, project_id: str, *, category: str) -> None:
    response = client.patch(
        f"/projects/{project_id}/brief",
        json={
            "product_name": "Cosmetic travel bag",
            "category": category,
            "quantity": 2000,
            "destination": "Sydney",
            "delivery_target": {"kind": "DATE", "date": "2027-01-01"},
            "target_unit_price": None,
            "requirements": [
                {
                    "kind": "MATERIAL",
                    "importance": "REQUIRED",
                    "expected_value": {"value": "recycled polyester"},
                },
                {
                    "kind": "CAPABILITY",
                    "importance": "REQUIRED",
                    "expected_value": {"capability_key": "CUSTOM_BRANDING", "value": True},
                },
                {
                    "kind": "CERTIFICATION",
                    "importance": "PREFERRED",
                    "expected_value": {"value": "grs"},
                },
            ],
        },
    )
    assert response.status_code == 200, response.text
    approved = client.post(
        f"/projects/{project_id}/brief/approve",
        json={"expected_brief_revision": response.json()["brief_revision"]},
    )
    assert approved.status_code == 200, approved.text


@pytest.mark.parametrize(
    "category",
    ["cosmetic bag", "Cosmetic bags", "cosmetic travel bag", "travel bags"],
)
def test_demo_category_aliases(category: str) -> None:
    assert normalize_category(category) == "cosmetic travel bag"


def test_ordering_keeps_moq_failure_and_unknown_without_a_score() -> None:
    candidates = [
        candidate_facts(uuid4(), "Matching with high MOQ", 5000, [("MATERIAL", "linen")]),
        candidate_facts(uuid4(), "Unknown MOQ", None, [("MATERIAL", "linen")]),
        candidate_facts(uuid4(), "Other material", 100, [("MATERIAL", "cotton")]),
    ]
    ordered = order_candidates(
        candidates,
        requirements=[RetrievalRequirement("MATERIAL", {"value": "linen"})],
        quantity=2000,
    )
    assert ordered == [candidates[0].id, candidates[1].id, candidates[2].id]
    assert order_candidates([], requirements=[], quantity=2000) == []


def test_repository_excludes_unrelated_category(engine: Engine, reset_database: None) -> None:
    with Session(engine) as session:
        seed_suppliers(session)
        matches = suppliers_in_category(session, "cosmetic travel bag")
        assert len(matches) == 9
        assert "Coastal Home Textiles" not in {item.name for item in matches}
        assert [item.name for item in matches] == sorted(item.name for item in matches)
        assert len(suppliers_in_category(session, "missing category")) == 0


def test_discovery_requires_approval_then_returns_five_stable_candidates(
    client: TestClient, engine: Engine
) -> None:
    with Session(engine) as session:
        seed_suppliers(session)
        session.commit()
    project_id = _create_project(client)
    endpoint = f"/projects/{project_id}/suppliers/discover"
    blocked = client.post(endpoint)
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "BRIEF_NOT_APPROVED"

    _approved_demo_brief(client, project_id, category="Cosmetic bags")
    response = client.post(endpoint)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["brief_revision"] == 1
    assert len(data["suppliers"]) == 5
    names = [supplier["name"] for supplier in data["suppliers"]]
    assert set(names) == {
        "Harbor Pouch Works",
        "Willow Stitch Studio",
        "Cedar Pack Co",
        "Moss Thread Bags",
        "Sunrise Textile Lab",
    }
    assert "Coastal Home Textiles" not in names
    assert "Cedar Pack Co" in names  # Its general MOQ exceeds the requested quantity.
    assert "Moss Thread Bags" in names  # Its certification is unknown.
    assert "Sunrise Textile Lab" in names  # Its evidence conflicts; U3 evaluates it.
    assert all(UUID(supplier["id"]) for supplier in data["suppliers"])
    assert client.post(endpoint).json() == data


def test_discovery_is_session_scoped(client: TestClient, engine: Engine) -> None:
    with Session(engine) as session:
        seed_suppliers(session)
        session.commit()
    project_id = _create_project(client)
    _approved_demo_brief(client, project_id, category="cosmetic travel bag")
    with TestClient(app, raise_server_exceptions=False) as other_client:
        assert other_client.post("/demo-session").status_code == 204
        response = other_client.post(f"/projects/{project_id}/suppliers/discover")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_discovery_returns_fewer_for_small_category(client: TestClient, engine: Engine) -> None:
    with Session(engine) as session:
        seed_suppliers(session)
        session.commit()
    project_id = _create_project(client)
    _approved_demo_brief(client, project_id, category="home textile pouch")
    response = client.post(f"/projects/{project_id}/suppliers/discover")
    assert response.status_code == 200, response.text
    assert [item["name"] for item in response.json()["suppliers"]] == ["Coastal Home Textiles"]


def test_discovery_returns_empty_for_unrepresented_category(
    client: TestClient, engine: Engine
) -> None:
    with Session(engine) as session:
        seed_suppliers(session)
        session.commit()
    project_id = _create_project(client)
    _approved_demo_brief(client, project_id, category="industrial gloves")
    response = client.post(f"/projects/{project_id}/suppliers/discover")
    assert response.status_code == 200, response.text
    assert response.json()["suppliers"] == []

    # Reading is navigation-safe; only incomplete edits revoke existing approval.
    brief_path = f"/projects/{project_id}/brief"
    before = client.get(brief_path).json()
    assert client.get(f"/projects/{project_id}/suppliers").json()["suppliers"] == []
    assert client.get(brief_path).json() == before
    edit = {key: before[key] for key in (
        "product_name", "quantity", "destination", "delivery_target", "target_unit_price", "requirements",
    )}
    changed = client.patch(brief_path, json={**edit, "category": "cosmetic bags",
                                           "expected_brief_revision": before["brief_revision"]})
    assert changed.status_code == 200, changed.text
    revision = changed.json()["brief_revision"]
    assert revision == before["brief_revision"] + 1
    assert changed.json()["status"] == "APPROVED"
    assert changed.json()["approved_at"] == before["approved_at"]
    incomplete = client.patch(brief_path, json={**edit, "category": None,
                                              "expected_brief_revision": revision})
    assert incomplete.json()["status"] == "IN_PROGRESS"
    assert client.post(f"/projects/{project_id}/suppliers/discover").status_code == 409
    restored = client.patch(brief_path, json={**edit, "category": "cosmetic bags",
                                            "expected_brief_revision": revision + 1})
    assert restored.json()["status"] == "READY_FOR_REVIEW"
    revision = restored.json()["brief_revision"]
    assert revision == before["brief_revision"] + 3
    assert client.post(f"{brief_path}/approve", json={
        "expected_brief_revision": before["brief_revision"],
    }).status_code == 409
    assert client.post(f"{brief_path}/approve", json={"expected_brief_revision": revision}).status_code == 200
    recovered = client.post(f"/projects/{project_id}/suppliers/discover")
    assert recovered.status_code == 200
    assert recovered.json()["suppliers"]
    assert all(not item["stale"] for item in client.get(f"/projects/{project_id}/suppliers").json()["suppliers"])
    client.cookies.clear()
    assert client.post("/demo-session").status_code == 204
    assert client.get(f"/projects/{project_id}/suppliers").status_code == 404
