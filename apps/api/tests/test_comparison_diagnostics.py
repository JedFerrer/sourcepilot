"""Safe diagnostics cannot reveal rejected model values or exception messages."""

import json
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from sourcepilot.ai.client import AnalystModelInvocation, ModelProviderError, ProviderDiagnostics
from sourcepilot.ai.comparison_advice import analyze_comparison_advice
from sourcepilot.ai.tracing import ERRORS, NAMES, safe_label
from sourcepilot.ai.tradeoff_analysis import TradeoffUnavailableError
from sourcepilot.comparison.validation import (
    REPAIR_FEEDBACK,
    ComparisonRejection,
    RejectionCode,
    comparison_repair_feedback,
    rejection_code,
    schema_issue_labels,
)
from sourcepilot.persistence.models import AIRun, Comparison, Project, SupplierExplanationRunStep
from tests.test_ai_tracing import Observation, run_record
from tests.test_comparison_advice import AdviceModel
from tests.test_tradeoff_analysis import (  # noqa: F401
    FakeModel,
    client,
    database_url,
    engine,
    ready,
)

# ruff: noqa: F811 -- shared isolated database fixtures.

SECRET = "private-quote-and-credential-sentinel"


def test_state_syntax_feedback_remains_for_tradeoffs_and_advice_selects_facts() -> None:
    from sourcepilot.ai.comparison_advice import INSTRUCTIONS as advice_instructions
    from sourcepilot.ai.tradeoff_analysis import INSTRUCTIONS as tradeoff_instructions

    feedback = comparison_repair_feedback(ComparisonRejection(RejectionCode.STATE_SYNTAX, SECRET))
    for text in (feedback, tradeoff_instructions):
        for example in ("Supplier A certification is MEETS.",
                        "Supplier A GOTS certification is MEETS.",
                        "Supplier C shipping cost is UNKNOWN."):
            assert example in text
        assert "quote_fields" in text and "requirement_ids" in text
        assert "separate cited points" in text
        assert "ownership" in text and "provenance" in text
        assert SECRET not in text
    assert "Return only ComparisonSelectionV1" in advice_instructions
    assert "Do not write narrative, states, values or evidence IDs" in advice_instructions
    assert SECRET not in advice_instructions


@pytest.mark.parametrize("mutation,code,phase", [
    ("supplier", "SUPPLIER_REFERENCE", "analysis"),
    ("requirement", "REQUIREMENT_REFERENCE", "analysis"),
    ("evidence", "UNKNOWN_EVIDENCE", "analysis"),
    ("score", "PROHIBITED_SCORE", "analysis"),
    ("unknown", "MISSING_UNKNOWN", "analysis"),
    ("required", "MISSING_REQUIRED_FAILURE", "analysis"),
    ("quote_owner", "QUOTE_OWNER_MISMATCH", "analysis"),
    ("state", "STATE_CONTRADICTION", "analysis"),
    ("reasons", "SUGGESTION_REASONS", "suggestion"),
    ("coverage", "SUGGESTION_COVERAGE", "suggestion"),
])
def test_real_validator_rejection_reason_and_phase(mutation, code, phase) -> None:
    from sourcepilot.ai.comparison_advice import ComparisonAdvice, validate_advice
    from sourcepilot.ai.tradeoff_analysis_eval import B, fixture_snapshot
    from tests.test_comparison_advice import suggestion
    from tests.test_tradeoff_analysis import valid_output

    snapshot = fixture_snapshot()
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    assert payload is not None
    advice = ComparisonAdvice.model_validate({
        "analysis": valid_output(payload), "suggestion": suggestion(payload, B),
    })
    validate_advice(advice, snapshot)
    point = advice.analysis.supplier_summaries[0]
    if mutation == "supplier":
        point.supplier_ids = [uuid4()]
    elif mutation == "requirement":
        point.requirement_ids = [uuid4()]
    elif mutation == "evidence":
        point.evidence_ids = [uuid4()]
    elif mutation == "score":
        point.text = "Supplier A has a 95% match score."
    elif mutation == "unknown":
        advice.analysis.important_unknowns.clear()
    elif mutation == "required":
        advice.analysis.supplier_summaries.clear()
        advice.analysis.key_tradeoffs.clear()
    elif mutation == "quote_owner":
        from sourcepilot.comparison.advice import QuoteFieldReference

        point.quote_fields = [QuoteFieldReference(
            quote_id=UUID(payload["suppliers"][1]["quote_id"]), field_key="unit_price")]
    elif mutation == "state":
        unknown = advice.analysis.important_unknowns[0]
        for supplier in payload["suppliers"]:
            if UUID(supplier["supplier_id"]) in unknown.supplier_ids:
                for finding in supplier["evaluation"]["results"]:
                    if finding["requirement_id"] and UUID(finding["requirement_id"]) in unknown.requirement_ids:
                        finding["status"] = "MEETS"
    elif mutation == "reasons":
        advice.suggestion.supporting_reasons.clear()
    else:
        advice.suggestion.tradeoffs.clear()
    with pytest.raises(ComparisonRejection) as failure:
        validate_advice(advice, snapshot)
    assert failure.value.code.value == code and failure.value.phase == phase
    assert SECRET not in comparison_repair_feedback(failure.value)


