import asyncio
import json
import socket
import threading
import time
from uuid import UUID

import pytest
import uvicorn
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from sqlalchemy.util import await_only

from sourcepilot.ai.client import AnalystModelInvocation
from sourcepilot.ai.comparison_advice import analyze_comparison_advice

# ruff: noqa: F811 -- shared guarded database fixtures.
from sourcepilot.comparison.deadline import (
    ComparisonDeadline,
    ComparisonDeadlineError,
    ComparisonTimeouts,
)
from sourcepilot.comparison.execution import run_bounded_comparison
from sourcepilot.main import app
from sourcepilot.persistence.models import AIRun, Comparison, Project
from tests.test_comparison_advice import AdviceModel
from tests.test_tradeoff_analysis import client, database_url, engine, ready  # noqa: F401


def test_remaining_budget_covers_retries_tools_repair_and_cleanup() -> None:
    now = [0.0]
    deadline = ComparisonDeadline(ComparisonTimeouts(total=180, attempt=60, cleanup=5),
                                  clock=lambda: now[0])
    assert deadline.attempt_seconds() == 60
    # First model, tools, retry/backoff and repair all share the original origin.
    for elapsed, expected in [(60, 60), (90, 60), (130, 45), (174, 1)]:
        now[0] = elapsed
        assert deadline.attempt_seconds() == expected
    now[0] = 175
    with pytest.raises(ComparisonDeadlineError):
        deadline.check()
    deadline.cleaning_up = True
    assert deadline.remaining() == 5
    now[0] = 180
    with pytest.raises(ComparisonDeadlineError):
        deadline.check()


@pytest.mark.parametrize("values", [
    {"total": 0}, {"attempt": -1}, {"cleanup": float("inf")},
    {"total": float("nan")}, {"total": 5, "cleanup": 5},
])
def test_invalid_timeout_configuration(values: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        ComparisonTimeouts(**values)


def test_environment_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXT_PUBLIC_SOURCEPILOT_ANALYSIS_TIMEOUT_SECONDS", "90")
    monkeypatch.setenv("SOURCEPILOT_ANALYSIS_ATTEMPT_SECONDS", "20")
    monkeypatch.setenv("SOURCEPILOT_ANALYSIS_CLEANUP_SECONDS", "3")
    assert ComparisonTimeouts.from_environment() == ComparisonTimeouts(90, 20, 3)


@pytest.mark.parametrize("phase", ["model", "repair", "tool", "backoff", "prepare", "late"])
def test_execution_deadline_including_database_tools(
    client, engine: Engine, monkeypatch: pytest.MonkeyPatch, phase: str,
) -> None:
    from sourcepilot.ai import tradeoff_analysis

    project_id, _, _ = ready(client)
    monkeypatch.setenv("NEXT_PUBLIC_SOURCEPILOT_ANALYSIS_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("SOURCEPILOT_ANALYSIS_CLEANUP_SECONDS", "0.5")
    cancelled = []

    async def stall() -> None:
        try:
            await asyncio.sleep(60)
        finally:
            cancelled.append(True)

    class SlowModel(AdviceModel):
        def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
            if phase == "model" or phase == "repair" and self.calls == 1:
                self.calls += 1
                await_only(stall())
                raise AssertionError("Cancelled model must not return")
            if phase == "late":
                from sourcepilot.comparison.deadline import current_deadline

                result = super().invoke_with_tools(**kwargs)
                deadline = current_deadline.get()
                assert deadline is not None
                deadline.started = deadline.clock() - 1.6
                return result
            return super().invoke_with_tools(**kwargs)

    model = SlowModel(actions=["invalid", "final"] if phase == "repair" else
                      ["provider", "final"] if phase == "backoff" else
                      ["final"] if phase == "late" else ["tool", "final"])
    if phase == "tool":
        def slow_tool(session: Session, *args: object) -> None:
            session.execute(text("select pg_sleep(60)"))
            raise AssertionError("Cancelled database tool must not return")
        monkeypatch.setattr(tradeoff_analysis, "_tool_output", slow_tool)
    if phase == "prepare":
        def slow_snapshot(session: Session, **kwargs: object) -> None:
            session.execute(text("select pg_sleep(60)"))
        monkeypatch.setattr(tradeoff_analysis, "_current_snapshot", slow_snapshot)
    if phase == "backoff":
        monkeypatch.setattr(tradeoff_analysis, "provider_retry_delay_seconds", lambda _: 60)

    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        snapshot_id = session.scalar(select(Comparison.id).where(Comparison.project_id == project.id))
        assert snapshot_id is not None
        started = time.monotonic()
        with pytest.raises(ComparisonDeadlineError):
            analyze_comparison_advice(session, demo_session_id=project.demo_session_id,
                                      project_id=project.id, snapshot_id=snapshot_id,
                                      client_factory=lambda: model)
        assert time.monotonic() - started < 2.75
        assert session.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE "
                                   "datname = current_database() AND state = 'active' "
                                   "AND query = 'select pg_sleep(60)' AND pid <> pg_backend_pid()")) == 0
        run = session.scalar(select(AIRun).where(AIRun.project_id == project.id))
        if phase == "prepare":
            assert run is None and model.calls == 0
        else:
            assert run is not None and run.status == "TIMED_OUT"
            assert run.error_type == "ComparisonDeadlineError"
            assert run.completed_at is not None
            assert model.calls == (2 if phase == "repair" else 1)
        if phase in {"model", "repair"}:
            assert cancelled == [True]


