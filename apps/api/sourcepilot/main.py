from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from sourcepilot.ai.client import OpenAIResponsesClient
from sourcepilot.ai.supplier_explanation import (
    ExplanationNotReadyError,
    ExplanationUnavailableError,
    SupplierExplanationResponse,
    analyst_limits_from_environment,
    explain_supplier,
)
from sourcepilot.api_errors import (
    error_response,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from sourcepilot.briefs.schemas import (
    AnalyzeBriefResponse,
    ApproveBriefRequest,
    BriefResponse,
    ClarificationResponse,
    EditBriefRequest,
)
from sourcepilot.briefs.workflow import (
    BriefAnalysisUnavailableError,
    BriefConflictError,
    BriefEditError,
    ClarificationUnavailableError,
    analyze_project_brief,
    approve_brief,
    brief_snapshot,
    clarify_project_brief,
    edit_brief,
    project_requirements,
)
from sourcepilot.persistence.database import get_database_session
from sourcepilot.persistence.models import Brief, DemoSession, Project
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
from sourcepilot.suppliers.schemas import (
    DiscoverSuppliersResponse,
    SupplierListResponse,
    UpdateSupplierReviewRequest,
)
from sourcepilot.suppliers.service import (
    DiscoveryNotReadyError,
    SupplierNotInProjectError,
    discover_suppliers,
    list_project_suppliers,
    update_supplier_review,
)

app = FastAPI(title="SourcePilot API")
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


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


def owned_project_or_404(
    database_session: Session, request: Request, project_id: UUID
) -> tuple[DemoSession, Project]:
    demo_session = active_demo_session(request, database_session)
    project = project_for_demo_session(database_session, demo_session, project_id)
    if project is None:
        database_session.rollback()
        raise HTTPException(status_code=404, detail="Project not found.")
    return demo_session, project


@app.get("/projects/{project_id}/brief", response_model=BriefResponse)
def read_brief_endpoint(
    project_id: UUID,
    request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> BriefResponse:
    _, project = owned_project_or_404(database_session, request, project_id)
    brief = database_session.get(Brief, project.id)
    result = brief_snapshot(project, brief, project_requirements(database_session, project.id))
    commit_or_rollback(database_session)
    return result


@app.patch("/projects/{project_id}/brief", response_model=BriefResponse)
def edit_brief_endpoint(
    project_id: UUID,
    payload: EditBriefRequest,
    request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> BriefResponse | JSONResponse:
    _, project = owned_project_or_404(database_session, request, project_id)
    try:
        result = edit_brief(database_session, project, payload)
        commit_or_rollback(database_session)
    except BriefConflictError as error:
        database_session.rollback()
        return error_response(409, code="BRIEF_CONFLICT", message=str(error))
    except BriefEditError as error:
        database_session.rollback()
        return error_response(422, code="VALIDATION_ERROR", message=str(error))
    return result


@app.post("/projects/{project_id}/brief/approve", response_model=BriefResponse)
def approve_brief_endpoint(
    project_id: UUID,
    payload: ApproveBriefRequest,
    request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> BriefResponse | JSONResponse:
    _, project = owned_project_or_404(database_session, request, project_id)
    try:
        result = approve_brief(database_session, project, payload)
        commit_or_rollback(database_session)
    except BriefConflictError as error:
        database_session.rollback()
        return error_response(409, code="BRIEF_CONFLICT", message=str(error))
    return result


@app.post("/projects/{project_id}/brief/analyze", response_model=AnalyzeBriefResponse)
def analyze_brief_endpoint(
    project_id: UUID,
    request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> AnalyzeBriefResponse | JSONResponse:
    demo_session, project = owned_project_or_404(database_session, request, project_id)
    try:
        result = analyze_project_brief(
            database_session,
            demo_session=demo_session,
            project=project,
            client_factory=OpenAIResponsesClient.from_environment,
        )
        commit_or_rollback(database_session)
    except BriefConflictError as error:
        database_session.rollback()
        return error_response(409, code="BRIEF_CONFLICT", message=str(error))
    except BriefAnalysisUnavailableError:
        database_session.rollback()
        return error_response(
            503,
            code="BRIEF_ANALYSIS_UNAVAILABLE",
            message="We could not analyze this request. Try again or enter the Brief manually.",
        )
    return result


@app.post("/projects/{project_id}/brief/clarifications", response_model=ClarificationResponse)
def generate_brief_clarifications_endpoint(
    project_id: UUID,
    request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> ClarificationResponse | JSONResponse:
    demo_session, project = owned_project_or_404(database_session, request, project_id)
    try:
        result = clarify_project_brief(
            database_session,
            demo_session=demo_session,
            project=project,
            client_factory=OpenAIResponsesClient.from_environment,
        )
        commit_or_rollback(database_session)
    except BriefConflictError as error:
        database_session.rollback()
        return error_response(409, code="BRIEF_CONFLICT", message=str(error))
    except ClarificationUnavailableError:
        database_session.rollback()
        return error_response(
            503,
            code="CLARIFICATION_UNAVAILABLE",
            message="We could not generate questions. Try again or edit the Brief manually.",
        )
    return result


@app.post("/projects/{project_id}/suppliers/discover", response_model=DiscoverSuppliersResponse)
def discover_suppliers_endpoint(
    project_id: UUID,
    request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> DiscoverSuppliersResponse | JSONResponse:
    _, project = owned_project_or_404(database_session, request, project_id)
    try:
        result = discover_suppliers(database_session, project_id=project.id)
        commit_or_rollback(database_session)
    except DiscoveryNotReadyError as error:
        database_session.rollback()
        return error_response(409, code="BRIEF_NOT_APPROVED", message=str(error))
    return result


@app.get("/projects/{project_id}/suppliers", response_model=SupplierListResponse)
def list_suppliers_endpoint(
    project_id: UUID,
    request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> SupplierListResponse:
    _, project = owned_project_or_404(database_session, request, project_id)
    result = list_project_suppliers(database_session, project)
    commit_or_rollback(database_session)
    return result


@app.patch("/projects/{project_id}/suppliers/{supplier_id}", response_model=SupplierListResponse)
def update_supplier_endpoint(
    project_id: UUID,
    supplier_id: UUID,
    payload: UpdateSupplierReviewRequest,
    request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> SupplierListResponse | JSONResponse:
    _, project = owned_project_or_404(database_session, request, project_id)
    try:
        result = update_supplier_review(database_session, project, supplier_id, payload)
        commit_or_rollback(database_session)
    except SupplierNotInProjectError as error:
        database_session.rollback()
        return error_response(404, code="SUPPLIER_NOT_FOUND", message=str(error))
    return result


@app.post(
    "/projects/{project_id}/suppliers/{supplier_id}/explanation",
    response_model=SupplierExplanationResponse,
)
def explain_supplier_endpoint(
    project_id: UUID,
    supplier_id: UUID,
    request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> SupplierExplanationResponse | JSONResponse:
    demo_session, project = owned_project_or_404(database_session, request, project_id)
    try:
        max_model_turns, max_tool_calls = analyst_limits_from_environment()
        result = explain_supplier(
            database_session, demo_session_id=demo_session.id,
            project_id=project.id, supplier_id=supplier_id,
            client_factory=OpenAIResponsesClient.from_environment,
            max_model_turns=max_model_turns, max_tool_calls=max_tool_calls,
        )
        commit_or_rollback(database_session)
    except ExplanationNotReadyError as error:
        database_session.rollback()
        status_code = 404 if error.code == "SUPPLIER_NOT_FOUND" else 409
        return error_response(status_code, code=error.code, message=str(error))
    except ExplanationUnavailableError:
        database_session.rollback()
        return error_response(
            503, code="SUPPLIER_EXPLANATION_UNAVAILABLE",
            message="We could not explain this supplier. Please try again.",
        )
    return result
