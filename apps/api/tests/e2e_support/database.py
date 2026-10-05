"""Fail-closed guard for the explicitly provisioned, disposable E2E database."""

from __future__ import annotations

import os
import socket
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from ipaddress import ip_address
from pathlib import Path

from psycopg import Connection as PsycopgConnection
from sqlalchemy import Connection, create_engine, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session

from alembic import command
from sourcepilot.suppliers.seed import seed_suppliers
from tests.database_test_support import (
    API_DIRECTORY,
    alembic_config,
    targets_same_postgres_database,
)


def reject_libpq_environment(environment: Mapping[str, str]) -> None:
    # Reject the entire libpq namespace, including service files, options and future
    # routing settings. Inspect the real process too when a caller supplies a mapping.
    if any(key.upper().startswith("PG") for key in (*environment, *os.environ)):
        raise RuntimeError("E2E safety forbids inherited PG* libpq settings.")


def validate_urls(environment: Mapping[str, str]) -> str:
    reject_libpq_environment(environment)
    urls: dict[str, URL] = {}
    for key in ("E2E_DATABASE_URL", "DATABASE_URL", "TEST_DATABASE_URL"):
        raw = environment.get(key)
        if not raw:
            raise RuntimeError(f"{key} must be explicitly configured.")
        url = make_url(raw)
        if (url.drivername != "postgresql+psycopg" or not url.host or not url.database
                or not url.username or not url.password):
            raise RuntimeError(f"{key} must be an explicit PostgreSQL psycopg URL.")
        if url.query:
            raise RuntimeError("E2E safety does not support connection URL query overrides.")
        urls[key] = url
    candidate = urls["E2E_DATABASE_URL"]
    if candidate.database != "sourcepilot_e2e":
        raise RuntimeError("E2E database must be named sourcepilot_e2e.")
    addresses = socket.getaddrinfo(candidate.host, candidate.port or 5432, type=socket.SOCK_STREAM)
    if not addresses or any(not ip_address(str(item[4][0])).is_loopback for item in addresses):
        raise RuntimeError("E2E database host must resolve only to loopback addresses.")
    for key in ("DATABASE_URL", "TEST_DATABASE_URL"):
        protected = urls[key]
        # Resolve even differently named protected databases: errors must abort.
        same_target = targets_same_postgres_database(candidate, protected)
        if same_target is not False:
            raise RuntimeError(f"E2E identity check did not establish separation from {key}.")
        if candidate.database == protected.database:
            raise RuntimeError(f"E2E database must be separate from {key}.")
    # Pin one resolved address and the default port; no later DNS lookup may route
    # a reconnect elsewhere. Multiple loopback families are safe, not a host list.
    address = min(str(item[4][0]) for item in addresses)
    return candidate.set(host=address, port=candidate.port or 5432).render_as_string(
        hide_password=False
    )


@dataclass(frozen=True)
class ValidatedDatabase:
    url: str
    connection: Connection


@contextmanager
def validated_database(
    environment: Mapping[str, str] | None = None,
) -> Iterator[ValidatedDatabase]:
    raw = validate_urls(os.environ if environment is None else environment)
    expected = make_url(raw)
    engine = create_engine(raw, connect_args={"connect_timeout": 5, "hostaddr": expected.host})
    try:
        # Keep validation, deletes, migrations and seeding on this exact connection
        # and transaction. A disposed validation engine followed by a new reset
        # connection cannot establish that the reset target was validated.
        with engine.begin() as connection:
            driver = connection.connection.driver_connection
            if not isinstance(driver, PsycopgConnection):
                raise TypeError("Connected database identity is unavailable.")
            # libpq's connected endpoint is the validated client-side address/port.
            # inet_server_addr() may differ behind the approved Docker port mapping.
            identity = (driver.info.dbname, driver.info.hostaddr, driver.info.port, driver.info.user)
            server_identity = connection.execute(text(
                "SELECT pg_catalog.current_database(), current_user"
            )).one()
            if (identity != (expected.database, expected.host, expected.port, expected.username)
                    or tuple(server_identity) != (expected.database, expected.username)):
                raise RuntimeError("Connected database identity does not match the validated E2E target.")
            reject_libpq_environment(os.environ)
            yield ValidatedDatabase(raw, connection)
    finally:
        engine.dispose()


def reset_database(target: ValidatedDatabase) -> None:
    """Reset and seed using only the positively validated, still-open connection."""
    reject_libpq_environment(os.environ)
    connection = target.connection
    if "requirements" in inspect(connection).get_table_names():
        connection.execute(text("DELETE FROM requirements"))
    config = alembic_config(target.url)
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    config.set_main_option("version_locations", str(API_DIRECTORY / "alembic" / "versions"))
    config.attributes["connection"] = connection
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    with Session(connection) as session:
        seed_suppliers(session)
        session.flush()


def safe_database_url(environment: Mapping[str, str] | None = None) -> str:
    with validated_database(environment) as target:
        return target.url