def test_exported_validation_diagnostics_are_actionable_and_content_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sourcepilot.ai import tracing

    calls = []
    monkeypatch.setattr(tracing, "langfuse_client", lambda: Observation(calls))
    run = run_record()
    run.operation = "comparison_advice"
    run.status = "VALIDATION_FAILED"
    run.error_type = "STATE_CONTRADICTION"
    observation = tracing.RunObservations(run, {})
    observation.step("validation_phase", "INVALID", "analysis_initial", 1)
    observation.step("validation", "INVALID", "STATE_CONTRADICTION", 2)
    observation.step("validation_schema", "INVALID", SECRET, 3)
    observation.record(run)
    serialized = json.dumps(calls)
    assert "STATE_CONTRADICTION" in serialized and "analysis_initial" in serialized
    assert SECRET not in serialized
    assert all("input" not in call and "output" not in call for call in calls)


@pytest.mark.parametrize("code", list(RejectionCode))
def test_reason_feedback_is_fixed_and_allowlisted(code: RejectionCode) -> None:
    error = ComparisonRejection(code, SECRET)
    assert rejection_code(error) == code
    assert safe_label(code.value, ERRORS) == code.value
    assert safe_label(code.value, NAMES) == code.value
    assert SECRET not in comparison_repair_feedback(error)
    assert REPAIR_FEEDBACK[code] in comparison_repair_feedback(error)


def test_unknown_exception_and_mutated_reason_fail_closed() -> None:
    error = ComparisonRejection(RejectionCode.STATE_REFERENCE, SECRET)
    error.code = SECRET  # type: ignore[assignment] - malicious/nonconforming boundary value
    for candidate in (error, ValueError(SECRET)):
        assert rejection_code(candidate) == RejectionCode.UNKNOWN_REJECTION
        assert SECRET not in comparison_repair_feedback(candidate)
    assert safe_label(SECRET, NAMES) == "OTHER"


def test_schema_reason_does_not_export_inputs_context_or_extra_field_names() -> None:
    class Output(BaseModel):
        model_config = ConfigDict(extra="forbid")
        count: int

    with pytest.raises(ValidationError) as raised:
        Output.model_validate({"count": SECRET, SECRET: SECRET})
    assert SECRET in str(raised.value)
    assert rejection_code(raised.value) == RejectionCode.SCHEMA_INVALID
    feedback = comparison_repair_feedback(raised.value)
    assert "schema validation" in feedback
    assert SECRET not in feedback
    assert all(SECRET not in label and safe_label(label, NAMES) == label
               for label in schema_issue_labels(raised.value))


