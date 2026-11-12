"""Recover failures through the real Analyst, freshness check and terminal trace."""
import asyncio
import logging
import threading
import time
from uuid import UUID, uuid4

import pytest
from psycopg.errors import LockNotAvailable, QueryCanceled
from sqlalchemy import Engine, event, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.util import await_only

from sourcepilot.ai.client import AnalystModelInvocation
from sourcepilot.persistence.models import AIRun, Comparison, SupplierExplanationRunStep
from tests.test_comparison_advice import AdviceModel
from tests.test_tradeoff_analysis import (  # noqa: F401
    FakeModel,
    client,
    database_url,
    engine,
    ready,
)

# ruff: noqa: F811 -- shared guarded database fixtures


@pytest.mark.parametrize("failure", ["query", "flush", "commit", "rollback"])
@pytest.mark.parametrize("stale", [False, True])
def test_failed_transaction_recovers_before_freshness_and_terminal_trace(
    client, engine, monkeypatch, failure, stale,
):
    from sourcepilot.ai import tradeoff_analysis

    project, _, _ = ready(client)
    path = f"/projects/{project}/comparison"
    before = client.get(path).json()
    model = AdviceModel(actions=["tool", "final"])
    monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", lambda: model)
    original = tradeoff_analysis._tool_output
    original_rollback = Session.rollback

    def rollback(session):
        if session.info.pop("fail_rollback", False):
            raise RuntimeError("synthetic rollback failure")
        original_rollback(session)

    monkeypatch.setattr(Session, "rollback", rollback)

    def fail(session, *args):
        if stale:
            with Session(engine) as other:
                row = other.get(Comparison, UUID(before["id"]))
                assert row is not None
                row.stale = True
                other.commit()
        if failure == "rollback":
            session.info["fail_rollback"] = True
        if failure in {"query", "rollback"}:
            session.execute(text("select 1 / 0"))
        else:
            session.add(SupplierExplanationRunStep(air_run_id=uuid4(), sequence=999,
                                                  kind="tool", outcome="ERROR"))
            if failure == "flush":
                session.flush()
            else:
                session.commit()
        raise AssertionError("Database constraint failure must propagate")

    monkeypatch.setattr(tradeoff_analysis, "_tool_output", fail)
    response = client.post(path + "/advice", json={"snapshot_id": before["id"]})
    assert response.status_code == (409 if stale else 503), response.text
    with Session(engine) as session:
        run = session.scalar(select(AIRun).where(AIRun.project_id == UUID(project)))
        assert run is not None and run.status == "FAILED" and run.completed_at is not None
        terminal = session.scalars(select(SupplierExplanationRunStep).where(
            SupplierExplanationRunStep.air_run_id == run.id,
            SupplierExplanationRunStep.kind == "run")).all()
        assert len(terminal) == 1 and terminal[0].outcome == "FAILED"
    if not stale:
        assert client.get(path).json() == before
        monkeypatch.setattr(tradeoff_analysis, "_tool_output", original)
        monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", AdviceModel)
        assert client.post(path + "/advice", json={"snapshot_id": before["id"]}).status_code == 200


