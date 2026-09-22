from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from sourcepilot.main import app
from sourcepilot.persistence.database import get_database_session
from sourcepilot.persistence.models import DemoSession, Project
from sourcepilot.session.service import (
    create_demo_session,
    project_for_current_demo_session,
    project_for_resolved_demo_session,
    resolve_demo_session,
)
from sourcepilot.session.settings import (
    DEMO_SESSION_COOKIE_NAME,
    DemoSessionSettings,
    demo_session_settings_from_environment,
)
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
def reset_demo_session_database(test_database_url: str) -> Iterator[None]:
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
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def make_demo_session(token: str, *, expires_at: datetime) -> DemoSession:
    return DemoSession(opaque_token=token, last_seen_at=expires_at - timedelta(hours=1), expires_at=expires_at)


def make_project(demo_session: DemoSession, name: str) -> Project:
    return Project(
        demo_session=demo_session,
        name=name,
        original_request=f"Source {name}.",
    )


def test_demo_session_settings_default_to_a_24_hour_local_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEMO_SESSION_TTL_SECONDS", raising=False)
    monkeypatch.delenv("DEMO_SESSION_COOKIE_SECURE", raising=False)

    assert demo_session_settings_from_environment() == DemoSessionSettings(
        ttl_seconds=86_400, cookie_secure=False
    )


@pytest.mark.parametrize("value", ["0", "-1", "not-a-number"])
def test_demo_session_settings_reject_invalid_ttl(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("DEMO_SESSION_TTL_SECONDS", value)

    with pytest.raises(RuntimeError, match="DEMO_SESSION_TTL_SECONDS must be a positive integer"):
        demo_session_settings_from_environment()


def test_first_request_creates_a_session_and_sets_a_local_session_cookie(
    api_client: TestClient,
    database_session: Session,
) -> None:
    response = api_client.post("/demo-session")

    assert response.status_code == 204
    assert response.content == b""
    set_cookie = response.headers["set-cookie"]
    assert f"{DEMO_SESSION_COOKIE_NAME}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Path=/" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Max-Age=86400" in set_cookie
    assert "Domain=" not in set_cookie
    assert "Secure" not in set_cookie
    assert database_session.scalar(select(func.count()).select_from(DemoSession)) == 1


def test_valid_session_reuse_updates_last_seen_without_renewing_expiry_or_cookie(
    api_client: TestClient,
    database_session: Session,
) -> None:
    initial_response = api_client.post("/demo-session")
    token = api_client.cookies.get(DEMO_SESSION_COOKIE_NAME)
    assert token is not None
    original_session = database_session.scalar(
        select(DemoSession).where(DemoSession.opaque_token == token)
    )
    assert original_session is not None
    original_expiry = original_session.expires_at
    original_last_seen = original_session.last_seen_at

    response = api_client.post("/demo-session")
    database_session.expire_all()
    reloaded_session = database_session.scalar(
        select(DemoSession).where(DemoSession.opaque_token == token)
    )

    assert initial_response.status_code == 204
    assert response.status_code == 204
    assert "set-cookie" not in response.headers
    assert reloaded_session is not None
    assert reloaded_session.expires_at == original_expiry
    assert reloaded_session.last_seen_at >= original_last_seen
    assert database_session.scalar(select(func.count()).select_from(DemoSession)) == 1


def test_expired_cookie_creates_a_fresh_session_without_exposing_a_token(
    api_client: TestClient,
    database_session: Session,
) -> None:
    now = datetime.now(UTC)
    expired_session = make_demo_session("expired-token", expires_at=now - timedelta(seconds=1))
    database_session.add(expired_session)
    database_session.commit()
    api_client.cookies.set(
        DEMO_SESSION_COOKIE_NAME,
        expired_session.opaque_token,
        domain="testserver.local",
        path="/",
    )

    response = api_client.post("/demo-session")

    assert response.status_code == 204
    assert response.content == b""
    assert expired_session.opaque_token not in response.text
    assert (
        api_client.cookies.get(DEMO_SESSION_COOKIE_NAME, domain="testserver.local", path="/")
        != expired_session.opaque_token
    )
    assert database_session.scalar(select(func.count()).select_from(DemoSession)) == 2


def test_production_cookie_configuration_sets_secure_flag(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEMO_SESSION_COOKIE_SECURE", "true")

    response = api_client.post("/demo-session")

    assert response.status_code == 204
    assert "Secure" in response.headers["set-cookie"]


def test_session_expiry_boundary_is_not_authorized(database_session: Session) -> None:
    now = datetime.now(UTC)
    expired_session = make_demo_session("expired", expires_at=now)
    database_session.add(expired_session)
    database_session.commit()

    assert resolve_demo_session(database_session, "expired", now=now) is None


def test_session_isolation_requires_a_resolved_session_and_project_ownership(
    database_session: Session,
) -> None:
    now = datetime.now(UTC)
    session_a = make_demo_session("session-a", expires_at=now + timedelta(hours=1))
    session_b = make_demo_session("session-b", expires_at=now + timedelta(hours=1))
    project_a = make_project(session_a, "Project A")
    project_b = make_project(session_b, "Project B")
    database_session.add_all([project_a, project_b])
    database_session.commit()

    resolved_session_a = resolve_demo_session(database_session, "session-a", now=now)

    assert resolved_session_a is not None
    assert project_for_resolved_demo_session(database_session, resolved_session_a, project_a.id) == project_a
    assert project_for_resolved_demo_session(database_session, resolved_session_a, project_b.id) is None


def test_expired_session_fails_resolution_and_cannot_access_its_project(
    database_session: Session,
) -> None:
    now = datetime.now(UTC)
    expired_session = make_demo_session("expired", expires_at=now - timedelta(seconds=1))
    project = make_project(expired_session, "Expired project")
    database_session.add(project)
    database_session.commit()

    assert resolve_demo_session(database_session, expired_session.opaque_token, now=now) is None
    assert (
        project_for_current_demo_session(
            database_session, expired_session.opaque_token, project.id, now=now
        )
        is None
    )


def test_create_demo_session_uses_fixed_expiry_and_retries_a_token_collision(
    database_session: Session,
) -> None:
    now = datetime(2026, 9, 22, tzinfo=UTC)
    database_session.add(make_demo_session("duplicate", expires_at=now + timedelta(days=1)))
    database_session.commit()
    tokens = iter(["duplicate", "unique"])

    created_session = create_demo_session(
        database_session,
        DemoSessionSettings(ttl_seconds=60, cookie_secure=False),
        now=now,
        token_factory=lambda _: next(tokens),
    )
    database_session.commit()

    assert created_session.opaque_token == "unique"
    assert created_session.expires_at == now + timedelta(seconds=60)
