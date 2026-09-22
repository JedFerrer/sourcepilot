from __future__ import annotations

import os
from dataclasses import dataclass

DEMO_SESSION_TTL_SECONDS_ENV = "DEMO_SESSION_TTL_SECONDS"
DEMO_SESSION_COOKIE_SECURE_ENV = "DEMO_SESSION_COOKIE_SECURE"
DEFAULT_DEMO_SESSION_TTL_SECONDS = 24 * 60 * 60
DEMO_SESSION_COOKIE_NAME = "sourcepilot_demo_session"


@dataclass(frozen=True)
class DemoSessionSettings:
    ttl_seconds: int
    cookie_secure: bool


def demo_session_settings_from_environment() -> DemoSessionSettings:
    """Read the small anonymous-session configuration surface from the environment."""
    ttl_seconds = positive_integer_from_environment(
        DEMO_SESSION_TTL_SECONDS_ENV, DEFAULT_DEMO_SESSION_TTL_SECONDS
    )
    cookie_secure = boolean_from_environment(DEMO_SESSION_COOKIE_SECURE_ENV, default=False)
    return DemoSessionSettings(ttl_seconds=ttl_seconds, cookie_secure=cookie_secure)


def positive_integer_from_environment(name: str, default: int) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be a positive integer.") from error
    if value <= 0:
        raise RuntimeError(f"{name} must be a positive integer.")
    return value


def boolean_from_environment(name: str, *, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    normalized_value = raw_value.lower()
    if normalized_value == "true":
        return True
    if normalized_value == "false":
        return False
    raise RuntimeError(f"{name} must be true or false.")
