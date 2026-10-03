from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import Engine, delete, inspect, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from sourcepilot.persistence.models import (
    DemoSession,
    Project,
    ProjectSupplier,
    Quote,
    QuoteDocument,
    QuoteValue,
    Requirement,
    Supplier,
)
from sourcepilot.quotes.domain import QuoteEntryType, QuoteStatus, authoritative_current_values
from sourcepilot.quotes.service import QuoteCandidateNotShortlistedError, create_quote
from tests.conftest import database_session_for_engine
from tests.database_test_support import (
    alembic_config,
    create_test_engine,
    persistence_test_database_url_from_environment,
    reset_test_database,
)


@pytest.fixture(scope="module")
def test_database_url() -> str:
    return persistence_test_database_url_from_environment()


@pytest.fixture(scope="module")
def test_engine(test_database_url: str) -> Iterator[Engine]:
    engine = create_test_engine(test_database_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(autouse=True)
def reset_persistence_database(test_database_url: str) -> Iterator[None]:
    reset_test_database(test_database_url)
    yield
    reset_test_database(test_database_url)


@pytest.fixture
def database_session(test_engine: Engine) -> Iterator[Session]:
    yield from database_session_for_engine(test_engine)


def make_demo_session(token: str = "token-a") -> DemoSession:
    now = datetime.now(UTC)
    return DemoSession(
        opaque_token=token,
        last_seen_at=now,
        expires_at=now + timedelta(hours=24),
    )


def test_migration_smoke_creates_only_current_application_tables(test_engine: Engine) -> None:
    with test_engine.connect() as connection:
        current_revisions = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()

    assert current_revisions == ["0015_preferred_supplier"]

    table_names = set(inspect(test_engine).get_table_names())

    assert {
        "demo_sessions", "projects", "ai_runs", "briefs", "requirements",
        "suppliers", "supplier_capabilities", "supplier_evidence",
        "project_suppliers", "requirement_evaluations", "supplier_explanation_run_steps",
        "quotes", "quote_values", "quote_documents", "document_blocks", "quote_field_evidence",
        "comparisons",
    }.issubset(table_names)
    assert table_names - {
        "demo_sessions",
        "projects",
        "ai_runs",
        "briefs",
        "requirements",
        "suppliers",
        "supplier_capabilities",
        "supplier_evidence",
        "project_suppliers",
        "requirement_evaluations",
        "supplier_explanation_run_steps",
        "quotes",
        "quote_values",
        "quote_documents",
        "document_blocks",
        "quote_field_evidence",
        "comparisons",
        "alembic_version",
    } == set()

    demo_session_unique_constraints = [
        constraint
        for constraint in inspect(test_engine).get_unique_constraints("demo_sessions")
        if constraint["column_names"] == ["opaque_token"]
    ]

    assert len(demo_session_unique_constraints) == 1

    project_columns = {column["name"]: column for column in inspect(test_engine).get_columns("projects")}
    brief_columns = {column["name"]: column for column in inspect(test_engine).get_columns("briefs")}
    requirement_columns = {column["name"]: column for column in inspect(test_engine).get_columns("requirements")}
    quote_columns = {column["name"]: column for column in inspect(test_engine).get_columns("quotes")}
    quote_document_columns = {
        column["name"]: column for column in inspect(test_engine).get_columns("quote_documents")
    }
    comparison_columns = {
        column["name"]: column for column in inspect(test_engine).get_columns("comparisons")
    }

    assert not project_columns["brief_revision"]["nullable"]
    assert project_columns["brief_revision"]["default"] == "0"
    assert brief_columns["quantity"]["nullable"]
    assert brief_columns["delivery_target"]["nullable"]
    assert brief_columns["target_unit_price"]["nullable"]
    assert "IN_PROGRESS" in str(brief_columns["status"]["default"])
    assert requirement_columns["importance"]["nullable"]
    assert not quote_columns["revision"]["nullable"]
    assert quote_columns["revision"]["default"] == "0"
    assert quote_document_columns["evidence_capture_version"]["nullable"]
    assert not quote_document_columns["is_active"]["nullable"]
    assert not comparison_columns["brief_revision"]["nullable"]
    assert not comparison_columns["quote_revision_snapshot"]["nullable"]
    assert not comparison_columns["comparison_payload"]["nullable"]
    assert not comparison_columns["stale"]["nullable"]
    assert any(index["name"] == "uq_quote_documents_one_active_per_quote"
               and index["unique"] for index in inspect(test_engine).get_indexes("quote_documents"))


def test_active_document_migration_backfills_single_canonical_document(
    database_session: Session, test_database_url: str, test_engine: Engine,
) -> None:
    from alembic import command

    project, supplier = quote_candidate(database_session)
    quote = create_quote(database_session, project_id=project.id, supplier_id=supplier.id,
                         entry_type=QuoteEntryType.PDF, status=QuoteStatus.PROCESSING)
    document = QuoteDocument(
        quote_id=quote.id, storage_key="canonical-pdf", original_filename="quote.pdf",
        sha256="a" * 64, page_count=1, processing_status="PROCESSING", processing_attempts=1,
        is_active=True,
    )
    database_session.add(document)
    database_session.commit()
    document_id = document.id
    config = alembic_config(test_database_url)
    command.downgrade(config, "0012_evidence_capture_marker")
    command.upgrade(config, "head")
    with test_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT is_active FROM quote_documents WHERE id = :document_id"
        ), {"document_id": document_id}).scalar_one()


