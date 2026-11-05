from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from sourcepilot.ai.client import OpenAIResponsesClient, prepare_comparison_transport
from sourcepilot.ai.comparison_advice import (
    ComparisonAdviceRequest,
    ComparisonAdviceResponse,
    analyze_comparison_advice,
)
from sourcepilot.ai.supplier_explanation import (
    ExplanationNotReadyError,
    ExplanationUnavailableError,
    SupplierExplanationResponse,
    analyst_limits_from_environment,
    explain_supplier,
)
from sourcepilot.ai.tracing import shutdown_tracing
from sourcepilot.ai.tradeoff_analysis import (
    TradeoffAnalysisResponse,
    TradeoffNotReadyError,
    TradeoffUnavailableError,
    analyze_tradeoffs,
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
from sourcepilot.comparison.deadline import ComparisonDeadlineError
from sourcepilot.comparison.execution import run_async_comparison
from sourcepilot.comparison.lifecycle import ComparisonLifecycle, ComparisonLifecycleMiddleware
from sourcepilot.comparison.schemas import ComparisonResponse
from sourcepilot.comparison.service import (
    ComparisonNotReadyError,
    comparison_response,
    generate_comparison,
    latest_comparison,
)
from sourcepilot.documents.body_limit import UploadBodyLimitMiddleware
from sourcepilot.documents.processing import run_pdf_quote_processing
from sourcepilot.documents.service import (
    PdfCommitUncertainError,
    PdfQuoteUploadResponse,
    PdfStorageError,
    PdfUploadError,
    stage_pdf_upload,
    store_pdf_quote,
)
from sourcepilot.documents.settings import document_settings_from_environment
from sourcepilot.documents.storage import DocumentStorage, storage_from_settings
from sourcepilot.persistence.database import get_database_session
from sourcepilot.persistence.models import Brief, DemoSession, Project, Quote
from sourcepilot.projects.decision import PreferredSupplierNotShortlistedError
from sourcepilot.projects.schemas import (
    CreateProjectRequest,
    PreferredSupplierRequest,
    ProjectResponse,
    RenameProjectRequest,
)
from sourcepilot.projects.service import (
    create_project,
    project_for_demo_session,
    projects_for_demo_session,
    rename_project,
    update_preferred_supplier,
)
from sourcepilot.projects.workflow import project_responses
from sourcepilot.quotes.schemas import (
    ManualQuoteCreateRequest,
    ManualQuoteEditRequest,
    QuoteResponse,
)
from sourcepilot.quotes.service import (
    QuoteCandidateNotShortlistedError,
    QuoteWorkflowError,
    confirm_quote,
    create_manual_quote,
    edit_manual_quote,
    edit_pdf_quote,
    list_quotes,
    manual_fallback_quote,
    quote_snapshot,
    retry_pdf_quote,
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
    ShortlistApprovalError,
    SupplierNotInProjectError,
    approve_shortlist,
    discover_suppliers,
    list_project_suppliers,
    update_supplier_review,
)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    prepare_comparison_transport()
    runtime = ComparisonLifecycle()
    application.state.comparison_lifecycle = runtime
    try:
        yield
    finally:
        await runtime.shutdown()
        application.state.comparison_lifecycle = None
        await run_in_threadpool(shutdown_tracing)


app = FastAPI(title="SourcePilot API", lifespan=lifespan)
app.add_middleware(UploadBodyLimitMiddleware)
app.add_middleware(ComparisonLifecycleMiddleware)
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


def get_document_storage() -> DocumentStorage:
    return storage_from_settings(document_settings_from_environment())


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
    return project_responses(database_session, [project])[0]


@app.get("/projects", response_model=list[ProjectResponse])
def list_projects_endpoint(
    request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> list[ProjectResponse]:
    demo_session = active_demo_session(request, database_session)
    projects = projects_for_demo_session(database_session, demo_session)
    commit_or_rollback(database_session)
    return project_responses(database_session, projects)


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
    return project_responses(database_session, [project])[0]


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
    return project_responses(database_session, [project])[0]


def owned_project_or_404(
    database_session: Session, request: Request, project_id: UUID
) -> tuple[DemoSession, Project]:
    demo_session = active_demo_session(request, database_session)
    project = project_for_demo_session(database_session, demo_session, project_id)
    if project is None:
        database_session.rollback()
        raise HTTPException(status_code=404, detail="Project not found.")
    return demo_session, project


@app.put("/projects/{project_id}/preferred-supplier", response_model=ProjectResponse)
def preferred_supplier_endpoint(
    project_id: UUID, payload: PreferredSupplierRequest, request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> ProjectResponse | JSONResponse:
    _, project = owned_project_or_404(database_session, request, project_id)
    try:
        updated = update_preferred_supplier(database_session, project, payload)
        commit_or_rollback(database_session)
        database_session.refresh(updated)
        return project_responses(database_session, [updated])[0]
    except PreferredSupplierNotShortlistedError as error:
        database_session.rollback()
        return error_response(409, code="PREFERRED_SUPPLIER_NOT_SHORTLISTED", message=str(error))


@app.post("/projects/{project_id}/comparison/generate", response_model=ComparisonResponse,
          status_code=status.HTTP_201_CREATED)
def generate_comparison_endpoint(
    project_id: UUID, request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> ComparisonResponse | JSONResponse:
    _, project = owned_project_or_404(database_session, request, project_id)
    try:
        comparison = generate_comparison(database_session, project.id)
        result = ComparisonResponse.model_validate(comparison_response(database_session, comparison))
        commit_or_rollback(database_session)
        return result
    except ComparisonNotReadyError as error:
        database_session.rollback()
        return error_response(409, code="COMPARISON_NOT_READY", message=str(error))


@app.get("/projects/{project_id}/comparison", response_model=ComparisonResponse)
def read_comparison_endpoint(
    project_id: UUID, request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> ComparisonResponse | JSONResponse:
    _, project = owned_project_or_404(database_session, request, project_id)
    comparison = latest_comparison(database_session, project.id)
    if comparison is None:
        database_session.rollback()
        return error_response(404, code="COMPARISON_NOT_FOUND", message="No comparison exists.")
    result = ComparisonResponse.model_validate(comparison_response(database_session, comparison))
    commit_or_rollback(database_session)
    return result


@app.post("/projects/{project_id}/comparison/analysis", response_model=TradeoffAnalysisResponse)
async def analyze_comparison_endpoint(
    project_id: UUID, request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> TradeoffAnalysisResponse | JSONResponse:
    def execute(database_session: Session) -> TradeoffAnalysisResponse | JSONResponse:
        demo_session, project = owned_project_or_404(database_session, request, project_id)
        try:
            max_model_turns, max_tool_calls = analyst_limits_from_environment()
            result = analyze_tradeoffs(
                database_session, demo_session_id=demo_session.id, project_id=project.id,
                client_factory=OpenAIResponsesClient.from_environment,
                max_model_turns=max_model_turns, max_tool_calls=max_tool_calls,
            )
            commit_or_rollback(database_session)
        except TradeoffNotReadyError as error:
            database_session.rollback()
            return error_response(404 if error.code == "COMPARISON_NOT_FOUND" else 409,
                                  code=error.code, message=str(error))
        except TradeoffUnavailableError:
            database_session.rollback()
            return error_response(503, code="TRADEOFF_ANALYSIS_UNAVAILABLE",
                                  message="We could not analyze this comparison. Please retry.")
        return result

    try:
        return await run_async_comparison(database_session, execute)
    except ComparisonDeadlineError:
        return error_response(504, code="COMPARISON_ANALYSIS_TIMEOUT",
                              message="Analysis took too long. Please retry.")


@app.post("/projects/{project_id}/comparison/advice", response_model=ComparisonAdviceResponse)
async def advise_comparison_endpoint(
    project_id: UUID, body: ComparisonAdviceRequest, request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> ComparisonAdviceResponse | JSONResponse:
    def execute(database_session: Session) -> ComparisonAdviceResponse | JSONResponse:
        demo_session, project = owned_project_or_404(database_session, request, project_id)
        try:
            max_model_turns, max_tool_calls = analyst_limits_from_environment()
            result = analyze_comparison_advice(
                database_session, demo_session_id=demo_session.id, project_id=project.id,
                snapshot_id=body.snapshot_id, client_factory=OpenAIResponsesClient.from_environment,
                max_model_turns=max_model_turns, max_tool_calls=max_tool_calls,
            )
            commit_or_rollback(database_session)
            return result
        except TradeoffNotReadyError as error:
            database_session.rollback()
            return error_response(404 if error.code == "COMPARISON_NOT_FOUND" else 409,
                                  code=error.code, message=str(error))
        except TradeoffUnavailableError:
            database_session.rollback()
            return error_response(503, code="COMPARISON_ADVICE_UNAVAILABLE",
                                  message="We could not analyze this comparison. Please retry.")

    try:
        return await run_async_comparison(database_session, execute)
    except ComparisonDeadlineError:
        return error_response(504, code="COMPARISON_ANALYSIS_TIMEOUT",
                              message="Analysis took too long. Please retry.")


def owned_quote_or_404(
    database_session: Session, request: Request, quote_id: UUID,
) -> Quote:
    demo_session = active_demo_session(request, database_session)
    query = select(Quote).join(Project).where(
        Quote.id == quote_id, Project.demo_session_id == demo_session.id,
    )
    quote = database_session.scalars(query).one_or_none()
    if quote is None:
        database_session.rollback()
        raise HTTPException(status_code=404, detail="Quote not found.")
    return quote


@app.get("/projects/{project_id}/quotes", response_model=list[QuoteResponse])
def list_quotes_endpoint(
    project_id: UUID, request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> list[QuoteResponse]:
    _, project = owned_project_or_404(database_session, request, project_id)
    result = list_quotes(database_session, project.id)
    commit_or_rollback(database_session)
    return result


@app.post(
    "/projects/{project_id}/quotes/manual", response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_manual_quote_endpoint(
    project_id: UUID, payload: ManualQuoteCreateRequest, request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> QuoteResponse | JSONResponse:
    _, project = owned_project_or_404(database_session, request, project_id)
    try:
        result = create_manual_quote(
            database_session, project, payload.supplier_id, payload.values, payload.notes,
        )
        commit_or_rollback(database_session)
    except (QuoteWorkflowError, QuoteCandidateNotShortlistedError) as error:
        database_session.rollback()
        return error_response(409, code="QUOTE_NOT_AVAILABLE", message=str(error))
    except IntegrityError:
        database_session.rollback()
        return error_response(
            409, code="QUOTE_NOT_AVAILABLE", message="A quote already exists for this supplier.",
        )
    return result


@app.post(
    "/projects/{project_id}/quotes/upload", response_model=PdfQuoteUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_pdf_quote_endpoint(
    project_id: UUID, request: Request,
    background_tasks: BackgroundTasks,
    supplier_id: Annotated[UUID, Form()], file: Annotated[UploadFile, File()],
    database_session: Annotated[Session, Depends(get_database_session)],
    storage: Annotated[DocumentStorage, Depends(get_document_storage)],
) -> PdfQuoteUploadResponse | JSONResponse:
    _, project = owned_project_or_404(database_session, request, project_id)
    temporary = None
    try:
        settings = document_settings_from_environment()
        temporary, path, filename, sha256, page_count = stage_pdf_upload(file, settings)
        result = store_pdf_quote(
            database_session, project, supplier_id, path=path, filename=filename,
            sha256=sha256, page_count=page_count, storage=storage,
        )
        background_tasks.add_task(
            run_pdf_quote_processing, result.document.id, result.document.processing_attempts,
        )
        return result
    except PdfUploadError as error:
        database_session.rollback()
        return error_response(error.status_code, code=error.code, message=str(error))
    except IntegrityError:
        database_session.rollback()
        return error_response(
            409, code="QUOTE_ALREADY_EXISTS", message="A quote already exists for this supplier.",
        )
    except (PdfStorageError, PdfCommitUncertainError):
        database_session.rollback()
        return error_response(503, code="UPLOAD_UNAVAILABLE", message="PDF upload is unavailable.")
    finally:
        if temporary is not None:
            temporary.cleanup()


@app.get("/quotes/{quote_id}", response_model=QuoteResponse)
def read_quote_endpoint(
    quote_id: UUID, request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> QuoteResponse:
    quote = owned_quote_or_404(database_session, request, quote_id)
    result = quote_snapshot(quote)
    commit_or_rollback(database_session)
    return result


@app.patch("/quotes/{quote_id}", response_model=QuoteResponse)
def edit_quote_endpoint(
    quote_id: UUID, payload: ManualQuoteEditRequest, request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> QuoteResponse | JSONResponse:
    quote = owned_quote_or_404(database_session, request, quote_id)
    try:
        edit = edit_pdf_quote if quote.entry_type == "PDF" else edit_manual_quote
        result = edit(
            database_session, quote, payload.values,
            notes_provided="notes" in payload.model_fields_set, notes=payload.notes,
        )
        commit_or_rollback(database_session)
    except QuoteWorkflowError as error:
        database_session.rollback()
        return error_response(409, code="QUOTE_NOT_EDITABLE", message=str(error))
    return result


@app.post("/quotes/{quote_id}/confirm", response_model=QuoteResponse)
def confirm_quote_endpoint(
    quote_id: UUID, request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> QuoteResponse | JSONResponse:
    quote = owned_quote_or_404(database_session, request, quote_id)
    try:
        result = confirm_quote(database_session, quote)
        commit_or_rollback(database_session)
    except QuoteWorkflowError as error:
        database_session.rollback()
        return error_response(409, code="QUOTE_NOT_CONFIRMABLE", message=str(error))
    return result


@app.post("/quotes/{quote_id}/retry", response_model=QuoteResponse)
def retry_quote_endpoint(
    quote_id: UUID, request: Request, background_tasks: BackgroundTasks,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> QuoteResponse | JSONResponse:
    quote = owned_quote_or_404(database_session, request, quote_id)
    try:
        result, scheduled_attempt = retry_pdf_quote(database_session, quote)
        commit_or_rollback(database_session)
    except QuoteWorkflowError as error:
        database_session.rollback()
        return error_response(409, code="QUOTE_NOT_RETRYABLE", message=str(error))
    if scheduled_attempt is not None:
        background_tasks.add_task(run_pdf_quote_processing, *scheduled_attempt)
    return result


@app.post("/quotes/{quote_id}/manual-fallback", response_model=QuoteResponse)
def manual_fallback_endpoint(
    quote_id: UUID, payload: ManualQuoteEditRequest, request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> QuoteResponse | JSONResponse:
    quote = owned_quote_or_404(database_session, request, quote_id)
    try:
        result = manual_fallback_quote(
            database_session, quote, payload.values,
            notes_provided="notes" in payload.model_fields_set, notes=payload.notes,
        )
        commit_or_rollback(database_session)
    except QuoteWorkflowError as error:
        database_session.rollback()
        return error_response(409, code="QUOTE_NOT_AVAILABLE", message=str(error))
    return result


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


@app.post("/projects/{project_id}/shortlist/approve", response_model=SupplierListResponse)
def approve_shortlist_endpoint(
    project_id: UUID,
    request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> SupplierListResponse | JSONResponse:
    _, project = owned_project_or_404(database_session, request, project_id)
    try:
        result = approve_shortlist(database_session, project)
        commit_or_rollback(database_session)
    except ShortlistApprovalError as error:
        database_session.rollback()
        return error_response(409, code="SHORTLIST_NOT_READY", message=str(error))
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
