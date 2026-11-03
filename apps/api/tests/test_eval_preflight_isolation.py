"""Eval target isolation without PostgreSQL connections, writes or provider calls."""

from __future__ import annotations

import socket
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy.engine import make_url

from sourcepilot.ai import eval_baseline as baseline
from sourcepilot.ai import eval_live


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(eval_live.os.environ):
        if key.startswith("PG") or key in {"DATABASE_URL", "TEST_DATABASE_URL"}:
            monkeypatch.delenv(key)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-test-only")
    monkeypatch.setenv("SOURCEPILOT_AI_MODEL", "configured-test-model")

    def resolve(host: str, port: int, **_: object) -> list[tuple[object, ...]]:
        addresses = {
            "localhost": ["::1", "127.0.0.1"],
            "alias": ["192.0.2.1", "192.0.2.2"],
            "overlap": ["192.0.2.2", "192.0.2.3"],
            "empty": [],
        }
        if host == "unresolvable":
            raise socket.gaierror("private hostname must not be reported")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))
                for address in addresses.get(host, [host])]

    monkeypatch.setattr(eval_live.socket, "getaddrinfo", resolve)


@pytest.mark.parametrize("protected_key", ["DATABASE_URL", "TEST_DATABASE_URL"])
@pytest.mark.parametrize("eval_url,protected_url", [
    ("postgresql+psycopg://user:secret@localhost/shared",
     "postgresql+psycopg://user:secret@localhost/shared"),
    ("postgresql+psycopg://eval:eval-secret@localhost/shared",
     "postgresql://app:app-secret@127.0.0.1:5432/shared"),
    ("postgresql+psycopg://eval:secret@[::1]/shared",
     "postgresql://app:other@127.0.0.1/shared"),
    ("postgresql+psycopg://eval:secret@[::ffff:192.0.2.2]/shared",
     "postgresql://app:other@192.0.2.2/shared"),
    ("postgresql+psycopg://eval:secret@alias/shared",
     "postgresql://app:other@overlap/shared"),
    ("postgresql+psycopg://eval:encoded%40secret@localhost/shared",
     "postgresql://app:other@localhost/shared"),
])
def test_colliding_targets_stop_runner_before_any_side_effect(
    protected_key: str, eval_url: str, protected_url: str,
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setenv("EVAL_DATABASE_URL", eval_url)
    monkeypatch.setenv(protected_key, protected_url)
    engine = Mock(side_effect=AssertionError("must not connect"))
    provider = Mock(side_effect=AssertionError("must not construct provider"))
    fixture = Mock(side_effect=AssertionError("must not write fixtures"))
    session = Mock(side_effect=AssertionError("must not open fixture session"))
    monkeypatch.setattr(eval_live, "create_engine", engine)
    monkeypatch.setattr(baseline.OpenAIResponsesClient, "from_environment", provider)
    monkeypatch.setattr(eval_live, "fresh_project", fixture)
    monkeypatch.setattr(baseline, "Session", session)
    result, code = baseline.execute("live", list(baseline.CATEGORIES), tmp_path)
    assert code == 2 and not result["complete"] and result["cases"] == []
    assert result["error"] == (
        f"EVAL_DATABASE_URL must target a separate database from {protected_key}."
    )
    for boundary in (engine, provider, fixture, session):
        boundary.assert_not_called()


@pytest.mark.parametrize("protected_url", [
    "postgresql://app:secret@localhost/application",
    "postgresql://app:secret@localhost:5433/eval_only",
    "postgresql://app:secret@192.0.2.1/eval_only",
])
def test_separate_database_port_or_address_is_allowed(
    protected_url: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", protected_url)
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://test:secret@localhost/test")
    eval_live.validate_database_isolation(make_url("postgresql://localhost/eval_only"))


@pytest.mark.parametrize("eval_url", [None, "not-a-database-url"])
def test_application_import_does_not_require_eval_configuration(
    eval_url: str | None, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import importlib

    if eval_url is None:
        monkeypatch.delenv("EVAL_DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("EVAL_DATABASE_URL", eval_url)
    preflight = Mock(side_effect=AssertionError("production must not run eval preflight"))
    monkeypatch.setattr(eval_live, "preflight_database", preflight)
    import sourcepilot.main

    assert importlib.reload(sourcepilot.main).app is not None
    preflight.assert_not_called()


@pytest.mark.parametrize("protected_url", [
    "not-a-url", "", "postgresql:///shared", "sqlite:///shared",
    "postgresql://localhost/shared?host=other",
    "postgresql://unresolvable/shared", "postgresql://empty/shared",
])
def test_unverifiable_protected_target_fails_closed_without_connecting(
    protected_url: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVAL_DATABASE_URL", "postgresql://localhost/eval_only")
    monkeypatch.setenv("DATABASE_URL", protected_url)
    engine = Mock()
    monkeypatch.setattr(eval_live, "create_engine", engine)
    with pytest.raises(eval_live.EvalPreflightError) as caught:
        eval_live.preflight_database()
    assert "secret" not in str(caught.value) and "private hostname" not in str(caught.value)
    engine.assert_not_called()