def test_only_one_active_document_is_allowed_per_quote(database_session: Session) -> None:
    project, supplier = quote_candidate(database_session)
    quote = create_quote(database_session, project_id=project.id, supplier_id=supplier.id,
                         entry_type=QuoteEntryType.PDF, status=QuoteStatus.PROCESSING)
    database_session.add_all([
        QuoteDocument(
            quote_id=quote.id, storage_key=f"active-{index}", original_filename=f"{index}.pdf",
            sha256=str(index) * 64, page_count=1, processing_status="PROCESSING",
            processing_attempts=1, is_active=True,
        ) for index in (1, 2)
    ])
    with pytest.raises(IntegrityError):
        database_session.commit()
    database_session.rollback()


@pytest.mark.parametrize("document_count", [0, 2], ids=["missing", "ambiguous"])
def test_active_document_migration_rejects_missing_or_ambiguous_existing_data(
    database_session: Session, test_database_url: str, test_engine: Engine,
    document_count: int,
) -> None:
    from alembic import command

    project, supplier = quote_candidate(database_session)
    quote = create_quote(database_session, project_id=project.id, supplier_id=supplier.id,
                         entry_type=QuoteEntryType.PDF, status=QuoteStatus.PROCESSING)
    if document_count == 2:
        database_session.add(QuoteDocument(
            quote_id=quote.id, storage_key="first-pdf", original_filename="first.pdf",
            sha256="a" * 64, page_count=1, processing_status="PROCESSING", processing_attempts=1,
            is_active=True,
        ))
    database_session.commit()
    quote_id = quote.id
    config = alembic_config(test_database_url)
    command.downgrade(config, "0012_evidence_capture_marker")
    if document_count == 2:
        with test_engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO quote_documents
                    (id, quote_id, storage_key, original_filename, sha256, page_count,
                     processing_status, processing_attempts)
                VALUES (:id, :quote_id, 'second-pdf', 'second.pdf', :sha256, 1, 'FAILED', 1)
            """), {"id": uuid4(), "quote_id": quote_id, "sha256": "b" * 64})
    with pytest.raises(RuntimeError, match="canonical PDF document"):
        command.upgrade(config, "head")
    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0012_evidence_capture_marker"
        )


def test_nullable_importance_preserves_existing_rows_through_upgrade(
    test_engine: Engine, test_database_url: str
) -> None:
    from alembic import command
    from tests.database_test_support import alembic_config

    config = alembic_config(test_database_url)
    command.downgrade(config, "0003_brief_requirement_domain")
    with Session(test_engine) as session:
        demo_session = make_demo_session()
        session.add(demo_session)
        session.flush()
        project_id = uuid4()
        # Insert only historical columns: the current ORM includes later decision fields.
        session.execute(text(
            "INSERT INTO projects (id, demo_session_id, name, original_request) "
            "VALUES (:id, :session_id, 'Existing', 'Source bags.')"
        ), {"id": project_id, "session_id": demo_session.id})
        requirement = Requirement(
            project_id=project_id,
            kind="MATERIAL",
            importance="REQUIRED",
            expected_value={"value": "Cotton"},
        )
        session.add(requirement)
        session.commit()
        requirement_id = requirement.id

    command.upgrade(config, "head")
    with Session(test_engine) as session:
        preserved = session.get(Requirement, requirement_id)
        assert preserved is not None
        assert preserved.project_id == project_id
        assert preserved.importance == "REQUIRED"
        assert preserved.expected_value == {"value": "cotton"}
        session.add(
            Requirement(
                project_id=project_id,
                kind="MATERIAL",
                importance=None,
                expected_value={"value": "Polyester"},
            )
        )
        session.commit()
        values = set(
            session.scalars(
                select(Requirement.importance).where(Requirement.project_id == project_id)
            ).all()
        )
        assert values == {"REQUIRED", None}
    with pytest.raises(RuntimeError, match="Resolve unknown requirement importance"):
        command.downgrade(config, "0003_brief_requirement_domain")


def test_project_brief_revision_defaults_to_zero(database_session: Session) -> None:
    project = Project(
        demo_session=make_demo_session(),
        name="New project",
        original_request="Source travel bags.",
    )
    database_session.add(project)
    database_session.commit()
    database_session.expire_all()

    reloaded = database_session.get(Project, project.id)
    assert reloaded is not None
    assert reloaded.brief_revision == 0


def test_project_persists_with_its_demo_session(database_session: Session) -> None:
    demo_session = make_demo_session()
    project = Project(
        demo_session=demo_session,
        name="Recycled Cosmetic Travel Bag",
        original_request="Source 2,000 recycled cosmetic travel bags.",
    )
    database_session.add(project)
    database_session.commit()
    project_id = project.id
    database_session.expire_all()

    reloaded = database_session.get(Project, project_id)

    assert reloaded is not None
    assert reloaded.demo_session_id == demo_session.id
    assert reloaded.demo_session.opaque_token == "token-a"
    assert reloaded.stage == "BRIEF"


def test_project_requires_an_existing_demo_session(database_session: Session) -> None:
    project = Project(
        demo_session_id=uuid4(),
        name="Unowned project",
        original_request="This must fail.",
    )
    database_session.add(project)

    with pytest.raises(IntegrityError):
        database_session.commit()
    database_session.rollback()


def test_demo_session_token_is_unique(database_session: Session) -> None:
    database_session.add(make_demo_session("same-token"))
    database_session.commit()
    database_session.add(make_demo_session("same-token"))

    with pytest.raises(IntegrityError):
        database_session.commit()
    database_session.rollback()


def test_deleting_a_demo_session_cascades_to_its_projects(database_session: Session) -> None:
    demo_session = make_demo_session()
    project = Project(
        demo_session=demo_session,
        name="Cascaded project",
        original_request="This project should be deleted with its session.",
    )
    database_session.add(project)
    database_session.commit()
    project_id = project.id

    database_session.execute(delete(DemoSession).where(DemoSession.id == demo_session.id))
    database_session.commit()
    database_session.expire_all()

    assert database_session.get(Project, project_id) is None


def test_database_is_reset_between_tests(database_session: Session) -> None:
    assert database_session.query(DemoSession).count() == 0
    assert database_session.query(Project).count() == 0


def quote_candidate(database_session: Session, *, shortlisted: bool = True) -> tuple[Project, Supplier]:
    project = Project(
        demo_session=make_demo_session(), name="Quote project",
        original_request="Source travel bags.", stage="COMPARISON",
    )
    supplier = Supplier(
        id=uuid4(), name="Fictional Quote Supplier", country="Testland",
        description="Synthetic supplier for quote persistence tests.",
    )
    database_session.add_all((project, supplier))
    database_session.flush()
    database_session.add(ProjectSupplier(
        project_id=project.id, supplier_id=supplier.id, shortlisted=shortlisted,
        dismissed=False, evaluated_against_brief_revision=0,
    ))
    database_session.flush()
    return project, supplier


def test_quote_creation_requires_shortlisted_candidate_but_not_exact_stage(
    database_session: Session,
) -> None:
    project, supplier = quote_candidate(database_session)
    quote = create_quote(
        database_session, project_id=project.id, supplier_id=supplier.id,
        entry_type=QuoteEntryType.MANUAL,
    )
    database_session.commit()
    database_session.expire_all()

    saved = database_session.get(Quote, quote.id)
    assert saved is not None
    assert saved.project_id == project.id
    assert saved.supplier_id == supplier.id
    assert saved.entry_type == "MANUAL"
    assert saved.status == "NEEDS_REVIEW"
    assert saved.revision == 0


def test_quote_creation_rejects_unshortlisted_or_unlinked_supplier(
    database_session: Session,
) -> None:
    project, supplier = quote_candidate(database_session, shortlisted=False)
    with pytest.raises(QuoteCandidateNotShortlistedError, match="not shortlisted"):
        create_quote(
            database_session, project_id=project.id, supplier_id=supplier.id,
            entry_type=QuoteEntryType.MANUAL,
        )
    with pytest.raises(QuoteCandidateNotShortlistedError, match="not shortlisted"):
        create_quote(
            database_session, project_id=project.id, supplier_id=uuid4(),
            entry_type=QuoteEntryType.MANUAL,
        )
    assert database_session.query(Quote).count() == 0


def test_quote_and_field_uniqueness_and_supplier_foreign_key(database_session: Session) -> None:
    project, supplier = quote_candidate(database_session)
    quote = create_quote(
        database_session, project_id=project.id, supplier_id=supplier.id,
        entry_type=QuoteEntryType.MANUAL,
    )
    quote.values.append(QuoteValue(
        field_key="quoted_quantity", current_value=2000,
        current_origin="USER_ENTERED", ai_extracted_value=None,
    ))
    database_session.commit()

    with pytest.raises(IntegrityError):
        create_quote(
            database_session, project_id=project.id, supplier_id=supplier.id,
            entry_type=QuoteEntryType.PDF, status=QuoteStatus.PROCESSING,
        )
    database_session.rollback()
    database_session.add(QuoteValue(
        quote_id=quote.id, field_key="quoted_quantity", current_value=3000,
        current_origin="USER_ENTERED", ai_extracted_value=None,
    ))
    with pytest.raises(IntegrityError):
        database_session.commit()
    database_session.rollback()

    database_session.add(Quote(
        project_id=project.id, supplier_id=uuid4(), entry_type="MANUAL",
        status="NEEDS_REVIEW",
    ))
    with pytest.raises(IntegrityError):
        database_session.commit()
    database_session.rollback()


@pytest.mark.parametrize("replacement", [None, {"amount": "9.99", "currency": "USD"}])
def test_stored_ai_extraction_cannot_be_cleared_or_overwritten(
    database_session: Session, replacement: object | None,
) -> None:
    project, supplier = quote_candidate(database_session)
    quote = create_quote(
        database_session, project_id=project.id, supplier_id=supplier.id,
        entry_type=QuoteEntryType.PDF,
    )
    original = {"amount": "4.22", "currency": "USD"}
    quote.values.append(QuoteValue(
        field_key="unit_price", current_value=original,
        current_origin="AI_EXTRACTED", ai_extracted_value=original,
    ))
    database_session.commit()
    database_session.expire_all()

    saved = database_session.get(Quote, quote.id)
    assert saved is not None
    value = saved.values[0]
    value.current_value = {"amount": "4.50", "currency": "USD"}
    value.current_origin = "USER_CORRECTED"
    value.ai_extracted_value = replacement
    with pytest.raises(DBAPIError, match="Stored AI-extracted quote value cannot be changed"):
        database_session.commit()
    database_session.rollback()
    database_session.expire_all()
    persisted = database_session.get(QuoteValue, value.id)
    assert persisted is not None
    assert persisted.ai_extracted_value == original
    assert persisted.current_value == original
    assert persisted.current_origin == "AI_EXTRACTED"


def test_quote_provenance_round_trip_and_confirmed_current_authority(
    database_session: Session,
) -> None:
    project, supplier = quote_candidate(database_session)
    quote = create_quote(
        database_session, project_id=project.id, supplier_id=supplier.id,
        entry_type=QuoteEntryType.PDF,
    )
    extracted = {"amount": "4.22", "currency": "USD"}
    corrected = {"amount": "4.50", "currency": "USD"}
    quote.values.extend((
        QuoteValue(
            field_key="unit_price", current_value=extracted,
            current_origin="AI_EXTRACTED", ai_extracted_value=extracted,
        ),
        QuoteValue(
            field_key="shipping_cost", current_value=None,
            current_origin="AI_EXTRACTED", ai_extracted_value=None,
            uncertainty="Not stated in the quote.",
        ),
    ))
    database_session.commit()
    database_session.expire_all()
    saved = database_session.get(Quote, quote.id)
    assert saved is not None
    assert authoritative_current_values(
        saved.status, ((value.field_key, value.current_value) for value in saved.values)
    ) is None

    unit_price = next(value for value in saved.values if value.field_key == "unit_price")
    unit_price.current_value = corrected
    unit_price.current_origin = "USER_CORRECTED"
    saved.status = "CONFIRMED"
    database_session.commit()
    database_session.expire_all()
    confirmed = database_session.get(Quote, quote.id)
    assert confirmed is not None
    corrected_value = next(value for value in confirmed.values if value.field_key == "unit_price")
    assert corrected_value.ai_extracted_value == extracted
    assert corrected_value.current_value == corrected
    assert corrected_value.current_origin == "USER_CORRECTED"
    assert authoritative_current_values(
        confirmed.status,
        ((value.field_key, value.current_value) for value in confirmed.values),
    ) == {
        "unit_price": corrected, "shipping_cost": None,
    }


def test_candidate_removal_preserves_quote_and_project_cleanup_works(
    database_session: Session,
) -> None:
    project, supplier = quote_candidate(database_session)
    quote = create_quote(
        database_session, project_id=project.id, supplier_id=supplier.id,
        entry_type=QuoteEntryType.MANUAL,
    )
    database_session.commit()
    quote_id = quote.id
    demo_session_id = project.demo_session_id

    database_session.execute(delete(ProjectSupplier).where(
        ProjectSupplier.project_id == project.id,
        ProjectSupplier.supplier_id == supplier.id,
    ))
    database_session.commit()
    database_session.expire_all()
    assert database_session.get(ProjectSupplier, (project.id, supplier.id)) is None
    saved = database_session.get(Quote, quote_id)
    assert saved is not None
    assert saved.project_id == project.id
    assert saved.supplier_id == supplier.id

    database_session.execute(delete(DemoSession).where(DemoSession.id == demo_session_id))
    database_session.commit()
    database_session.expire_all()
    assert database_session.get(Quote, quote_id) is None
