"""Provider-free timing tests with SQLite projections and PostgreSQL transactions."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, event, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles, deregister
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from sourcepilot.ai.supplier_explanation import ExplanationNotReadyError, explain_supplier
from sourcepilot.comparison.source_resolution import FactContext, SourceFact, resolve_sources
from sourcepilot.persistence.models import (
    AIRun,
    Base,
    Brief,
    DemoSession,
    Project,
    ProjectSupplier,
    Quote,
    QuoteFieldEvidence,
    QuoteValue,
    Supplier,
)
from sourcepilot.suppliers.service import list_project_suppliers
from sourcepilot.suppliers.timing import TimingScopeError, read_supplier_timing, timing_disclosure
from tests.database_test_support import (
    create_test_engine,
    persistence_test_database_url_from_environment,
)
from tests.test_supplier_explanation import FakeClient


@pytest.fixture
def saved() -> Iterator[tuple[Session, DemoSession, Project, Supplier]]:
    # Compile JSONB as JSON only for this isolated fixture; no external URL is read.
    compiles(JSONB, "sqlite")(lambda element, compiler, **kw: "JSON")
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    try:
        # Unrelated PDF text-regex constraints are PostgreSQL-only. These tests
        # exercise ORM scope/values, not migrations or database lock semantics.
        Base.metadata.create_all(engine, tables=[
            t for t in Base.metadata.sorted_tables if t.name != "document_blocks"
        ])
        with Session(engine, expire_on_commit=False) as session:
            actor = DemoSession(opaque_token="synthetic-only", expires_at=datetime.now(UTC)+timedelta(days=1))
            supplier = Supplier(id=uuid4(), name="Test", country="Demo", description="Synthetic",
                                general_lead_time_days=32)
            session.add_all([actor, supplier])
            session.flush()
            project = Project(demo_session_id=actor.id, name="Test", original_request="Test",
                              stage="SUPPLIERS", brief_revision=1)
            session.add(project)
            session.flush()
            session.add_all([
                Brief(project_id=project.id, destination="Sydney",
                      delivery_target={"kind":"DATE", "date":"2027-03-01"}, status="APPROVED"),
                ProjectSupplier(project_id=project.id, supplier_id=supplier.id,
                                shortlisted=True, dismissed=False, evaluated_against_brief_revision=1),
            ])
            session.commit()
            yield session, actor, project, supplier
    finally:
        engine.dispose()
        deregister(JSONB)


def read(saved):
    session, actor, project, supplier = saved
    return read_supplier_timing(session, demo_session_id=actor.id,
                                project_id=project.id, supplier_id=supplier.id)


def quote(saved, status="CONFIRMED"):
    session, _, project, supplier = saved
    result = Quote(project_id=project.id, supplier_id=supplier.id, entry_type="MANUAL",
                   status=status, revision=1)
    result.values = [QuoteValue(field_key="production_lead_time", current_value="25 days",
                                current_origin="USER_ENTERED")]
    session.add(result)
    session.commit()
    return result


def test_no_quote_and_typical_only_are_unknown_without_writes(saved):
    session, _, project, _ = saved
    statements = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(session.get_bind(), "before_cursor_execute", capture)
    result = read(saved)
    listed = list_project_suppliers(session, project)
    assert listed.suppliers[0].timing_disclosure == result
    assert result.delivery_target == {"kind":"DATE", "date":"2027-03-01"}
    assert result.production.status == result.delivery.status == "UNKNOWN"
    assert result.production.facts == []
    assert all(s.lstrip().upper().startswith("SELECT") for s in statements)


@pytest.mark.parametrize("joined_savepoint", [False, True], ids=["session", "savepoint"])
@pytest.mark.parametrize("finish", ["commit", "rollback"])
def test_postgres_timing_preserves_edits_and_caller_transaction(
    joined_savepoint: bool, finish: str,
) -> None:
    engine = create_test_engine(persistence_test_database_url_from_environment())
    actor_id = uuid4()
    supplier_id = uuid4()
    try:
        with engine.connect() as connection:
            outer = connection.begin() if joined_savepoint else None
            with Session(
                bind=connection, expire_on_commit=False,
                join_transaction_mode="create_savepoint" if joined_savepoint else "conditional_savepoint",
            ) as session:
                actor = DemoSession(id=actor_id, opaque_token=uuid4().hex,
                                    expires_at=datetime.now(UTC) + timedelta(days=1))
                supplier = Supplier(id=supplier_id, name=f"Timing {uuid4()}", country="Demo",
                                    description="Synthetic transaction regression")
                session.add_all([actor, supplier])
                session.flush()
                project = Project(demo_session_id=actor.id, name="Timing transaction",
                                  original_request="Synthetic", brief_revision=1)
                session.add(project)
                session.flush()
                brief = Brief(project_id=project.id, destination="Sydney", status="APPROVED")
                membership = ProjectSupplier(project_id=project.id, supplier_id=supplier.id,
                                             shortlisted=True, evaluated_against_brief_revision=1)
                value = QuoteValue(field_key="production_lead_time", current_value="25 days",
                                   current_origin="USER_ENTERED")
                quote_record = Quote(project_id=project.id, supplier_id=supplier.id,
                                     entry_type="MANUAL", status="CONFIRMED", revision=1,
                                     values=[value])
                session.add_all([brief, membership, quote_record])
                session.flush()
                project_id, supplier_id = project.id, supplier.id
                transaction = session.get_transaction()
                db_transaction = connection.get_transaction()
                savepoint = connection.get_nested_transaction()
                backend = connection.scalar(text("SELECT pg_backend_pid()"))
                transaction_id = connection.scalar(text("SELECT txid_current()"))
                baseline = read_supplier_timing(session, demo_session_id=actor_id,
                                                project_id=project_id, supplier_id=supplier_id)
                assert baseline.production.status == "CONFIRMED"
                assert baseline.production.facts[0].value == "25 days"
                with Session(engine) as observer:
                    assert observer.get(Project, project_id) is None

                pending_owner = uuid4()
                pending_project = uuid4()
                project.demo_session_id = pending_owner
                supplier.name = "Pending supplier"
                membership.project_id = pending_project
                membership.shortlisted = False
                brief.destination = "Pending destination"
                quote_record.status = "NEEDS_REVIEW"
                value.current_value = "99 days"
                pending = {project, supplier, membership, brief, quote_record, value}
                new_supplier = Supplier(id=uuid4(), name=f"Unflushed {uuid4()}",
                                        country="Demo", description="Synthetic")
                session.add(new_supplier)
                statements: list[str] = []
                boundaries: list[str] = []

                def capture(conn, cursor, statement, parameters, context, executemany):
                    statements.append(statement)

                def committed(conn):
                    boundaries.append("commit")

                def rolled_back(conn):
                    boundaries.append("rollback")

                event.listen(connection, "before_cursor_execute", capture)
                event.listen(connection, "commit", committed)
                event.listen(connection, "rollback", rolled_back)
                try:
                    assert read_supplier_timing(
                        session, demo_session_id=actor_id,
                        project_id=project_id, supplier_id=supplier_id,
                    ) == baseline
                    with pytest.raises(TimingScopeError):
                        read_supplier_timing(session, demo_session_id=uuid4(),
                                             project_id=project_id, supplier_id=supplier_id)
                    assert all(sql.lstrip().upper().startswith("SELECT") for sql in statements)
                    assert statements and boundaries == []
                    assert session.get_transaction() is transaction
                    assert connection.get_transaction() is db_transaction
                    assert connection.get_nested_transaction() is savepoint
                    assert transaction is not None and transaction.is_active
                    assert connection.scalar(text("SELECT pg_backend_pid()")) == backend
                    assert connection.scalar(text("SELECT txid_current()")) == transaction_id
                    assert set(session.dirty) == pending
                    assert set(session.new) == {new_supplier} and not session.deleted
                    assert project.demo_session_id == pending_owner
                    assert supplier.name == "Pending supplier"
                    assert membership.project_id == pending_project and not membership.shortlisted
                    assert brief.destination == "Pending destination"
                    assert quote_record.status == "NEEDS_REVIEW" and value.current_value == "99 days"
                finally:
                    event.remove(connection, "before_cursor_execute", capture)
                    event.remove(connection, "commit", committed)
                    event.remove(connection, "rollback", rolled_back)

                # Discard deliberately invalid pending FK edits; finish only by caller action.
                session.expunge(new_supplier)
                for entity in pending:
                    session.expire(entity)
                if finish == "commit":
                    session.commit()
                    if outer is not None:
                        assert outer.is_active
                        with Session(engine) as observer:
                            assert observer.get(Project, project_id) is None
                        outer.commit()
                else:
                    session.rollback()
                    if outer is not None:
                        assert outer.is_active
                        outer.rollback()
                with Session(engine) as observer:
                    assert (observer.get(Project, project_id) is not None) == (finish == "commit")
    finally:
        # The committed branch deliberately proves caller ownership, then cleans only its rows.
        with engine.begin() as cleanup:
            cleanup.execute(delete(DemoSession).where(DemoSession.id == actor_id))
            cleanup.execute(delete(Supplier).where(Supplier.id == supplier_id))
        engine.dispose()


def test_confirmed_production_is_not_delivery_and_revision_invalidates(saved):
    value = quote(saved)
    before = read(saved)
    assert before.production.status == "CONFIRMED"
    assert before.production.facts[0].value == "25 days"
    assert before.delivery.status == "UNKNOWN"
    value.revision += 1
    saved[0].commit()
    assert read(saved).freshness_key != before.freshness_key


def test_missing_typical_time_is_not_invented(saved):
    session, _, _, supplier = saved
    supplier.general_lead_time_days = None
    session.commit()
    assert read(saved).production.status == "UNKNOWN"
    assert read(saved).production.facts == []


def test_quote_conflict_retains_alternatives_then_honors_correction(saved):
    session = saved[0]
    value = quote(saved).values[0]
    value.current_origin = "AI_EXTRACTED"
    value.ai_extracted_value = "25 days"
    value.evidence = [QuoteFieldEvidence(document_block_id=uuid4(), evidence_value=v)
                      for v in ("25 days", "40 days")]
    session.commit()
    conflict = read(saved)
    assert conflict.production.status == "CONFLICT"
    assert {f.value for f in conflict.production.facts} == {"25 days", "40 days"}
    assert all(f.provenance_evidence_ids and not f.supporting_evidence_ids
               for f in conflict.production.facts)
    value.current_origin = "USER_CORRECTED"
    value.current_value = "30 days"
    session.commit()
    corrected = read(saved)
    assert corrected.production.status == "CONFIRMED"
    assert corrected.production.facts[0].value == "30 days"
    assert corrected.production.facts[0].provenance_evidence_ids
    assert corrected.delivery.status == "UNKNOWN"


@pytest.mark.parametrize("condition", ["unconfirmed", "dismissed", "not_shortlisted", "foreign"])
def test_ineligible_quote_cannot_resolve_timing(saved, condition):
    session, _, project, supplier = saved
    value = quote(saved, "NEEDS_REVIEW" if condition == "unconfirmed" else "CONFIRMED")
    membership = session.get(ProjectSupplier, (project.id, supplier.id))
    assert membership is not None
    if condition == "dismissed": membership.dismissed = True
    if condition == "not_shortlisted": membership.shortlisted = False
    if condition == "foreign": value.project_id = uuid4()
    session.commit()
    assert read(saved).production.status == "UNKNOWN"


def test_foreign_actor_and_expired_session_rejected(saved):
    session, actor, project, supplier = saved
    with pytest.raises(ValueError, match="scope"):
        read_supplier_timing(session, demo_session_id=uuid4(), project_id=project.id,
                             supplier_id=supplier.id)
    actor.expires_at = datetime.now(UTC)-timedelta(days=1)
    session.commit()
    with pytest.raises(ValueError, match="scope"): read(saved)


@pytest.mark.parametrize("target", [None, {"kind":"PERIOD", "label":"Spring", "start_date":None, "end_date":None}])
def test_absent_or_period_target_is_preserved(saved, target):
    session, _, project, _ = saved
    brief = session.get(Brief, project.id)
    assert brief is not None
    brief.delivery_target = target
    session.commit()
    assert read(saved).delivery_target == target


@pytest.mark.parametrize("values,status", [([],"UNKNOWN"), (["2027-02-20"],"CONFIRMED"),
                                          (["2027-02-20","2027-03-20"],"CONFLICT")])
def test_dated_delivery_contract_only(values, status):
    # Current persistence adapter cannot supply these dated facts; no schema expansion.
    facts = tuple(SourceFact("delivery_date", v, FactContext.PROJECT_QUOTE, f"quote:{i}")
                  for i,v in enumerate(values))
    result = timing_disclosure(destination="Sydney", target={"kind":"DATE","date":"2027-03-01"},
        production=resolve_sources("production_lead_time"),
        delivery=resolve_sources("delivery_date", project_facts=facts))
    assert result.delivery.status == status
    assert [f.value for f in result.delivery.facts] == values


def test_explanation_returns_application_disclosure_with_no_extra_turn(saved):
    session, actor, project, supplier = saved
    client = FakeClient(supplier.id)
    result = explain_supplier(session, demo_session_id=actor.id, project_id=project.id,
                              supplier_id=supplier.id, client_factory=lambda:client)
    assert result.timing_disclosure == read(saved)
    assert client.calls == 2
    assert result.explanation.unknowns == []  # No fabricated requirement/model claim.
    assert project.stage == "SUPPLIERS" and project.preferred_supplier_id is None


def test_quote_change_during_generation_rejects_without_retry(saved):
    session, actor, project, supplier = saved
    value = quote(saved)
    def change():
        value.revision += 1
        session.commit()
    client = FakeClient(supplier.id, on_final=change)
    with pytest.raises(ExplanationNotReadyError, match="Timing facts changed"):
        explain_supplier(session, demo_session_id=actor.id, project_id=project.id,
                         supplier_id=supplier.id, client_factory=lambda:client)
    run = session.scalar(select(AIRun))
    assert run is not None and run.status == "FAILED" and run.error_type == "SCOPE_CHANGED"
    assert client.calls == 2


@pytest.mark.parametrize("turns,tools", [(1, 6), (4, 1)])
def test_timing_does_not_expand_analyst_limits(saved, turns, tools):
    from sourcepilot.ai.supplier_explanation import ExplanationUnavailableError

    session, actor, project, supplier = saved
    fake = FakeClient(supplier.id)
    with pytest.raises(ExplanationUnavailableError):
        explain_supplier(session, demo_session_id=actor.id, project_id=project.id,
                         supplier_id=supplier.id, client_factory=lambda:fake,
                         max_model_turns=turns, max_tool_calls=tools)
    run = session.scalar(select(AIRun))
    assert run is not None and run.status == "FAILED_LIMIT_REACHED"
    assert run.model_turn_count <= turns and run.tool_call_count <= tools


def test_api_disclosure_and_foreign_project_rejection(saved, monkeypatch):
    from fastapi import HTTPException
    from starlette.requests import Request

    from sourcepilot.ai.supplier_explanation import SupplierExplanationResponse
    from sourcepilot.main import explain_supplier_endpoint
    from sourcepilot.session.settings import DEMO_SESSION_COOKIE_NAME

    session, actor, project, supplier = saved
    fake = FakeClient(supplier.id)
    monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", lambda: fake)
    request = Request({"type":"http", "headers":[
        (b"cookie", f"{DEMO_SESSION_COOKIE_NAME}={actor.opaque_token}".encode()),
    ]})
    result = explain_supplier_endpoint(project.id, supplier.id, request, session)
    assert isinstance(result, SupplierExplanationResponse) and result.timing_disclosure is not None
    assert result.timing_disclosure.delivery.status == "UNKNOWN"
    assert fake.calls == 2
    with pytest.raises(HTTPException) as rejected:
        explain_supplier_endpoint(project.id, supplier.id,
                                  Request({"type":"http", "headers":[]}), session)
    assert rejected.value.status_code == 401
    assert fake.calls == 2
    session.refresh(project)
    assert project.stage == "SUPPLIERS" and project.preferred_supplier_id is None
