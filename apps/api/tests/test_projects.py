from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from sourcepilot.main import app
from sourcepilot.persistence.database import get_database_session
from sourcepilot.persistence.models import DemoSession, Project
from sourcepilot.projects.service import create_project, projects_for_demo_session, rename_project
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
def reset_project_database(test_database_url: str) -> Iterator[None]:
    reset_test_database(test_database_url)
    yield
    reset_test_database(test_database_url)


@pytest.fixture
def database_session(test_engine: Engine) -> Iterator[Session]:
    session = sessionmaker(bind=test_engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def api_client(test_engine: Engine) -> Iterator[TestClient]:
    session_factory = sessionmaker(bind=test_engine, expire_on_commit=False)

    def override_database_session() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_database_session] = override_database_session
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()


def test_project_service_creates_lists_and_renames_owned_projects(database_session: Session) -> None:
    now = datetime.now(UTC)
    demo_session = DemoSession(
        opaque_token="service-session",
        last_seen_at=now,
        expires_at=now + timedelta(hours=1),
    )
    database_session.add(demo_session)
    database_session.flush()
    first_project = create_project(
        database_session,
        demo_session,
        name="First project",
        original_request="Source the first item.",
    )
    second_project = create_project(
        database_session,
        demo_session,
        name="Second project",
        original_request="Source the second item.",
    )
    database_session.commit()

    rename_project(database_session, first_project, name="Renamed first project")
    database_session.commit()

    assert [project.id for project in projects_for_demo_session(database_session, demo_session)] == [
        first_project.id,
        second_project.id,
    ]
    assert first_project.name == "Renamed first project"


def test_project_api_creates_lists_reads_and_renames_current_session_projects(
    api_client: TestClient,
) -> None:
    assert api_client.post("/demo-session").status_code == 204

    created = api_client.post(
        "/projects",
        json={
            "name": "  Recycled Cosmetic Travel Bag  ",
            "original_request": "  Source 2,000 recycled cosmetic travel bags.  ",
        },
    )

    assert created.status_code == 201
    project = created.json()
    assert project["name"] == "Recycled Cosmetic Travel Bag"
    assert project["original_request"] == "Source 2,000 recycled cosmetic travel bags."
    assert project["stage"] == "BRIEF"

    listed = api_client.get("/projects")
    read = api_client.get(f"/projects/{project['id']}")
    renamed = api_client.patch(f"/projects/{project['id']}", json={"name": "Travel Bag v2"})

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [project["id"]]
    assert read.status_code == 200
    assert read.json()["original_request"] == project["original_request"]
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Travel Bag v2"
    assert api_client.get(f"/projects/{project['id']}").json()["name"] == "Travel Bag v2"


def test_project_api_rejects_blank_input_and_a_missing_session(api_client: TestClient) -> None:
    assert api_client.post("/projects", json={"name": "Project", "original_request": "Request"}).status_code == 401
    assert api_client.post("/demo-session").status_code == 204

    response = api_client.post("/projects", json={"name": "   ", "original_request": "  "})

    assert response.status_code == 422


def test_api_errors_share_the_stable_contract(api_client: TestClient) -> None:
    missing_session = api_client.post(
        "/projects", json={"name": "Project", "original_request": "Source an item."}
    )
    assert missing_session.status_code == 401
    assert missing_session.json() == {
        "error": {"code": "UNAUTHORIZED", "message": "Demo session is unavailable."}
    }

    assert api_client.post("/demo-session").status_code == 204
    missing_project = api_client.get("/projects/00000000-0000-0000-0000-000000000000")
    assert missing_project.status_code == 404
    assert missing_project.json() == {
        "error": {"code": "NOT_FOUND", "message": "Project not found."}
    }

    invalid_payload = api_client.post("/projects", json={"name": " ", "original_request": "Source."})
    assert invalid_payload.status_code == 422
    assert invalid_payload.json() == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed.",
            "fields": [{"field": "body.name", "message": "Value error, must not be blank"}],
        }
    }

    invalid_path = api_client.get("/projects/not-a-uuid")
    assert invalid_path.status_code == 422
    assert invalid_path.json()["error"]["code"] == "VALIDATION_ERROR"
    assert invalid_path.json()["error"]["fields"][0]["field"] == "path.project_id"


