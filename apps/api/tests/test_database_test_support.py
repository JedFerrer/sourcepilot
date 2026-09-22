import socket

import pytest
from alembic.config import Config
from sqlalchemy.engine import make_url

from alembic import command
from tests.database_test_support import (
    API_DIRECTORY,
    persistence_test_database_url_from_environment,
    targets_same_postgres_database,
)


def test_alembic_requires_database_url_when_no_programmatic_url_is_supplied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL must be set for Alembic migration commands"):
        command.current(Config(str(API_DIRECTORY / "alembic.ini")))


def test_test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/sourcepilot")

    with pytest.raises(RuntimeError, match="TEST_DATABASE_URL must be set"):
        persistence_test_database_url_from_environment()


def loopback_resolver(host: str, port: int | None, **_: object) -> list[tuple[object, ...]]:
    addresses = {
        "127.0.0.1": "127.0.0.1",
        "::1": "::1",
        "::ffff:127.0.0.1": "::ffff:127.0.0.1",
        "localhost": "127.0.0.1",
        "database-a.example": "192.0.2.10",
        "database-b.example": "192.0.2.11",
    }
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (addresses[host], port))]


@pytest.mark.parametrize(
    ("database_url", "test_database_url"),
    [
        (
            "postgresql+psycopg://app:pass@127.0.0.1/sourcepilot",
            "postgresql+psycopg://test:pass@[::1]:5432/sourcepilot",
        ),
        (
            "postgresql+psycopg://app:pass@localhost/sourcepilot",
            "postgresql+psycopg://test:pass@[::1]:5432/sourcepilot",
        ),
        (
            "postgresql+psycopg://app:pass@127.0.0.1/sourcepilot",
            "postgresql+psycopg://test:pass@localhost:5432/sourcepilot",
        ),
        (
            "postgresql+psycopg://app:pass@127.0.0.1/sourcepilot",
            "postgresql+psycopg://test:pass@[::ffff:127.0.0.1]:5432/sourcepilot",
        ),
    ],
)
def test_test_database_url_rejects_equivalent_database_targets(
    monkeypatch: pytest.MonkeyPatch, database_url: str, test_database_url: str
) -> None:
    monkeypatch.setattr("tests.database_test_support.socket.getaddrinfo", loopback_resolver)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TEST_DATABASE_URL", test_database_url)

    with pytest.raises(RuntimeError, match="must target a different database"):
        persistence_test_database_url_from_environment()


def test_test_database_url_allows_a_genuinely_different_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("tests.database_test_support.socket.getaddrinfo", loopback_resolver)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://app:pass@localhost/sourcepilot")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+psycopg://test:pass@127.0.0.1:5432/sourcepilot_test")

    assert persistence_test_database_url_from_environment().endswith("sourcepilot_test")


def test_same_database_guard_allows_genuinely_different_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("tests.database_test_support.socket.getaddrinfo", loopback_resolver)

    assert not targets_same_postgres_database(
        make_url("postgresql+psycopg://app:pass@database-a.example/sourcepilot"),
        make_url("postgresql+psycopg://test:pass@database-b.example:5432/sourcepilot"),
    )
