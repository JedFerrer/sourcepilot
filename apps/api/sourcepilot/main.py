from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response
from sqlalchemy.orm import Session

from sourcepilot.persistence.database import get_database_session
from sourcepilot.session.service import get_or_create_demo_session
from sourcepilot.session.settings import (
    DEMO_SESSION_COOKIE_NAME,
    demo_session_settings_from_environment,
)

app = FastAPI(title="SourcePilot API")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/demo-session", status_code=204)
def initialize_demo_session(
    request: Request,
    response: Response,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> None:
    """Create or reuse the anonymous session identified by the HttpOnly cookie."""
    settings = demo_session_settings_from_environment()
    opaque_token = request.cookies.get(DEMO_SESSION_COOKIE_NAME)
    try:
        demo_session, was_created = get_or_create_demo_session(
            database_session, opaque_token, settings
        )
        database_session.commit()
    except Exception:
        database_session.rollback()
        raise

    if was_created:
        response.set_cookie(
            key=DEMO_SESSION_COOKIE_NAME,
            value=demo_session.opaque_token,
            max_age=settings.ttl_seconds,
            path="/",
            secure=settings.cookie_secure,
            httponly=True,
            samesite="lax",
        )
