"""Application-owned run steps and optional, metadata-only Langfuse observations."""

from __future__ import annotations

import atexit
import importlib
import logging
import os
import threading
import time
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from sourcepilot.ai.client import PROVIDER_CATEGORIES, PROVIDER_CODES, PROVIDER_STATUSES
from sourcepilot.comparison.deadline import (
    TIMEOUT_ORIGINS,
    TRANSPORT_PHASES,
    TRANSPORT_STATES,
    TimeoutDiagnostics,
)
from sourcepilot.comparison.validation import SCHEMA_LABELS, RejectionCode
from sourcepilot.persistence.models import AIRun, SupplierExplanationRunStep

logger = logging.getLogger(__name__)
OPERATIONS = frozenset({
    "brief_interpreter", "clarification_generator", "quote_extractor",
    "supplier_explanation", "tradeoff_analysis", "comparison_advice", "foundation_smoke",
})
TOOLS = frozenset({
    "get_supplier_snapshot", "get_supplier_evidence", "get_comparison_snapshot",
    "get_quote_evidence",
})
OUTCOMES = frozenset({
    "RUNNING", "COMPLETED", "FAILED", "PROVIDER_FAILED", "VALIDATION_FAILED",
    "FAILED_LIMIT_REACHED", "PROVIDER_ERROR", "TIMEOUT", "FINAL", "TOOL_CALLS",
    "SUCCESS", "INVALID", "VALID", "REPAIRED", "PROVIDER", "REPAIR", "REACHED",
    "CHANGED", "CURRENT", "LIMIT_REACHED", "NOT_FOUND", "NOT_ALLOWED", "OUT_OF_SCOPE",
    "COMPLETE", "PARTIAL", "UNAVAILABLE", "ERROR", "TIMED_OUT",
})
OUTCOMES = OUTCOMES | {"DIAGNOSTIC"}
ERRORS = frozenset({
    "ModelProviderError", "ValidationError", "ValueError", "TimeoutError",
    "SCOPE_CHANGED", "STALE_COMPARISON", "COMPARISON_STALE", "StalePdfAttemptError",
    "NOT_FOUND", "NOT_ALLOWED", "OUT_OF_SCOPE", "LIMIT_REACHED", "INVALID_ARGUMENTS", "INTERRUPTED",
})
ERRORS = ERRORS | {"ComparisonDeadlineError"} | frozenset(code.value for code in RejectionCode)
NAMES = TOOLS | SCHEMA_LABELS | {"model_turns", "tool_calls", "input_tokens", "output_tokens"} | frozenset(
    code.value for code in RejectionCode
) | frozenset(f"{phase}_{attempt}" for phase in ("analysis", "suggestion", "schema", "unknown")
              for attempt in ("initial", "repair"))
NAMES = NAMES | PROVIDER_CATEGORIES | PROVIDER_STATUSES | PROVIDER_CODES
NAMES = NAMES | TIMEOUT_ORIGINS | TRANSPORT_PHASES | TRANSPORT_STATES


def safe_label(value: str | None, allowed: frozenset[str]) -> str | None:
    return value if value is None or value in allowed else "OTHER"


def provider_failure_outcome(error: Exception) -> str:
    # The normalized provider error retains the SDK cause, never its message.
    cause = error.__cause__
    return "TIMEOUT" if isinstance(cause, TimeoutError) or (
        cause is not None and type(cause).__name__ == "APITimeoutError"
    ) else "PROVIDER_ERROR"


class AIRunTracer(Protocol):
    def record(self, air_run: AIRun) -> None: ...


class NoOpAIRunTracer:
    def record(self, air_run: AIRun) -> None:
        return None


def _diagnostic() -> None:
    # Do not include SDK exceptions: they can contain headers, URLs or payloads.
    logger.warning("Optional AI tracing unavailable; application run records remain authoritative.")


