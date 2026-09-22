from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sourcepilot.persistence.models import DemoSession, Project
from sourcepilot.session.settings import DemoSessionSettings

TOKEN_BYTES = 32
MAX_TOKEN_GENERATION_ATTEMPTS = 3


def current_time() -> datetime:
    return datetime.now(UTC)


def create_demo_session(
    database_session: Session,
    settings: DemoSessionSettings,
    *,
    now: datetime | None = None,
    token_factory: Callable[[int], str] = token_urlsafe,
) -> DemoSession:
    """Persist a new fixed-lifetime anonymous session, retrying a token collision."""
    created_at = now or current_time()
    for _ in range(MAX_TOKEN_GENERATION_ATTEMPTS):
        demo_session = DemoSession(
            opaque_token=token_factory(TOKEN_BYTES),
            last_seen_at=created_at,
            expires_at=created_at + timedelta(seconds=settings.ttl_seconds),
        )
        database_session.add(demo_session)
        try:
            database_session.flush()
        except IntegrityError:
            database_session.rollback()
            continue
        return demo_session
    raise RuntimeError("Could not generate a unique demo-session token.")


def resolve_demo_session(
    database_session: Session, opaque_token: str | None, *, now: datetime | None = None
) -> DemoSession | None:
    """Return a valid current session and record activity without extending its lifetime."""
    if not opaque_token:
        return None
    resolved_at = now or current_time()
    demo_session = database_session.scalar(
        select(DemoSession).where(
            DemoSession.opaque_token == opaque_token,
            DemoSession.expires_at > resolved_at,
        )
    )
    if demo_session is None:
        return None
    demo_session.last_seen_at = resolved_at
    return demo_session


def get_or_create_demo_session(
    database_session: Session,
    opaque_token: str | None,
    settings: DemoSessionSettings,
    *,
    now: datetime | None = None,
) -> tuple[DemoSession, bool]:
    """Reuse a valid session or create a new one for a missing or invalid cookie."""
    resolved_at = now or current_time()
    existing_session = resolve_demo_session(database_session, opaque_token, now=resolved_at)
    if existing_session is not None:
        return existing_session, False
    return create_demo_session(database_session, settings, now=resolved_at), True


def project_for_resolved_demo_session(
    database_session: Session, demo_session: DemoSession, project_id: UUID
) -> Project | None:
    """Look up a project only through an already-resolved current demo session."""
    return database_session.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.demo_session_id == demo_session.id,
        )
    )


def project_for_current_demo_session(
    database_session: Session,
    opaque_token: str | None,
    project_id: UUID,
    *,
    now: datetime | None = None,
) -> Project | None:
    """Authorize project access by resolving a valid session before ownership lookup."""
    demo_session = resolve_demo_session(database_session, opaque_token, now=now)
    if demo_session is None:
        return None
    return project_for_resolved_demo_session(database_session, demo_session, project_id)