@pytest.mark.parametrize("phase,expected", [
    ("selection", "STATE_REFERENCE"), ("suggestion", "STATE_REFERENCE"),
    ("schema", "SCHEMA_INVALID"),
])
def test_both_rejections_have_safe_reason_and_phase(
    client, engine: Engine, phase: str, expected: str,
) -> None:
    class RejectedModel(AdviceModel):
        def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
            # Repeat a schema or targeted selection failure; public-validator
            # reason/phase coverage remains in the direct validator test above.
            result = super().invoke_with_tools(**kwargs)
            output = json.loads(result.output_text)
            if phase == "selection":
                output["highlights"] = [SECRET]
            elif phase == "suggestion":
                output["suggestion"]["no_suggestion_reason"] = None
            else:
                output[SECRET] = SECRET
            if kwargs["schema_name"] == "SelectionRepairV1":
                output = {"version": "comparison-selection-repair-v1", "snapshot_id": output["snapshot_id"],
                          "replacements": [{"slot_id": "highlights[0]" if phase == "selection" else "suggestion",
                                            "op": "replace", "value": SECRET if phase == "selection" else output["suggestion"]}]}
            return AnalystModelInvocation(json.dumps(output), (), 1, 1)

    project_id, _, _ = ready(client)
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        snapshot = session.scalar(select(Comparison.id).where(Comparison.project_id == project.id))
        assert snapshot is not None
        with pytest.raises(TradeoffUnavailableError):
            analyze_comparison_advice(session, demo_session_id=project.demo_session_id,
                                      project_id=project.id, snapshot_id=snapshot,
                                      client_factory=RejectedModel)
        run = session.scalar(select(AIRun).where(AIRun.project_id == project.id))
        assert run is not None and run.error_type == expected and run.model_turn_count == 2
        steps = session.scalars(select(SupplierExplanationRunStep).where(
            SupplierExplanationRunStep.air_run_id == run.id).order_by(SupplierExplanationRunStep.sequence)).all()
        assert [step.name for step in steps if step.kind == "validation"] == [expected, expected]
        # Internal selection rejections retain ComparisonRejection's existing
        # analysis phase; no new tracing taxonomy is introduced by this amendment.
        diagnostic_phase = "schema" if phase == "schema" else "analysis"
        assert [step.name for step in steps if step.kind == "validation_phase"] == [
            f"{diagnostic_phase}_initial", f"{diagnostic_phase}_repair"]
        assert SECRET not in json.dumps([(step.kind, step.outcome, step.name) for step in steps])


@pytest.mark.parametrize("entrypoint", ["advice", "analysis"])
@pytest.mark.parametrize("scenario", ["reject", "twice", "recover", "unknown"])
def test_provider_diagnostics_preserve_retry_public_errors_and_facts(
    client, engine, monkeypatch, caplog, entrypoint, scenario,
) -> None:
    from sourcepilot.ai import tracing

    exported = []
    monkeypatch.setattr(tracing, "langfuse_client", lambda: Observation(exported))
    project_id, _, _ = ready(client)
    path = f"/projects/{project_id}/comparison"
    before = client.get(path).json()
    model = AdviceModel() if entrypoint == "advice" else FakeModel()
    original = model.invoke_with_tools
    calls = []
    diagnostics = (ProviderDiagnostics() if scenario == "unknown" else
                   ProviderDiagnostics("AUTHENTICATION", "401", "invalid_api_key") if scenario == "reject"
                   else ProviderDiagnostics("SERVER_ERROR", "503", "server_error"))

    def invoke(**kwargs):
        calls.append(True)
        if scenario != "recover" or len(calls) == 1:
            raise ModelProviderError(SECRET, retryable=scenario != "reject", diagnostics=diagnostics)
        return original(**kwargs)

    monkeypatch.setattr(model, "invoke_with_tools", invoke)
    monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", lambda: model)
    response = client.post(path + f"/{entrypoint}", json={"snapshot_id": before["id"]})
    assert response.status_code == (200 if scenario == "recover" else 503)
    assert client.get(path).json() == before
    expected_calls = 1 if scenario == "reject" else 2
    assert len(calls) == expected_calls
    with Session(engine) as session:
        run = session.scalar(select(AIRun).where(AIRun.project_id == UUID(project_id)))
        assert run is not None
        assert run.status == ("COMPLETED" if scenario == "recover" else "PROVIDER_FAILED")
        assert run.attempts == run.model_turn_count == expected_calls
        assert run.tool_call_count == 0
        assert run.error_type == (None if scenario == "recover" else "ModelProviderError")
        rows = session.scalars(select(SupplierExplanationRunStep).where(
            SupplierExplanationRunStep.air_run_id == run.id).order_by(SupplierExplanationRunStep.sequence)).all()
        events = [(row.kind, row.outcome, row.name) for row in rows]
        failed_attempt = [("model", "PROVIDER_ERROR", None),
                          ("provider_category", "DIAGNOSTIC", diagnostics.category),
                          ("provider_status", "DIAGNOSTIC", diagnostics.status),
                          ("provider_code", "DIAGNOSTIC", diagnostics.code),
                          ("timeout_origin", "DIAGNOSTIC", "UNKNOWN"),
                          ("transport_phase", "DIAGNOSTIC", "UNKNOWN"),
                          ("transport_phase_state", "DIAGNOSTIC", "UNKNOWN")]
        assert events[:7] == failed_attempt
        if expected_calls == 2:
            assert events[7] == ("retry", "PROVIDER", None)
            if scenario != "recover":
                assert events[8:15] == failed_attempt
        assert sum(kind == "retry" for kind, _, _ in events) == expected_calls - 1
        usage = "PARTIAL" if scenario == "recover" else "UNAVAILABLE"
        assert events[-3:] == [("usage", usage, "input_tokens"),
                               ("usage", usage, "output_tokens"), ("run", run.status, None)]
        assert (run.input_tokens, run.output_tokens) == ((2, 1) if scenario == "recover" else (None, None))
        assert SECRET not in json.dumps(events) + json.dumps(exported) + response.text + caplog.text