_client: Any = None
_provider: Any = None
_initialized = False
_lock = threading.Lock()
SHUTDOWN_TIMEOUT_SECONDS = 3


class _SDKDiagnosticFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # SDK/exporter diagnostics may otherwise echo remote bodies or credentials.
        record.msg = "Optional AI tracing SDK diagnostic; inspect application-owned run records."
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True


def langfuse_client() -> Any:
    global _client, _provider, _initialized
    if os.environ.get("SOURCEPILOT_LANGFUSE_ENABLED", "false").lower() != "true":
        return None
    with _lock:
        if _initialized:
            return _client
        _initialized = True
        try:
            public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
            secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
            base_url = os.environ.get("LANGFUSE_BASE_URL", "")
            url = urlsplit(base_url)
            if not public_key or not secret_key or url.scheme != "https" or not url.hostname:
                raise ValueError("Missing tracing configuration.")
            if url.username or url.password or url.query or url.fragment:
                raise ValueError("Invalid tracing endpoint.")
            # Optional imports occur only after explicit enablement/configuration.
            Langfuse = importlib.import_module("langfuse").Langfuse
            Resource = importlib.import_module("opentelemetry.sdk.resources").Resource
            TracerProvider = importlib.import_module("opentelemetry.sdk.trace").TracerProvider

            for name in ("langfuse", "opentelemetry.exporter.otlp.proto.http.trace_exporter",
                         "opentelemetry.sdk._shared_internal"):
                sdk_logger = logging.getLogger(name)
                if not any(isinstance(f, _SDKDiagnosticFilter) for f in sdk_logger.filters):
                    sdk_logger.addFilter(_SDKDiagnosticFilter())

            # Isolate the SDK from unrelated instrumentation and resource detectors.
            provider = TracerProvider(
                resource=Resource({"service.name": "sourcepilot"}), shutdown_on_exit=False,
            )
            _provider = provider
            _client = Langfuse(
                public_key=public_key, secret_key=secret_key, base_url=base_url,
                timeout=2, debug=False, flush_at=32, flush_interval=5,
                tracer_provider=provider,
                should_export_span=lambda span: bool(
                    span.attributes and span.attributes.get("langfuse.observation.metadata.sourcepilot")
                ),
            )
            atexit.register(shutdown_tracing)
        except Exception:  # noqa: BLE001 - optional telemetry must not affect business behavior
            _diagnostic()
        return _client


def shutdown_tracing() -> None:
    global _client, _provider, _initialized
    with _lock:
        client, _client = _client, None
        provider, _provider = _provider, None
        _initialized = False
    if client is None and provider is None:
        return

    def close() -> None:
        try:
            if client is not None:
                client.shutdown()
        except Exception:  # noqa: BLE001 - optional telemetry must not affect business behavior
            _diagnostic()
        finally:
            if provider is not None:
                try:
                    provider.shutdown()
                except Exception:  # noqa: BLE001 - optional telemetry must not affect shutdown
                    _diagnostic()

    try:
        worker = threading.Thread(target=close, name="sourcepilot-tracing-shutdown", daemon=True)
        worker.start()
        worker.join(timeout=SHUTDOWN_TIMEOUT_SECONDS)
        if worker.is_alive():
            _diagnostic()
    except Exception:  # noqa: BLE001 - optional telemetry must not affect shutdown
        _diagnostic()


