"""Metadata-only optional tracing, exercised without a provider or tracing service."""

from __future__ import annotations

import builtins
import json
import logging
import threading
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

from sourcepilot.ai import tracing
from sourcepilot.ai.client import ProviderDiagnostics, comparison_provider_diagnostics
from sourcepilot.persistence.models import AIRun


@pytest.fixture(autouse=True)
def isolated_tracing(monkeypatch: pytest.MonkeyPatch):
    # Existing Alembic fixtures disable pre-existing loggers when configuring logging.
    monkeypatch.setattr(tracing.logger, "disabled", False)
    monkeypatch.delenv("SOURCEPILOT_LANGFUSE_ENABLED", raising=False)
    monkeypatch.setattr(tracing, "_client", None)
    monkeypatch.setattr(tracing, "_provider", None)
    monkeypatch.setattr(tracing, "_initialized", False)
    yield
    tracing.shutdown_tracing()


def run_record() -> AIRun:
    return AIRun(
        id=uuid4(), demo_session_id=uuid4(), project_id=uuid4(), operation="brief_interpreter",
        model="fixture-model", prompt_version="fixture-v1", input_hash="not-exported",
        status="COMPLETED", attempts=2, input_tokens=3, output_tokens=1,
        started_at=datetime.now(UTC), completed_at=datetime.now(UTC), latency_ms=10,
        validation_status="REPAIRED", error_type=None,
    )


class Observation:
    def __init__(self, calls: list[dict[str, Any]], **kwargs: Any):
        self.calls = calls
        self.calls.append(kwargs)
        self.ended = False

    def start_observation(self, **kwargs: Any) -> Observation:
        return Observation(self.calls, **kwargs)

    def update(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)

    def end(self) -> None:
        self.ended = True


def test_disabled_never_imports_sdk_or_constructs_client(monkeypatch: pytest.MonkeyPatch) -> None:
    original = builtins.__import__

    def guarded(name: str, *args: Any, **kwargs: Any) -> Any:
        assert not name.startswith(("langfuse", "opentelemetry"))
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.setattr(tracing.importlib, "import_module", lambda _: pytest.fail("Optional import"))
    observation = tracing.RunObservations(run_record(), {})
    observation.begin("model")
    observation.record(run_record())
    assert tracing.langfuse_client() is None


@pytest.mark.parametrize("failure", ["config", "import", "init"])
def test_unavailable_sdk_is_noop_with_safe_diagnostic(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, failure: str,
) -> None:
    monkeypatch.setenv("SOURCEPILOT_LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-fixture")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sensitive-secret")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://fixture.invalid")
    if failure == "config":
        monkeypatch.delenv("LANGFUSE_SECRET_KEY")
    else:
        def broken(*args: Any, **kwargs: Any) -> Any:
            raise ImportError("sensitive-secret") if failure == "import" else RuntimeError("sensitive-secret")

        if failure == "import":
            monkeypatch.setattr(tracing.importlib, "import_module", broken)
        else:
            monkeypatch.setattr(tracing.importlib, "import_module", lambda _: SimpleNamespace(
                Langfuse=broken, Resource=lambda _: None, TracerProvider=lambda **_: None,
            ))
    assert tracing.langfuse_client() is None
    assert tracing.langfuse_client() is None
    assert "sensitive-secret" not in caplog.text
    assert caplog.text.count("Optional AI tracing unavailable") == 1


def test_export_allows_only_metadata_and_safe_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(tracing, "langfuse_client", lambda: Observation(calls))
    run = run_record()
    run.error_type = "secret-exception"
    observation = tracing.RunObservations(run, {"max_model_turns": 4, "max_tool_calls": 6})
    observation.begin("model")
    observation.usage(3, None)
    observation.step("model", "FINAL", None, 1)
    observation.begin("tool", "secret-tool-name")
    observation.step("tool", "secret-tool-error", "secret-tool-name", 2)
    observation.step("retry", "REPAIR", None, 3)
    observation.record(run)
    serialized = json.dumps(calls)
    assert "secret-" not in serialized
    assert str(run.demo_session_id) not in serialized
    assert str(run.project_id) not in serialized
    assert run.input_hash not in serialized
    assert all("input" not in call and "output" not in call for call in calls)
    assert [call["usage_details"] for call in calls if "usage_details" in call] == [{"input": 3}]
    assert any(call.get("trace_context") == {"trace_id": run.id.hex} for call in calls)
    assert observation.root is None


