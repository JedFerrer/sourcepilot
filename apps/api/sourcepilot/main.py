from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from sourcepilot.persistence.database import get_database_session
from sourcepilot.persistence.models import DemoSession
from sourcepilot.projects.schemas import CreateProjectRequest, ProjectResponse, RenameProjectRequest
from sourcepilot.projects.service import (
    create_project,
    project_for_demo_session,
    projects_for_demo_session,
    rename_project,
)
from sourcepilot.session.service import get_or_create_demo_session, resolve_demo_session
from sourcepilot.session.settings import (
    DEMO_SESSION_COOKIE_NAME,
    demo_session_settings_from_environment,
)

app = FastAPI(title="SourcePilot API")


def active_demo_session(request: Request, database_session: Session) -> DemoSession:
    """Resolve the valid session carried only in the anonymous-session cookie."""
    demo_session = resolve_demo_session(
        database_session, request.cookies.get(DEMO_SESSION_COOKIE_NAME)
    )
    if demo_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Demo session is unavailable.",
        )
    return demo_session


def commit_or_rollback(database_session: Session) -> None:
    try:
        database_session.commit()
    except Exception:
        database_session.rollback()
        raise


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


@app.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project_endpoint(
    payload: CreateProjectRequest,
    request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> ProjectResponse:
    demo_session = active_demo_session(request, database_session)
    project = create_project(
        database_session,
        demo_session,
        name=payload.name,
        original_request=payload.original_request,
    )
    commit_or_rollback(database_session)
    database_session.refresh(project)
    return ProjectResponse.model_validate(project)


@app.get("/projects", response_model=list[ProjectResponse])
def list_projects_endpoint(
    request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> list[ProjectResponse]:
    demo_session = active_demo_session(request, database_session)
    projects = projects_for_demo_session(database_session, demo_session)
    commit_or_rollback(database_session)
    return [ProjectResponse.model_validate(project) for project in projects]


@app.get("/projects/{project_id}", response_model=ProjectResponse)
def read_project_endpoint(
    project_id: UUID,
    request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> ProjectResponse:
    demo_session = active_demo_session(request, database_session)
    project = project_for_demo_session(database_session, demo_session, project_id)
    if project is None:
        database_session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    commit_or_rollback(database_session)
    return ProjectResponse.model_validate(project)


@app.patch("/projects/{project_id}", response_model=ProjectResponse)
def rename_project_endpoint(
    project_id: UUID,
    payload: RenameProjectRequest,
    request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> ProjectResponse:
    demo_session = active_demo_session(request, database_session)
    project = project_for_demo_session(database_session, demo_session, project_id)
    if project is None:
        database_session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    rename_project(database_session, project, name=payload.name)
    commit_or_rollback(database_session)
    database_session.refresh(project)
    return ProjectResponse.model_validate(project)