class RunObservations:
    """One manual root and at most one active model/tool child; no captured I/O."""

    def __init__(self, run: AIRun, limits: dict[str, int]) -> None:
        self.root: Any = None
        self.child: Any = None
        self.child_kind: str | None = None
        self.model = run.model  # Application configuration, never model output.
        try:
            client = langfuse_client()
            if client is not None:
                self.root = client.start_observation(
                    name=safe_label(run.operation, OPERATIONS), as_type="span",
                    trace_context={"trace_id": run.id.hex},
                    metadata={"sourcepilot": True, "run_id": str(run.id),
                              "operation": safe_label(run.operation, OPERATIONS),
                              "prompt_version": run.prompt_version, "model": run.model,
                              **limits},
                )
        except Exception:  # noqa: BLE001 - optional telemetry must not affect business behavior
            _diagnostic()

    def begin(self, kind: str, name: str | None = None) -> None:
        if self.root is None:
            return
        try:
            self._close_child("ERROR")
            self.child_kind = kind
            self.child = self.root.start_observation(
                name=(safe_label(name, TOOLS) or "OTHER") if kind == "tool" else "model",
                as_type="tool" if kind == "tool" else "generation",
                metadata={"sourcepilot": True},
                **({"model": self.model} if kind == "model" else {}),
            )
        except Exception:  # noqa: BLE001 - optional telemetry must not affect business behavior
            _diagnostic()

    def usage(self, input_tokens: int | None, output_tokens: int | None) -> None:
        if self.child is None or self.child_kind != "model":
            return
        try:
            usage = {key: value for key, value in {
                "input": input_tokens, "output": output_tokens,
            }.items() if value is not None}
            if usage:
                self.child.update(usage_details=usage)
        except Exception:  # noqa: BLE001 - optional telemetry must not affect business behavior
            _diagnostic()

    def _close_child(self, outcome: str, sequence: int | None = None) -> None:
        child, self.child = self.child, None
        self.child_kind = None
        if child is not None:
            try:
                child.update(metadata={"sourcepilot": True, "outcome": outcome,
                                       "sequence": sequence})
            finally:
                child.end()

    def step(self, kind: str, outcome: str, name: str | None, sequence: int) -> None:
        if self.root is None:
            return
        try:
            safe_outcome = safe_label(outcome, OUTCOMES) or "OTHER"
            if self.child is not None and self.child_kind == kind:
                self._close_child(safe_outcome, sequence)
            else:
                observation = self.root.start_observation(
                    name=kind if kind in {"model", "tool", "retry", "validation", "scope",
                                         "limit", "run", "usage", "provider_category",
                                         "provider_status", "provider_code", "timeout_origin",
                                         "transport_phase", "transport_phase_state"} else "OTHER",
                    as_type="span", metadata={
                        "sourcepilot": True, "outcome": safe_outcome,
                        "name": safe_label(name, NAMES), "sequence": sequence,
                    },
                )
                observation.end()
        except Exception:  # noqa: BLE001 - optional telemetry must not affect business behavior
            _diagnostic()

    def record(self, run: AIRun, *, persisted: bool = True) -> None:
        if self.root is None:
            return
        try:
            self._close_child("ERROR")
            self.root.update(metadata={
                "sourcepilot": True, "status": safe_label(run.status, OUTCOMES) if persisted else "PERSISTENCE_FAILED",
                "validation_status": safe_label(run.validation_status, OUTCOMES),
                "error_type": safe_label(run.error_type, ERRORS),
                "attempts": run.attempts, "latency_ms": run.latency_ms,
                "started_at": run.started_at.isoformat(),
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "model_turn_count": run.model_turn_count, "tool_call_count": run.tool_call_count,
                "input_tokens": run.input_tokens, "output_tokens": run.output_tokens,
                "estimated_cost": str(run.estimated_cost) if run.estimated_cost is not None else None,
            })
        except Exception:  # noqa: BLE001 - optional telemetry must not affect business behavior
            _diagnostic()
        finally:
            try:
                self.root.end()
            except Exception:  # noqa: BLE001 - optional telemetry must not affect business behavior
                _diagnostic()
            self.root = None


