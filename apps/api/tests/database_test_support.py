from __future__ import annotations

import os
import socket
from collections.abc import Iterator
from ipaddress import IPv6Address, ip_address
from pathlib import Path

from alembic.config import Config
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.engine import URL, make_url

from alembic import command

DATABASE_URL_ENV = "DATABASE_URL"
TEST_DATABASE_URL_ENV = "TEST_DATABASE_URL"
API_DIRECTORY = Path(__file__).resolve().parents[1]
LOOPBACK_ADDRESS_IDENTITY = "loopback"


def persistence_test_database_url_from_environment() -> str:
    test_database_url = os.environ.get(TEST_DATABASE_URL_ENV)
    if not test_database_url:
        message = f"{TEST_DATABASE_URL_ENV} must be set for persistence tests."
        raise RuntimeError(message)

    application_database_url = os.environ.get(DATABASE_URL_ENV)
    if not application_database_url:
        message = f"{DATABASE_URL_ENV} must be set alongside {TEST_DATABASE_URL_ENV}."
        raise RuntimeError(message)

    if targets_same_postgres_database(
        make_url(test_database_url), make_url(application_database_url)
    ):
        message = f"{TEST_DATABASE_URL_ENV} must target a different database from {DATABASE_URL_ENV}."
        raise RuntimeError(message)
    return test_database_url


def targets_same_postgres_database(first_url: URL, second_url: URL) -> bool:
    """Return whether two PostgreSQL URLs resolve to the same database target."""
    first_identity = database_identity(first_url)
    second_identity = database_identity(second_url)
    return (
        first_identity.database == second_identity.database
        and first_identity.port == second_identity.port
        and bool(first_identity.addresses & second_identity.addresses)
    )


class PostgresDatabaseIdentity:
    """Canonical PostgreSQL database target used before destructive test resets."""

    def __init__(self, database: str, port: int, addresses: frozenset[str]) -> None:
        self.database = database
        self.port = port
        self.addresses = addresses


def database_identity(url: URL) -> PostgresDatabaseIdentity:
    if not url.host or not url.database:
        raise RuntimeError("Database URLs must include both a PostgreSQL host and database name.")

    port = url.port or 5432
    try:
        resolved_addresses = socket.getaddrinfo(url.host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        message = f"Could not resolve PostgreSQL host {url.host!r} for test-database safety."
        raise RuntimeError(message) from error

    addresses = frozenset(
        normalized_address_identity(str(address[4][0])) for address in resolved_addresses
    )
    if not addresses:
        raise RuntimeError(f"Could not resolve PostgreSQL host {url.host!r} for test-database safety.")
    return PostgresDatabaseIdentity(database=url.database, port=port, addresses=addresses)


def normalized_address_identity(address: str) -> str:
    """Collapse all IP loopback forms into one destructive-reset safety identity."""
    parsed_address = ip_address(address)
    if isinstance(parsed_address, IPv6Address) and parsed_address.ipv4_mapped is not None:
        parsed_address = parsed_address.ipv4_mapped

    if parsed_address.is_loopback:
        return LOOPBACK_ADDRESS_IDENTITY
    return str(parsed_address)


def alembic_config(database_url: str) -> Config:
    config = Config(str(API_DIRECTORY / "alembic.ini"))
    config.attributes["database_url"] = database_url
    return config


def reset_test_database(database_url: str) -> None:
    config = alembic_config(database_url)
    # Reset discards test data; remove nullable-importance rows before a guarded downgrade.
    engine = create_test_engine(database_url)
    try:
        if "requirements" in inspect(engine).get_table_names():
            with engine.begin() as connection:
                connection.execute(text("DELETE FROM requirements"))
    finally:
        engine.dispose()
    command.downgrade(config, "base")
    command.upgrade(config, "head")


def create_test_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def test_database_connection() -> Iterator[Engine]:
    engine = create_test_engine(persistence_test_database_url_from_environment())
    try:
        yield engine
    finally:
        engine.dispose()
