import os
from collections.abc import Generator
from functools import cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL_ENV = "DATABASE_URL"


def database_url_from_environment() -> str:
    """Return the configured application database URL when persistence is used."""
    database_url = os.environ.get(DATABASE_URL_ENV)
    if not database_url:
        message = f"{DATABASE_URL_ENV} must be set when application persistence is used."
        raise RuntimeError(message)
    return database_url


def create_database_engine(database_url: str) -> Engine:
    """Create a synchronous PostgreSQL engine for a configured database URL."""
    return create_engine(database_url, pool_pre_ping=True)


@cache
def application_engine() -> Engine:
    """Lazily create the application engine so health-only startup needs no database URL."""
    return create_database_engine(database_url_from_environment())


@cache
def application_session_factory() -> sessionmaker[Session]:
    """Return the shared session factory for application persistence operations."""
    return sessionmaker(bind=application_engine(), expire_on_commit=False)


def get_database_session() -> Generator[Session, None, None]:
    """Yield one database session for a FastAPI operation and always close it."""
    session = application_session_factory()()
    try:
        yield session
    finally:
        session.close()