class RunTrace:
    """Record the existing minimal ordered steps, usage availability and terminal run."""

    def __init__(
        self, session: Session, run: AIRun, *, tracer: AIRunTracer | None = None,
        max_model_turns: int | None = None, max_tool_calls: int | None = None,
    ) -> None:
        self.session, self.run = session, run
        self.started = time.monotonic()
        self.sequence = 0
        self.active_kind: str | None = None
        self.pending_diagnostics: list[tuple[str, str, str | None]] = []
        self.reported = {"input_tokens": 0, "output_tokens": 0}
        self.tracer = tracer
        self.observations = RunObservations(run, {
            key: value for key, value in {
                "max_model_turns": max_model_turns, "max_tool_calls": max_tool_calls,
            }.items() if value is not None
        })

    def step(self, kind: str, outcome: str, name: str | None = None) -> None:
        events, self.pending_diagnostics = self.pending_diagnostics, []
        events.append((kind, outcome, safe_label(name, NAMES)))
        for event_kind, event_outcome, event_name in events:
            self.sequence += 1
            self.session.add(SupplierExplanationRunStep(
                air_run_id=self.run.id, sequence=self.sequence, kind=event_kind,
                outcome=event_outcome, name=event_name,
            ))
        self.session.commit()
        if kind == self.active_kind:
            self.active_kind = None
        for offset, (event_kind, event_outcome, event_name) in enumerate(events):
            self.observations.step(event_kind, event_outcome, event_name,
                                   self.sequence - len(events) + offset + 1)

    def timeout_diagnostics(self, diagnostics: TimeoutDiagnostics) -> None:
        # Join the next existing commit; no additional I/O or budget for observation.
        try:
            safe = TimeoutDiagnostics(diagnostics.timeout_origin, diagnostics.transport_phase,
                                      diagnostics.transport_phase_state)
            self.pending_diagnostics.extend((kind, "DIAGNOSTIC", getattr(safe, kind)) for kind in (
                "timeout_origin", "transport_phase", "transport_phase_state",
            ))
        except Exception:  # noqa: BLE001, S110 - optional observation cannot replace the failure
            pass

    def begin(self, kind: str, name: str | None = None) -> None:
        self.active_kind = kind
        self.observations.begin(kind, name)

    def usage(self, input_tokens: int | None, output_tokens: int | None) -> None:
        for key, value in {"input_tokens": input_tokens, "output_tokens": output_tokens}.items():
            if value is not None:
                setattr(self.run, key, (getattr(self.run, key) or 0) + value)
                self.reported[key] += 1
        self.observations.usage(input_tokens, output_tokens)

    def finish(self) -> None:
        if self.run.status == "RUNNING":
            # Cancellation/SystemExit still propagate, but cannot leave a completed path RUNNING.
            self.run.status = "FAILED"
            self.run.error_type = "INTERRUPTED"
        self.run.latency_ms = int((time.monotonic() - self.started) * 1000)
        self.run.completed_at = datetime.now(UTC)
        events: list[tuple[str, str, str | None]] = []
        if self.active_kind is not None:
            events.append((self.active_kind, "ERROR", None))
        events.extend(self.pending_diagnostics)
        self.pending_diagnostics = []
        for key, reported in self.reported.items():
            outcome = "UNAVAILABLE" if reported == 0 else (
                "COMPLETE" if reported == self.run.attempts else "PARTIAL"
            )
            events.append(("usage", outcome, key))
        events.append(("run", self.run.status, None))
        persisted = False
        try:
            for offset, (kind, outcome, name) in enumerate(events, 1):
                self.session.add(SupplierExplanationRunStep(
                    air_run_id=self.run.id, sequence=self.sequence + offset,
                    kind=kind, outcome=outcome, name=name,
                ))
            self.session.commit()
            persisted = True
            for offset, (kind, outcome, name) in enumerate(events, 1):
                self.observations.step(kind, outcome, name, self.sequence + offset)
        finally:
            self.observations.record(self.run, persisted=persisted)
        if self.tracer is not None:
            try:
                self.tracer.record(self.run)
            except Exception:  # noqa: BLE001 - optional telemetry must not affect business behavior
                _diagnostic()