@pytest.mark.parametrize("entrypoint", ["advice", "analysis"])
@pytest.mark.parametrize("failure,status,code,category,attempts", [
    ("http", 401, "invalid_api_key", "AUTHENTICATION", 1),
    ("http", 503, "server_error", "SERVER_ERROR", 2),
    ("http", 418, SECRET, "UNKNOWN", 1),
    ("http", 409, SECRET, "UNKNOWN", 2),
    ("type", None, None, "LOCAL_CLIENT_ERROR", 2),
    ("value", None, None, "LOCAL_CLIENT_ERROR", 2),
    ("connection", None, None, "CONNECTION", 2),
    ("timeout", None, None, "TIMEOUT", 2),
    ("connect_timeout", None, None, "TIMEOUT", 2),
    ("write_timeout", None, None, "TIMEOUT", 2),
    ("pool_timeout", None, None, "TIMEOUT", 2),
    ("sdk_unknown", None, None, "TIMEOUT", 2),
    ("attempt", None, None, "TIMEOUT", 2),
    ("real_connect", None, None, "TIMEOUT", 2),
    ("real_tls", None, None, "TIMEOUT", 2),
    ("real_write_headers", None, None, "TIMEOUT", 2),
    ("real_write_body", None, None, "TIMEOUT", 2),
    ("real_read_headers", None, None, "TIMEOUT", 2),
    ("real_read_body", None, None, "TIMEOUT", 2),
    ("reuse_failure", None, None, "TIMEOUT", 2),
    ("unknown_event", None, None, "TIMEOUT", 2),
    ("unexpected", None, None, "UNKNOWN", 2),
])
def test_sdk_failure_reaches_persisted_and_exported_comparison_trace(
    client, engine, monkeypatch, caplog, entrypoint, failure, status, code, category, attempts,
) -> None:
    import httpx
    from openai import AsyncOpenAI as SDKAsyncOpenAI

    from sourcepilot.ai import tracing
    from sourcepilot.ai.client import prepare_comparison_transport

    # Keep the route's real client factory, adapter, normalization and runtime.
    # Only transport/construction and the optional external sink are replaced.
    prepare_comparison_transport()
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    monkeypatch.setenv("SOURCEPILOT_AI_MODEL", "fixture-model")
    if failure == "attempt":
        monkeypatch.setenv("SOURCEPILOT_ANALYSIS_ATTEMPT_SECONDS", "0.05")
    exported = []
    monkeypatch.setattr(tracing, "langfuse_client", lambda: Observation(exported))
    project_id, _, _ = ready(client)
    path = f"/projects/{project_id}/comparison"
    before = client.get(path).json()
    constructions = []
    requests = []
    transports = []
    sdk_clients = []
    networks = []
    real_phases = {"real_connect": "CONNECT_TCP", "real_tls": "START_TLS",
                   "real_write_headers": "SEND_REQUEST_HEADERS", "real_write_body": "SEND_REQUEST_BODY",
                   "real_read_headers": "RECEIVE_RESPONSE_HEADERS", "real_read_body": "RECEIVE_RESPONSE_BODY"}

    async def handle(request):
        requests.append(request)
        assert request.headers["authorization"] == f"Bearer {SECRET}"
        if failure == "connection":
            raise httpx.ConnectError(SECRET, request=request)
        if failure in {"timeout", "connect_timeout", "write_timeout", "pool_timeout", "sdk_unknown"}:
            kind = {"timeout": httpx.ReadTimeout, "connect_timeout": httpx.ConnectTimeout,
                    "write_timeout": httpx.WriteTimeout, "pool_timeout": httpx.PoolTimeout,
                    "sdk_unknown": httpx.TimeoutException}[failure]
            raise kind(SECRET, request=request)
        if failure == "attempt":
            import asyncio
            await asyncio.sleep(60)
        assert failure == "http"
        return httpx.Response(status, headers={"x-request-id": SECRET}, json={
            "error": {"code": code, "message": SECRET, "param": SECRET, "type": SECRET},
        })

    def make_http(**kwargs):
        constructions.append(True)
        # These fail before any HTTP exchange, at the real adapter boundary.
        if failure == "type":
            raise TypeError(SECRET)
        if failure == "value":
            raise ValueError(SECRET)
        if failure == "unexpected":
            raise RuntimeError(SECRET)
        if failure in {"reuse_failure", "unknown_event"}:
            transport, network = redirect_failure_http(unknown_event=failure == "unknown_event")
            networks.append(network)
        elif failure in real_phases:
            from tests.test_comparison_transport import ScriptedNetwork, real_transport_http
            network = ScriptedNetwork(real_phases[failure])
            networks.append(network)
            transport = real_transport_http(network)
        else:
            transport = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        transports.append(transport)
        return transport

    def make_sdk(**kwargs):
        assert kwargs["max_retries"] == 0
        sdk = SDKAsyncOpenAI(**kwargs)
        sdk_clients.append(sdk)
        return sdk

    monkeypatch.setattr("sourcepilot.ai.client.httpx", SimpleNamespace(AsyncClient=make_http))
    monkeypatch.setattr("sourcepilot.ai.client.AsyncOpenAI", make_sdk)
    response = client.post(path + f"/{entrypoint}", json={"snapshot_id": before["id"]})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == (
        "COMPARISON_ADVICE_UNAVAILABLE" if entrypoint == "advice" else "TRADEOFF_ANALYSIS_UNAVAILABLE")
    assert client.get(path).json() == before
    assert len(constructions) == attempts
    http_attempts = attempts if failure not in {"type", "value", "unexpected"} else 0
    assert len(transports) == len(sdk_clients) == http_attempts
    assert (sum(network.connections for network in networks) if networks else len(requests)) == http_attempts
    assert all(transport.is_closed for transport in transports)
    if failure in {"reuse_failure", "unknown_event"}:
        for network in networks:
            assert network.connections == network.closed == 1
            assert len(network.exchanges) == 2
            assert network.resets == [("UNKNOWN", "UNKNOWN")] * 2
            assert network.completed == [("RECEIVE_RESPONSE_BODY", "COMPLETE")]
            first, reused = network.exchanges
            assert "connection.connect_tcp.complete" in first
            assert "connection.start_tls.complete" in first
            assert not any(event.startswith("connection.") for event in reused)
            assert "http11.receive_response_headers.started" in reused
            assert (SECRET if failure == "unknown_event" else
                    "http11.receive_response_headers.failed") in reused

    with Session(engine) as session:
        run = session.scalars(select(AIRun).where(AIRun.project_id == UUID(project_id))).one()
        assert run.operation == ("comparison_advice" if entrypoint == "advice" else "tradeoff_analysis")
        assert run.status == "PROVIDER_FAILED" and run.error_type == "ModelProviderError"
        assert run.attempts == run.model_turn_count == attempts
        assert run.tool_call_count == 0
        assert run.input_tokens is None and run.output_tokens is None
        rows = session.scalars(select(SupplierExplanationRunStep).where(
            SupplierExplanationRunStep.air_run_id == run.id).order_by(SupplierExplanationRunStep.sequence)).all()
        expected_status = "NO_HTTP_STATUS" if status is None else (
            "OTHER_HTTP" if status == 418 else str(status))
        expected_code = code if code in {"invalid_api_key", "server_error"} else "UNKNOWN"
        origin = {"timeout": "SDK_READ", "connect_timeout": "SDK_CONNECT",
                  "write_timeout": "SDK_WRITE", "pool_timeout": "SDK_POOL",
                  "sdk_unknown": "SDK_UNKNOWN", "attempt": "APP_ATTEMPT",
                  "real_connect": "SDK_CONNECT", "real_tls": "SDK_CONNECT",
                  "real_write_headers": "SDK_WRITE", "real_write_body": "SDK_WRITE",
                  "real_read_headers": "SDK_READ", "real_read_body": "SDK_READ",
                  "reuse_failure": "SDK_READ", "unknown_event": "SDK_READ"}.get(failure, "NOT_APPLICABLE")
        phase = "RECEIVE_RESPONSE_HEADERS" if failure == "reuse_failure" else real_phases.get(failure, "UNKNOWN")
        attempt_events = [
            ("model", "TIMEOUT" if category == "TIMEOUT" else "PROVIDER_ERROR", None),
            ("provider_category", "DIAGNOSTIC", category),
            ("provider_status", "DIAGNOSTIC", expected_status),
            ("provider_code", "DIAGNOSTIC", expected_code),
            ("timeout_origin", "DIAGNOSTIC", origin),
            ("transport_phase", "DIAGNOSTIC", phase),
            ("transport_phase_state", "DIAGNOSTIC", "FAILED" if phase != "UNKNOWN" else "UNKNOWN"),
        ]
        expected = attempt_events + (
            [("retry", "PROVIDER", None)] + attempt_events if attempts == 2 else [])
        expected += [("usage", "UNAVAILABLE", "input_tokens"),
                     ("usage", "UNAVAILABLE", "output_tokens"),
                     ("run", "PROVIDER_FAILED", None)]
        events = [(row.kind, row.outcome, row.name) for row in rows]
        assert events == expected
        assert [row.sequence for row in rows] == list(range(1, len(rows) + 1))
        # Compare actual export observations with the persisted diagnostic and
        # retry steps, including sequence; do not manufacture steps in this test.
        export_steps = [(call["metadata"]["sequence"], call["name"],
                         call["metadata"]["outcome"], call["metadata"]["name"])
                        for call in exported if call.get("name") in {
                            "provider_category", "provider_status", "provider_code", "retry",
                            "timeout_origin", "transport_phase", "transport_phase_state"}]
        assert export_steps == [(row.sequence, row.kind, row.outcome, row.name)
                                for row in rows if row.outcome == "DIAGNOSTIC" or row.kind == "retry"]
        assert SECRET not in json.dumps(events) + json.dumps(exported) + response.text + caplog.text