@pytest.mark.parametrize("outcome", ["stale", "timeout", "late_stale"])
def test_final_freshness_stale_precedence_only_within_work_budget(client, engine, monkeypatch, outcome):
    from sourcepilot.ai import tradeoff_analysis

    project, _, _ = ready(client)
    path = f"/projects/{project}/comparison"
    before = client.get(path).json()
    monkeypatch.setenv("NEXT_PUBLIC_SOURCEPILOT_ANALYSIS_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("SOURCEPILOT_ANALYSIS_CLEANUP_SECONDS", "0.5")
    monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", AdviceModel)
    original = tradeoff_analysis._current_snapshot

    def verify(session, **kwargs):
        if kwargs.get("expected") is not None:
            if outcome in {"stale", "late_stale"}:
                if outcome == "late_stale":
                    from sourcepilot.comparison.deadline import current_deadline
                    deadline = current_deadline.get()
                    assert deadline is not None
                    deadline.started = deadline.clock() - 1.6
                raise tradeoff_analysis.TradeoffNotReadyError("COMPARISON_STALE", "Inputs changed.")
            session.execute(text("select pg_sleep(60)"))
        return original(session, **kwargs)

    monkeypatch.setattr(tradeoff_analysis, "_current_snapshot", verify)
    response = client.post(path + "/advice", json={"snapshot_id": before["id"]})
    assert response.status_code == (409 if outcome == "stale" else 504), response.text
    assert client.get(path).json() == before
    with Session(engine) as session:
        run = session.scalar(select(AIRun).where(AIRun.project_id == UUID(project)))
        assert run is not None and run.status == ("FAILED" if outcome == "stale" else "TIMED_OUT")
        assert run.completed_at is not None


@pytest.mark.parametrize("stage", ["model", "recovery_freshness"])
def test_external_cancellation_propagates_after_single_terminal_record(client, engine, monkeypatch, stage):
    from sourcepilot.ai import tradeoff_analysis
    from sourcepilot.ai.comparison_advice import analyze_comparison_advice
    from sourcepilot.comparison.execution import comparison_cli_lifecycle, run_async_comparison
    from sourcepilot.persistence.models import Project

    project_id, _, _ = ready(client)
    snapshot = client.get(f"/projects/{project_id}/comparison").json()

    def cancel():
        task = asyncio.current_task()
        assert task is not None
        asyncio.get_running_loop().call_soon(task.cancel)
        await_only(asyncio.sleep(60))
        raise AssertionError("External cancellation must not return a result")

    class CancelModel(AdviceModel):
        def invoke_with_tools(self, **kwargs):
            return cancel()

    factory = CancelModel
    if stage == "recovery_freshness":
        original_snapshot = tradeoff_analysis._current_snapshot

        def fail(session, *args):
            session.execute(text("select 1 / 0"))

        def verify(session, **kwargs):
            if kwargs.get("expected") is not None:
                cancel()
            return original_snapshot(session, **kwargs)

        monkeypatch.setattr(tradeoff_analysis, "_tool_output", fail)
        monkeypatch.setattr(tradeoff_analysis, "_current_snapshot", verify)
        factory = lambda: AdviceModel(actions=["tool", "final"])

    with Session(engine) as metadata:
        project = metadata.get(Project, UUID(project_id))
        assert project is not None
        session_id = project.demo_session_id

        def operation(owned):
            return analyze_comparison_advice(owned, demo_session_id=session_id,
                project_id=UUID(project_id), snapshot_id=UUID(snapshot["id"]),
                client_factory=factory)

        with comparison_cli_lifecycle() as runner, pytest.raises(asyncio.CancelledError):
            runner.run(run_async_comparison(metadata, operation))
        run = metadata.scalar(select(AIRun).where(AIRun.project_id == UUID(project_id)))
        assert run is not None and run.status == "FAILED" and run.error_type == "INTERRUPTED"
        assert run.completed_at is not None
        terminal = metadata.scalars(select(SupplierExplanationRunStep).where(
            SupplierExplanationRunStep.air_run_id == run.id,
            SupplierExplanationRunStep.kind == "run")).all()
        assert len(terminal) == 1


def test_timeout_during_error_recovery_freshness_still_finalizes_timeout(client, engine, monkeypatch):
    from sourcepilot.ai import tradeoff_analysis

    project_id, _, _ = ready(client)
    path = f"/projects/{project_id}/comparison"
    snapshot = client.get(path).json()
    monkeypatch.setenv("NEXT_PUBLIC_SOURCEPILOT_ANALYSIS_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("SOURCEPILOT_ANALYSIS_CLEANUP_SECONDS", "0.5")
    monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment",
                        lambda: AdviceModel(actions=["tool", "final"]))
    original_snapshot = tradeoff_analysis._current_snapshot

    def fail(session, *args):
        session.execute(text("select 1 / 0"))

    def verify(session, **kwargs):
        if kwargs.get("expected") is not None:
            session.execute(text("select pg_sleep(60)"))
        return original_snapshot(session, **kwargs)

    monkeypatch.setattr(tradeoff_analysis, "_tool_output", fail)
    monkeypatch.setattr(tradeoff_analysis, "_current_snapshot", verify)
    response = client.post(path + "/advice", json={"snapshot_id": snapshot["id"]})
    assert response.status_code == 504, response.text
    assert response.json()["error"]["code"] == "COMPARISON_ANALYSIS_TIMEOUT"
    with Session(engine) as session:
        run = session.scalar(select(AIRun).where(AIRun.project_id == UUID(project_id)))
        assert run is not None and run.status == "TIMED_OUT" and run.completed_at is not None
        assert run.error_type == "ComparisonDeadlineError"
        terminal = session.scalars(select(SupplierExplanationRunStep).where(
            SupplierExplanationRunStep.air_run_id == run.id,
            SupplierExplanationRunStep.kind == "run")).all()
        assert len(terminal) == 1 and terminal[0].outcome == "TIMED_OUT"


def recovery_business_state(engine: Engine) -> dict[str, list[dict[str, object]]]:
    from sourcepilot.persistence.models import (
        Brief,
        Project,
        ProjectSupplier,
        Quote,
        QuoteFieldEvidence,
        QuoteValue,
        Requirement,
    )

    with engine.connect() as connection:
        return {model.__tablename__: [dict(row) for row in connection.execute(
            select(model.__table__).order_by(*model.__table__.primary_key)).mappings()]
            for model in (Project, Brief, Requirement, ProjectSupplier, Quote, QuoteValue,
                          QuoteFieldEvidence, Comparison)}


@pytest.mark.parametrize("endpoint", ["advice", "analysis"])
@pytest.mark.parametrize("ordering", ["database_first", "application_first", "lock", "unavailable"])
def test_controlled_recovery_timeout_ordering(
    client, engine, monkeypatch, record_property, endpoint, ordering,
):
    from sourcepilot.ai import tradeoff_analysis
    from sourcepilot.comparison.deadline import current_deadline
    from sourcepilot.main import app

    project_id, _, _ = ready(client)
    path = f"/projects/{project_id}/comparison"
    snapshot = client.get(path).json()
    before = recovery_business_state(engine)
    monkeypatch.setenv("NEXT_PUBLIC_SOURCEPILOT_ANALYSIS_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("SOURCEPILOT_ANALYSIS_CLEANUP_SECONDS", "0.5")
    factory = AdviceModel if endpoint == "advice" else FakeModel
    model = factory(actions=["tool", "final"])
    monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", lambda: model)
    original_snapshot = tradeoff_analysis._current_snapshot
    original_tool = tradeoff_analysis._tool_output
    events = []

    def fail(session, *args):
        events.append("initial_failure")
        session.execute(text("select 1 / 0"))

    def verify(session, **kwargs):
        if kwargs.get("expected") is None:
            return original_snapshot(session, **kwargs)
        events.append("recovery_freshness")
        deadline = current_deadline.get()
        assert deadline is not None and deadline.work_timeout is not None
        if ordering == "application_first":
            deadline.work_timeout.reschedule(asyncio.get_running_loop().time())
            try:
                await_only(asyncio.Future())
            except asyncio.CancelledError:
                assert deadline.work_timeout.expired()
                events.append("application_cancelled")
                raise
            raise AssertionError("Scheduled work timeout must cancel freshness")
        if ordering == "lock":
            events.append("55P03")
            raise OperationalError("synthetic lock timeout", {}, LockNotAvailable())
        if ordering == "unavailable":
            events.append("non_timeout")
            raise RuntimeError("synthetic recovery failure")

        bind = session.get_bind()

        def database_timeout(connection, cursor, statement, parameters, context, executemany):
            if "repair_u4_recovery_wait" in statement:
                # Installed after the request's own statement guard. This orders
                # PostgreSQL cancellation first without extending any budget.
                cursor.execute("SET LOCAL statement_timeout = '1ms'")
                events.append("database_timeout_armed")

        event.listen(bind, "before_cursor_execute", database_timeout)
        try:
            session.execute(text("select pg_sleep(60) /* repair_u4_recovery_wait */"))
        except OperationalError as error:
            assert isinstance(error.orig, QueryCanceled)
            assert error.orig.sqlstate == "57014"
            assert not deadline.work_timeout.expired()
            assert deadline.remaining() > 0
            events.append("57014_before_application_timeout")
            record_property("database_timeout_order", {
                "sqlstate": error.orig.sqlstate, "work_timer_expired": False,
                "positive_work_budget": True,
            })
            raise
        finally:
            event.remove(bind, "before_cursor_execute", database_timeout)
            assert not event.contains(bind, "before_cursor_execute", database_timeout)
        raise AssertionError("PostgreSQL statement timeout must interrupt freshness")

    monkeypatch.setattr(tradeoff_analysis, "_tool_output", fail)
    monkeypatch.setattr(tradeoff_analysis, "_current_snapshot", verify)
    response = client.post(path + "/" + endpoint, json={"snapshot_id": snapshot["id"]})
    expected_event = {
        "database_first": ["database_timeout_armed", "57014_before_application_timeout"],
        "application_first": ["application_cancelled"], "lock": ["55P03"],
        "unavailable": ["non_timeout"],
    }
    assert events == ["initial_failure", "recovery_freshness", *expected_event[ordering]]
    assert model.calls == 1 and model.actions == ["final"]
    assert recovery_business_state(engine) == before
    assert client.get(path).json() == snapshot
    assert not app.state.comparison_lifecycle.owners
    with engine.connect() as connection:
        assert connection.scalar(text(
            "select count(*) from pg_stat_activity where datname=current_database() "
            "and pid<>pg_backend_pid() and state='active' "
            "and query like '%repair_u4_recovery_wait%'")) == 0
    with Session(engine) as session:
        run = session.scalars(select(AIRun).where(AIRun.project_id == UUID(project_id))).one()
        terminal = session.scalars(select(SupplierExplanationRunStep).where(
            SupplierExplanationRunStep.air_run_id == run.id,
            SupplierExplanationRunStep.kind == "run")).all()
        observed = (response.status_code, response.json()["error"]["code"], run.status,
                    run.error_type, run.completed_at is not None,
                    [step.outcome for step in terminal])
        record_property("recovery_outcome", repr(observed))
        if ordering == "unavailable":
            code = ("COMPARISON_ADVICE_UNAVAILABLE" if endpoint == "advice"
                    else "TRADEOFF_ANALYSIS_UNAVAILABLE")
            assert observed == (503, code, "FAILED", "INTERRUPTED", True, ["FAILED"])
        else:
            assert observed == (504, "COMPARISON_ANALYSIS_TIMEOUT", "TIMED_OUT",
                                "ComparisonDeadlineError", True, ["TIMED_OUT"])
        run_id = run.id

    monkeypatch.setattr(tradeoff_analysis, "_tool_output", original_tool)
    monkeypatch.setattr(tradeoff_analysis, "_current_snapshot", original_snapshot)
    monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", factory)
    retry = client.post(path + "/" + endpoint, json={"snapshot_id": snapshot["id"]})
    assert retry.status_code == 200, retry.text
    assert recovery_business_state(engine) == before
    assert not app.state.comparison_lifecycle.owners
    with Session(engine) as session:
        runs = session.scalars(select(AIRun).where(AIRun.project_id == UUID(project_id))).all()
        assert len(runs) == 2
        retried = next(row for row in runs if row.id != run_id)
        assert retried.status == "COMPLETED" and retried.completed_at is not None
        for row in runs:
            outcomes = session.scalars(select(SupplierExplanationRunStep.outcome).where(
                SupplierExplanationRunStep.air_run_id == row.id,
                SupplierExplanationRunStep.kind == "run")).all()
            assert outcomes == [row.status]


def test_http_capacity_survives_repeated_timeouts_and_recovers(client, monkeypatch):
    import socket

    from sourcepilot.main import app

    project, _, _ = ready(client)
    path = f"/projects/{project}/comparison"
    before = client.get(path).json()
    runtime = app.state.comparison_lifecycle
    runtime.capacity = 1
    monkeypatch.setenv("NEXT_PUBLIC_SOURCEPILOT_ANALYSIS_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("SOURCEPILOT_ANALYSIS_CLEANUP_SECONDS", "0.5")
    release = threading.Event()

    def resolve(*args, **kwargs):
        assert release.wait(5)
        return []

    real_resolver = socket.getaddrinfo

    class ResolverModel(AdviceModel):
        def invoke_with_tools(self, **kwargs) -> AnalystModelInvocation:
            # Only the synthetic model lookup is blocked, not PostgreSQL setup.
            with monkeypatch.context() as patch:
                patch.setattr(socket, "getaddrinfo", resolve)
                await_only(asyncio.get_running_loop().getaddrinfo("fixture.invalid", 443))
            raise AssertionError("No model continuation after timeout")

    try:
        for _ in range(2):
            release.clear()
            monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", ResolverModel)
            first = client.post(path + "/advice", json={"snapshot_id": before["id"]})
            assert first.status_code == 504, first.text
            start = time.monotonic()
            for _ in range(3):
                busy = client.post(path + "/advice", json={"snapshot_id": before["id"]})
                assert busy.status_code == 503 and busy.json()["error"]["code"] == "COMPARISON_ANALYSIS_BUSY"
            assert time.monotonic() - start < 1
            release.set()
            for _ in range(100):
                if not runtime.owners:
                    break
                time.sleep(0.01)
            assert not runtime.owners
            assert socket.getaddrinfo is real_resolver
        monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", AdviceModel)
        assert client.post(path + "/advice", json={"snapshot_id": before["id"]}).status_code == 200
        assert client.get(path).json() == before
    finally:
        release.set()


def test_failed_terminal_persistence_is_unconfirmed_and_cannot_return_advice(
    client, engine, monkeypatch, caplog,
):
    from sourcepilot.ai.tracing import RunTrace

    # Migration fixture fileConfig disables loggers created by earlier cases.
    monkeypatch.setattr(logging.getLogger("sourcepilot.ai.tradeoff_analysis"), "disabled", False)
    caplog.set_level("WARNING", logger="sourcepilot.ai.tradeoff_analysis")
    project, _, _ = ready(client)
    path = f"/projects/{project}/comparison"
    before = client.get(path).json()
    monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", AdviceModel)

    def fail(trace):
        trace.session.execute(text("select 1 / 0 /* sensitive-terminal-sentinel */"))

    monkeypatch.setattr(RunTrace, "finish", fail)
    response = client.post(path + "/advice", json={"snapshot_id": before["id"]})
    assert response.status_code == 503, response.text
    assert "terminal trace persistence unconfirmed" in caplog.text
    assert "sensitive-terminal-sentinel" not in caplog.text + response.text
    assert client.get(path).json() == before
    with Session(engine) as session:
        run = session.scalar(select(AIRun).where(AIRun.project_id == UUID(project)))
        assert run is not None and run.status == "RUNNING" and run.completed_at is None
        terminal = session.scalars(select(SupplierExplanationRunStep).where(
            SupplierExplanationRunStep.air_run_id == run.id,
            SupplierExplanationRunStep.kind == "run")).all()
        assert not terminal


@pytest.mark.parametrize("failure", ["close", "cancel_close", "dispose", "exhausted"])
def test_actual_request_cleanup_attempts_and_forced_connection_release(
    client, engine, monkeypatch, failure, caplog,
):
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

    from sourcepilot.comparison import execution
    from sourcepilot.main import app

    project, _, _ = ready(client)
    monkeypatch.setattr(execution.logger, "disabled", False)
    caplog.set_level("WARNING", logger="sourcepilot.comparison.execution")
    path = f"/projects/{project}/comparison"
    before = client.get(path).json()
    events = []
    original_close, original_dispose = AsyncSession.close, AsyncEngine.dispose

    async def close(session):
        events.append("close")
        if failure == "close":
            raise RuntimeError("sensitive-cleanup-sentinel")
        if failure == "cancel_close":
            raise asyncio.CancelledError()
        await original_close(session)

    async def dispose(engine, *args, **kwargs):
        events.append("dispose")
        if failure == "dispose":
            raise RuntimeError("sensitive-cleanup-sentinel")
        await original_dispose(engine, *args, **kwargs)

    class LateModel(AdviceModel):
        def invoke_with_tools(self, **kwargs):
            result = super().invoke_with_tools(**kwargs)
            if failure == "exhausted":
                from sourcepilot.comparison.deadline import current_deadline
                deadline = current_deadline.get()
                assert deadline is not None
                deadline.started -= deadline.settings.total + 1
            return result

    monkeypatch.setattr(AsyncSession, "close", close)
    monkeypatch.setattr(AsyncEngine, "dispose", dispose)
    monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", LateModel)
    response = client.post(path + "/advice", json={"snapshot_id": before["id"]})
    assert response.status_code == 504, response.text
    assert events == ["close", "dispose"]
    assert "Comparison cleanup incomplete" in caplog.text
    assert "sensitive-cleanup-sentinel" not in caplog.text
    assert not app.state.comparison_lifecycle.owners
    assert client.get(path).json() == before