def test_terminal_bookkeeping_has_its_own_bounded_reserve(
    engine: Engine, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sourcepilot.comparison.deadline import current_deadline

    monkeypatch.setenv("NEXT_PUBLIC_SOURCEPILOT_ANALYSIS_TIMEOUT_SECONDS", "10")
    monkeypatch.setenv("SOURCEPILOT_ANALYSIS_CLEANUP_SECONDS", "0.25")

    def cleanup(session: Session) -> None:
        deadline = current_deadline.get()
        assert deadline is not None
        deadline.begin_cleanup()
        session.execute(text("select pg_sleep(60)"))
        raise AssertionError("Slow cleanup must not complete")

    with Session(engine) as session:
        started = time.monotonic()
        with pytest.raises(ComparisonDeadlineError):
            run_bounded_comparison(session, cleanup)
        assert time.monotonic() - started < 1
        assert session.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE "
                                   "datname = current_database() AND state = 'active' "
                                   "AND query = 'select pg_sleep(60)' AND pid <> pg_backend_pid()")) == 0


def test_database_failure_releases_owned_session_and_budget(
    engine: Engine, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sourcepilot.comparison.deadline import current_deadline

    monkeypatch.setenv("NEXT_PUBLIC_SOURCEPILOT_ANALYSIS_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("SOURCEPILOT_ANALYSIS_CLEANUP_SECONDS", "0.5")

    def fail(session: Session) -> None:
        session.execute(text("select 1 / 0"))

    with Session(engine) as session:
        started = time.monotonic()
        with pytest.raises(DBAPIError):
            run_bounded_comparison(session, fail)
        assert time.monotonic() - started < 2.75
        assert current_deadline.get() is None
        assert run_bounded_comparison(session, lambda owned: owned.scalar(text("select 1"))) == 1


def test_timeout_api_preserves_facts_and_explicit_retry_succeeds(
    client, engine: Engine, monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id, _, _ = ready(client)
    path = f"/projects/{project_id}/comparison"
    before = {route: client.get(route).json() for route in (
        path, f"/projects/{project_id}", f"/projects/{project_id}/quotes",
    )}
    monkeypatch.setenv("NEXT_PUBLIC_SOURCEPILOT_ANALYSIS_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("SOURCEPILOT_ANALYSIS_CLEANUP_SECONDS", "0.5")

    class SlowModel(AdviceModel):
        def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
            self.calls += 1
            await_only(asyncio.sleep(60))
            raise AssertionError("No late result")

    model = SlowModel()
    monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", lambda: model)
    response = client.post(path + "/advice", json={"snapshot_id": before[path]["id"]})
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "COMPARISON_ANALYSIS_TIMEOUT"
    assert model.calls == 1
    assert {route: client.get(route).json() for route in before} == before
    model = AdviceModel()
    retry = client.post(path + "/advice", json={"snapshot_id": before[path]["id"]})
    assert retry.status_code == 200, retry.text
    assert model.calls == 1
    with Session(engine) as session:
        runs = session.scalars(select(AIRun).where(AIRun.project_id == UUID(project_id)).order_by(AIRun.started_at)).all()
        assert [run.status for run in runs] == ["TIMED_OUT", "COMPLETED"]


def test_http_disconnect_does_not_escape_backend_deadline(
    client, engine: Engine, monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id, _, _ = ready(client)
    snapshot = client.get(f"/projects/{project_id}/comparison").json()
    monkeypatch.setenv("NEXT_PUBLIC_SOURCEPILOT_ANALYSIS_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("SOURCEPILOT_ANALYSIS_CLEANUP_SECONDS", "0.5")
    entered = threading.Event()
    cancelled = threading.Event()

    async def stall() -> None:
        entered.set()
        try:
            await asyncio.sleep(60)
        finally:
            cancelled.set()

    class SlowModel(AdviceModel):
        def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
            self.calls += 1
            await_only(stall())
            raise AssertionError("Disconnected analysis must not return late advice")

    model = SlowModel()
    monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", lambda: model)
    server = uvicorn.Server(uvicorn.Config(app, log_level="error",
        loop="sourcepilot.comparison.lifecycle:comparison_loop"))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        worker = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        worker.start()
        try:
            until = time.monotonic() + 5
            while not server.started and worker.is_alive() and time.monotonic() < until:
                time.sleep(0.01)
            assert server.started
            body = json.dumps({"snapshot_id": snapshot["id"]})
            cookie = "; ".join(f"{key}={value}" for key, value in client.cookies.items())
            request = (f"POST /projects/{project_id}/comparison/advice HTTP/1.1\r\n"
                       f"Host: 127.0.0.1:{port}\r\nCookie: {cookie}\r\n"
                       f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n{body}")
            started = time.monotonic()
            with socket.create_connection(("127.0.0.1", port), timeout=5) as browser:
                browser.sendall(request.encode())
                assert entered.wait(5)
                browser.shutdown(socket.SHUT_RDWR)
            assert cancelled.wait(2.75)
            with Session(engine) as session:
                run = None
                while time.monotonic() - started < 2.75:
                    run = session.scalar(select(AIRun).where(AIRun.project_id == UUID(project_id)))
                    if run is not None and run.completed_at is not None:
                        break
                    session.expire_all()
                    time.sleep(0.01)
                assert run is not None and run.status == "TIMED_OUT"
                assert run.completed_at is not None
            assert time.monotonic() - started < 2.75
            assert model.calls == 1
            assert client.get(f"/projects/{project_id}/comparison").json() == snapshot
        finally:
            server.should_exit = True
            worker.join(timeout=5)
            assert not worker.is_alive()