@pytest.mark.parametrize("method", ["start_observation", "update", "end"])
def test_sdk_errors_never_escape(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, method: str,
) -> None:
    def broken(*args: Any, **kwargs: Any) -> Any:
        raise TimeoutError("secret response body")

    monkeypatch.setattr(Observation, method, broken)
    monkeypatch.setattr(tracing, "langfuse_client", lambda: Observation([]))
    observation = tracing.RunObservations(run_record(), {})
    observation.begin("model")
    observation.usage(1, 1)
    observation.step("model", "FINAL", None, 1)
    observation.record(run_record())
    assert "secret response body" not in caplog.text


def test_shutdown_failure_is_safe_and_idempotent(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    def broken() -> None:
        raise RuntimeError("secret shutdown error")

    monkeypatch.setattr(tracing, "_client", SimpleNamespace(shutdown=broken))
    tracing.shutdown_tracing()
    tracing.shutdown_tracing()
    assert "secret shutdown error" not in caplog.text


def test_real_optional_sdk_manual_observations_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    sdk = pytest.importorskip("langfuse")
    exporter_module = pytest.importorskip("opentelemetry.sdk.trace.export.in_memory_span_exporter")
    exporter = exporter_module.InMemorySpanExporter()
    def no_network(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("Tracing fixture attempted a network request")

    monkeypatch.setattr("httpx.Client.send", no_network)
    monkeypatch.setattr("requests.Session.send", no_network)
    real_import = tracing.importlib.import_module
    captured: dict[str, Any] = {}

    def client_factory(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return sdk.Langfuse(**kwargs, span_exporter=exporter)

    def modules(name: str) -> Any:
        return SimpleNamespace(Langfuse=client_factory) if name == "langfuse" else real_import(name)

    monkeypatch.setattr(tracing.importlib, "import_module", modules)
    monkeypatch.setenv("SOURCEPILOT_LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-" + uuid4().hex)
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-fixture")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://fixture.invalid")
    run = run_record()
    observation = tracing.RunObservations(run, {})
    observation.begin("model")
    observation.usage(3, 1)
    observation.step("model", "FINAL", None, 1)
    observation.step("retry", "REPAIR", None, 2)
    observation.record(run)
    tracing.shutdown_tracing()
    spans = exporter.get_finished_spans()
    assert len(spans) == 3
    assert {span.context.trace_id for span in spans} == {run.id.int}
    assert captured["timeout"] == 2 and captured["debug"] is False
    assert all("langfuse.observation.input" not in span.attributes for span in spans)
    assert all("langfuse.observation.output" not in span.attributes for span in spans)
    assert [span.name for span in spans] == ["model", "retry", "brief_interpreter"]


def test_sdk_diagnostics_drop_sensitive_messages_and_tracebacks() -> None:
    record = logging.LogRecord(
        "langfuse", 40, "fixture", 1, "secret %s", ("credential",), None,
    )
    record.exc_text = "secret traceback"
    assert tracing._SDKDiagnosticFilter().filter(record)
    assert "secret" not in record.getMessage()
    assert record.exc_text is None and record.args == ()


def test_shutdown_does_not_wait_indefinitely(monkeypatch: pytest.MonkeyPatch) -> None:
    released, entered = threading.Event(), threading.Event()

    def blocked() -> None:
        entered.set()
        released.wait(timeout=2)

    monkeypatch.setattr(tracing, "_client", SimpleNamespace(shutdown=blocked))
    monkeypatch.setattr(tracing, "SHUTDOWN_TIMEOUT_SECONDS", 0.01)
    try:
        tracing.shutdown_tracing()
        assert entered.is_set() and not released.is_set()
    finally:
        released.set()


@pytest.mark.parametrize("export", ["disabled", "enabled", "broken"])
@pytest.mark.parametrize("known", [True, False])
def test_provider_diagnostics_persist_and_export_only_allowlisted_labels(monkeypatch, caplog, export, known):
    import httpx
    from openai import APIStatusError

    calls = []
    rows = []
    request = httpx.Request("POST", "https://fixture.invalid/private-url",
                           headers={"Authorization": "private-credential"}, content="private-quote")
    error = APIStatusError("private-message", response=httpx.Response(
        401, request=request, headers={"x-request-id": "private-header"}),
        body={"code": "invalid_api_key" if known else "private-code", "message": "private-body"})
    diagnostics = comparison_provider_diagnostics(error)
    assert diagnostics == ProviderDiagnostics("AUTHENTICATION", "401", "invalid_api_key" if known else "UNKNOWN")
    if export == "enabled":
        monkeypatch.setattr(tracing, "langfuse_client", lambda: Observation(calls))
    elif export == "broken":
        class BrokenObservation(Observation):
            def start_observation(self, **kwargs):
                raise RuntimeError("private-export-message")
        monkeypatch.setattr(tracing, "langfuse_client", lambda: BrokenObservation(calls))
    session = SimpleNamespace(add=rows.append, commit=lambda: None)
    run = run_record()
    run.operation = "comparison_advice"
    trace = tracing.RunTrace(session, run)  # type: ignore[arg-type]
    for name in ("category", "status", "code"):
        trace.step(f"provider_{name}", "DIAGNOSTIC", getattr(diagnostics, name))
    assert [(row.sequence, row.kind, row.outcome, row.name) for row in rows] == [
        (1, "provider_category", "DIAGNOSTIC", "AUTHENTICATION"),
        (2, "provider_status", "DIAGNOSTIC", "401"),
        (3, "provider_code", "DIAGNOSTIC", "invalid_api_key" if known else "UNKNOWN"),
    ]
    if export == "enabled":
        assert [(call["name"], call["metadata"]["name"]) for call in calls[2:]] == [
            (row.kind, row.name) for row in rows]
    payload = json.dumps(calls) + json.dumps([(r.kind, r.outcome, r.name) for r in rows]) + caplog.text
    assert "private-" not in payload


@pytest.mark.parametrize("broken", [False, True])
@pytest.mark.parametrize("known", [False, True])
def test_timeout_metadata_joins_existing_commit_with_safe_export(monkeypatch, caplog, broken, known):
    from sourcepilot.comparison.deadline import TimeoutDiagnostics
    from tests.test_comparison_transport import HostileDiagnostic
    calls, rows, commits = [], [], []
    class Export(Observation):
        def start_observation(self, **kwargs):
            if broken:
                raise RuntimeError("private-export")
            return super().start_observation(**kwargs)
    monkeypatch.setattr(tracing, "langfuse_client", lambda: Export(calls))
    session = SimpleNamespace(add=rows.append, commit=lambda: commits.append(True))
    trace = tracing.RunTrace(cast(Any, session), run_record())
    diagnostic = (TimeoutDiagnostics("SDK_READ", "RECEIVE_RESPONSE_BODY", "FAILED") if known else
                  TimeoutDiagnostics(*[cast(Any, HostileDiagnostic()) for _ in range(3)]))
    trace.timeout_diagnostics(diagnostic)
    assert not rows and not commits
    trace.step("retry", "PROVIDER")
    assert len(commits) == 1
    assert [(row.sequence, row.kind, row.name) for row in rows] == [
        (1, "timeout_origin", "SDK_READ" if known else "UNKNOWN"),
        (2, "transport_phase", "RECEIVE_RESPONSE_BODY" if known else "UNKNOWN"),
        (3, "transport_phase_state", "FAILED" if known else "UNKNOWN"),
        (4, "retry", None),
    ]
    if not broken:
        assert [(call["name"], call["metadata"]["name"]) for call in calls[2:]] == [
            (row.kind, row.name) for row in rows]
    assert "private-" not in json.dumps(calls) + caplog.text