def test_unhandled_api_errors_are_safe_without_a_test_endpoint(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert api_client.post("/demo-session").status_code == 204

    def fail_create_project(*_: object, **__: object) -> None:
        raise RuntimeError("database password must stay private")

    monkeypatch.setattr("sourcepilot.main.create_project", fail_create_project)
    response = api_client.post(
        "/projects", json={"name": "Project", "original_request": "Source an item."}
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "We could not complete that request. Please try again.",
        }
    }
    assert "password" not in response.text


@pytest.mark.parametrize("field", ["name", "original_request"])
@pytest.mark.parametrize("malformed_value", [123, ["not text"], {"text": "not text"}, None])
def test_project_api_rejects_non_string_create_input(
    api_client: TestClient, field: str, malformed_value: object
) -> None:
    assert api_client.post("/demo-session").status_code == 204
    payload: dict[str, object] = {"name": "Project", "original_request": "Source an item."}
    payload[field] = malformed_value

    response = api_client.post("/projects", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["fields"][0]["field"] == f"body.{field}"


@pytest.mark.parametrize("malformed_value", [123, ["not text"], {"text": "not text"}, None])
def test_project_api_rejects_non_string_rename_input(
    api_client: TestClient, malformed_value: object
) -> None:
    assert api_client.post("/demo-session").status_code == 204
    created = api_client.post(
        "/projects", json={"name": "Original name", "original_request": "Source an item."}
    )

    response = api_client.patch(
        f"/projects/{created.json()['id']}", json={"name": malformed_value}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["fields"][0]["field"] == "body.name"


@pytest.mark.parametrize(
    ("method", "name", "expected_status"),
    [
        ("create", f"  {'a' * 255}  ", 201),
        ("create", f"  {'a' * 256}  ", 422),
        ("rename", f"  {'b' * 255}  ", 200),
        ("rename", f"  {'b' * 256}  ", 422),
    ],
)
def test_project_api_applies_name_length_limit_after_trimming(
    api_client: TestClient, method: str, name: str, expected_status: int
) -> None:
    assert api_client.post("/demo-session").status_code == 204

    if method == "create":
        response = api_client.post(
            "/projects", json={"name": name, "original_request": "Source an item."}
        )
    else:
        created = api_client.post(
            "/projects", json={"name": "Original name", "original_request": "Source an item."}
        )
        response = api_client.patch(f"/projects/{created.json()['id']}", json={"name": name})

    assert response.status_code == expected_status
    if expected_status < 300:
        assert response.json()["name"] == name.strip()


def test_project_api_hides_foreign_projects_from_another_session(api_client: TestClient) -> None:
    first_session = api_client.post("/demo-session")
    assert first_session.status_code == 204
    created = api_client.post(
        "/projects",
        json={"name": "Private project", "original_request": "Private request"},
    )
    project_id = created.json()["id"]

    api_client.cookies.clear()
    assert api_client.post("/demo-session").status_code == 204

    assert api_client.get("/projects").json() == []
    assert api_client.get(f"/projects/{project_id}").status_code == 404
    assert api_client.patch(f"/projects/{project_id}", json={"name": "Stolen"}).status_code == 404


def test_project_api_rejects_an_expired_session(
    api_client: TestClient, database_session: Session
) -> None:
    expired_session = DemoSession(
        opaque_token="expired-project-session",
        last_seen_at=datetime.now(UTC) - timedelta(days=2),
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    database_session.add(expired_session)
    database_session.commit()
    api_client.cookies.set("sourcepilot_demo_session", expired_session.opaque_token)

    assert api_client.get("/projects").status_code == 401


def test_project_service_limits_listing_to_the_active_session(database_session: Session) -> None:
    now = datetime.now(UTC)
    session_a = DemoSession(
        opaque_token="a", last_seen_at=now, expires_at=now + timedelta(hours=1)
    )
    session_b = DemoSession(
        opaque_token="b", last_seen_at=now, expires_at=now + timedelta(hours=1)
    )
    database_session.add_all([session_a, session_b])
    database_session.flush()
    database_session.add_all(
        [
            Project(demo_session=session_a, name="A", original_request="A request"),
            Project(demo_session=session_b, name="B", original_request="B request"),
        ]
    )
    database_session.commit()

    assert [project.name for project in projects_for_demo_session(database_session, session_a)] == ["A"]
    assert database_session.scalar(select(Project.name).where(Project.demo_session_id == session_b.id)) == "B"