def redirect_failure_http(*, unknown_event):
    """Real HTTP transport: consume a redirect, reuse its socket, then fail."""
    import httpcore
    import httpx

    from tests.test_comparison_transport import HostileDiagnostic

    network = SimpleNamespace(connections=0, closed=0, exchanges=[], resets=[], completed=[])

    class Stream(httpcore.AsyncMockStream):
        def __init__(self):
            super().__init__([
                ("HTTP/1.1 307 Temporary Redirect\r\nLocation: /next?private=" + SECRET
                 + "\r\nX-Private: " + SECRET + "\r\nContent-Length: "
                 + str(len(SECRET.encode())) + "\r\n\r\n").encode(),
                SECRET.encode(),
            ])
            self.reads = 0

        async def start_tls(self, *args, **kwargs):
            return self

        async def read(self, max_bytes, timeout=None):
            self.reads += 1
            if self.reads == 3:
                raise httpcore.ReadTimeout(SECRET)
            return await super().read(max_bytes, timeout)

        async def aclose(self):
            network.closed += 1
            await super().aclose()

    class Network(httpcore.AsyncNetworkBackend):
        async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
            network.connections += 1
            return Stream()

    class Transport(httpx.AsyncHTTPTransport):
        async def handle_async_request(self, request):
            # The production request hook has already installed the real observer
            # and reset exchange state. Do not set labels or call its helpers.
            callback = request.extensions["trace"]
            observer = callback.__self__
            network.resets.append((observer.phase, observer.state))
            events = []
            network.exchanges.append(events)
            assert request.headers["authorization"] == f"Bearer {SECRET}"

            async def trace(event, info):
                # Simulate an unsupported transport operation at the actual hook
                # delivery seam, after a recognized STARTED event. Keep the real
                # socket error and HTTPX/SDK exception normalization intact.
                if unknown_event and event == "http11.receive_response_headers.failed":
                    event = SECRET
                    info = {"private": HostileDiagnostic(), "content": SECRET}
                events.append(event)
                await callback(event, info)
                if event == "http11.receive_response_body.complete":
                    network.completed.append((observer.phase, observer.state))

            request.extensions["trace"] = trace
            return await super().handle_async_request(request)

    transport = Transport()
    transport._pool = httpcore.AsyncConnectionPool(network_backend=Network())
    return httpx.AsyncClient(transport=transport, follow_redirects=True), network


