from datetime import UTC, datetime, timedelta

from sourcepilot.persistence.models import DemoSession, Project


def make_demo_session(
    token: str = "test-session", *, expires_at: datetime | None = None
) -> DemoSession:
    expiry = expires_at or datetime.now(UTC) + timedelta(hours=1)
    return DemoSession(
        opaque_token=token,
        last_seen_at=expiry - timedelta(hours=1),
        expires_at=expiry,
    )


def make_project(demo_session: DemoSession, name: str = "Test project") -> Project:
    return Project(
        demo_session=demo_session,
        name=name,
        original_request=f"Source {name}.",
    )