@pytest.mark.parametrize("entrypoint", ["advice", "analysis"])
@pytest.mark.parametrize("mode", ["work", "sdk_then_work"])
def test_real_transport_work_budget_reaches_persisted_trace(client, engine, monkeypatch, caplog, entrypoint, mode):
    from openai import AsyncOpenAI as SDKAsyncOpenAI

    from sourcepilot.ai import tracing
    from sourcepilot.ai.client import prepare_comparison_transport
    from tests.test_comparison_transport import ScriptedNetwork, real_transport_http
    prepare_comparison_transport()
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    monkeypatch.setenv("SOURCEPILOT_AI_MODEL", "fixture")
    monkeypatch.setenv("NEXT_PUBLIC_SOURCEPILOT_ANALYSIS_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("SOURCEPILOT_ANALYSIS_ATTEMPT_SECONDS", "5")
    monkeypatch.setenv("SOURCEPILOT_ANALYSIS_CLEANUP_SECONDS", "0.5")
    exported = []
    monkeypatch.setattr(tracing, "langfuse_client", lambda: Observation(exported))
    network = ScriptedNetwork("RECEIVE_RESPONSE_HEADERS", "stall" if mode == "work" else "timeout")
    monkeypatch.setattr("sourcepilot.ai.client.httpx", SimpleNamespace(
        AsyncClient=lambda **kwargs: real_transport_http(network)))
    class SDK(SDKAsyncOpenAI):
        async def close(self):
            await super().close()
            if mode == "sdk_then_work":
                from sourcepilot.comparison.deadline import current_deadline
                deadline = current_deadline.get()
                assert deadline is not None
                # Cleanup consumes work budget after the SDK failure was frozen.
                deadline.started = deadline.clock() - 1.6
    def sdk(**kwargs):
        assert kwargs["max_retries"] == 0
        assert 0 < kwargs["timeout"] <= 1.5
        return SDK(**kwargs)
    monkeypatch.setattr("sourcepilot.ai.client.AsyncOpenAI", sdk)
    project_id, _, _ = ready(client)
    path = f"/projects/{project_id}/comparison"
    before = client.get(path).json()
    response = client.post(path + f"/{entrypoint}", json={"snapshot_id": before["id"]})
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "COMPARISON_ANALYSIS_TIMEOUT"
    assert client.get(path).json() == before
    assert network.connections == network.closed == 1
    with Session(engine) as session:
        run = session.scalars(select(AIRun).where(AIRun.project_id == UUID(project_id))).one()
        assert run.status == "TIMED_OUT" and run.error_type == "ComparisonDeadlineError"
        assert run.attempts == run.model_turn_count == 1 and run.tool_call_count == 0
        rows = session.scalars(select(SupplierExplanationRunStep).where(
            SupplierExplanationRunStep.air_run_id == run.id).order_by(SupplierExplanationRunStep.sequence)).all()
        events = [(r.kind, r.outcome, r.name) for r in rows]
        expected = [
            ("model", "ERROR", None),
            ("timeout_origin", "DIAGNOSTIC", "APP_WORK_BUDGET" if mode == "work" else "SDK_READ"),
            ("transport_phase", "DIAGNOSTIC", "RECEIVE_RESPONSE_HEADERS"),
            ("transport_phase_state", "DIAGNOSTIC", "FAILED"),
        ]
        if mode == "sdk_then_work":
            expected += [("timeout_origin", "DIAGNOSTIC", "APP_WORK_BUDGET"),
                         ("transport_phase", "DIAGNOSTIC", "UNKNOWN"),
                         ("transport_phase_state", "DIAGNOSTIC", "UNKNOWN")]
        expected += [
            ("usage", "UNAVAILABLE", "input_tokens"),
            ("usage", "UNAVAILABLE", "output_tokens"), ("run", "TIMED_OUT", None),
        ]
        assert events == expected
        assert [r.sequence for r in rows] == list(range(1, len(rows) + 1))
        exported_diagnostics = [(call["name"], call["metadata"]["name"]) for call in exported
                                if call.get("name") in {"timeout_origin", "transport_phase", "transport_phase_state"}]
        assert exported_diagnostics == [(r.kind, r.name) for r in rows if r.outcome == "DIAGNOSTIC"]
        assert SECRET not in json.dumps(events) + json.dumps(exported) + caplog.text + response.text
