"""Exercise the installed SDK with an in-process transport; no provider access."""

import asyncio
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError
from openai import AsyncOpenAI as SDKAsyncOpenAI
from openai.resources.responses import AsyncResponses

from sourcepilot.ai.client import (
    PROVIDER_CODES,
    AISettings,
    ModelProviderError,
    OpenAIResponsesClient,
    ProviderDiagnostics,
    comparison_provider_diagnostics,
    prepare_comparison_transport,
)
from sourcepilot.comparison.deadline import (
    ComparisonDeadline,
    ComparisonDeadlineError,
    ComparisonTimeouts,
    current_deadline,
)


@pytest.mark.parametrize("phase", ["headers", "body"])
def test_sdk_attempt_cancels_transport_and_never_retries(
    monkeypatch: pytest.MonkeyPatch, phase: str,
) -> None:
    requests = []
    cancelled = []
    closed = []
    clients = []
    sdk_clients = []

    class TricklingBody(httpx.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            try:
                while True:
                    yield b" "
                    await asyncio.sleep(0.001)
            finally:
                cancelled.append("body")

        async def aclose(self) -> None:
            closed.append(True)

    async def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if phase == "headers":
            try:
                await asyncio.sleep(60)
            finally:
                cancelled.append("headers")
        return httpx.Response(200, headers={"content-type": "application/json"},
                              stream=TricklingBody())

    def sdk_factory(**kwargs: object) -> SDKAsyncOpenAI:
        assert kwargs["max_retries"] == 0
        assert 0 < kwargs["timeout"] <= 0.05  # type: ignore[operator]
        assert kwargs["http_client"] is clients[0]
        return sdk_clients[0]

    monkeypatch.setattr("sourcepilot.ai.client.AsyncOpenAI", sdk_factory)
    # Production startup owns cold TLS/header/resource preparation. A request
    # must reuse it rather than silently repeating potentially blocking probing.
    tls, _ = prepare_comparison_transport()

    def unexpected_platform_probe():
        raise AssertionError("Cold platform probe reached comparison request")

    monkeypatch.setattr("openai._base_client.get_platform", unexpected_platform_probe)

    async def exercise() -> None:
        # This test isolates cancellation after transport entry. Prepare its
        # in-process SDK/HTTP fixture before starting the unchanged clock; do
        # not construct and discard a second, untracked HTTP client. Request-time
        # construction consuming the total is verified separately below.
        http = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        clients.append(http)
        sdk = SDKAsyncOpenAI(api_key="synthetic-test-key", max_retries=0,
                            timeout=0.05, http_client=http)
        sdk_clients.append(sdk)

        def prepared_http(*, verify):
            assert verify is tls
            return http

        # Patch only the application module's reference, not httpx globally.
        monkeypatch.setattr("sourcepilot.ai.client.httpx", SimpleNamespace(AsyncClient=prepared_http))
        deadline = ComparisonDeadline(ComparisonTimeouts(total=1, attempt=0.05, cleanup=0.1))
        token = current_deadline.set(deadline)
        try:
            client = OpenAIResponsesClient(AISettings("synthetic-test-key", "fixture-model"))
            with pytest.raises(ModelProviderError) as failure:
                await client._invoke_comparison(instructions="fixture", input_items=[], tools=[],
                                                schema_name="fixture", schema={})
            assert isinstance(failure.value.__cause__, TimeoutError)
            assert failure.value.diagnostics == ProviderDiagnostics(category="TIMEOUT")
            assert len(requests) == 1
            assert cancelled == [phase]
            if phase == "body":
                assert closed
            assert len(clients) == 1
            assert all(client.is_closed for client in clients)
            assert len(asyncio.all_tasks()) == 1
        finally:
            current_deadline.reset(token)
            await sdk.close()

    asyncio.run(exercise())


def test_request_time_construction_exhaustion_rejects_before_transport(monkeypatch) -> None:
    prepare_comparison_transport()
    requests = []

    async def exercise():
        http = httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: requests.append(request) or httpx.Response(500)))
        sdk = SDKAsyncOpenAI(api_key="synthetic", max_retries=0, http_client=http)
        monkeypatch.setattr("sourcepilot.ai.client.httpx", SimpleNamespace(
            AsyncClient=lambda **kwargs: http))
        deadline = ComparisonDeadline(ComparisonTimeouts(total=1, attempt=0.05, cleanup=0.1))

        def delayed_construction(**kwargs):
            assert kwargs["http_client"] is http
            # Deterministically reproduce time spent in request-owned construction.
            # Do not reset the origin or increase any production/test allowance.
            deadline.started -= 2
            return sdk

        monkeypatch.setattr("sourcepilot.ai.client.AsyncOpenAI", delayed_construction)
        token = current_deadline.set(deadline)
        try:
            client = OpenAIResponsesClient(AISettings("synthetic", "fixture"))
            with pytest.raises(ComparisonDeadlineError):
                await client._invoke_comparison(instructions="fixture", input_items=[], tools=[],
                                                schema_name="fixture", schema={})
            assert not requests
            assert http.is_closed
        finally:
            current_deadline.reset(token)
            await sdk.close()

    asyncio.run(exercise())


def test_external_cancellation_is_not_masked_by_failed_provider_close(monkeypatch, caplog) -> None:
    from sourcepilot.comparison import execution
    from sourcepilot.comparison.lifecycle import ComparisonLifecycle, comparison_loop, current_owner

    # Prior database fixture teardown runs Alembic fileConfig, which disables
    # pre-existing loggers. Restore capture for this standalone transport test.
    monkeypatch.setattr(execution.logger, "disabled", False)
    caplog.set_level("WARNING", logger="sourcepilot.comparison.execution")
    prepare_comparison_transport()

    async def handle(request):
        task = asyncio.current_task()
        assert task is not None
        asyncio.get_running_loop().call_soon(task.cancel)
        await asyncio.sleep(60)
        raise AssertionError("Cancelled request cannot finish")

    class FailedCloseClient(SDKAsyncOpenAI):
        async def close(self):
            await super().close()
            raise RuntimeError("sensitive-close-sentinel")

    def factory(**kwargs):
        return FailedCloseClient(api_key="synthetic", max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)))

    monkeypatch.setattr("sourcepilot.ai.client.AsyncOpenAI", factory)

    async def exercise():
        runtime = ComparisonLifecycle(1)
        owner = runtime.acquire()
        owner_token = current_owner.set(owner)
        token = current_deadline.set(ComparisonDeadline())
        try:
            client = OpenAIResponsesClient(AISettings("synthetic", "fixture"))
            with pytest.raises(asyncio.CancelledError):
                await client._invoke_comparison(instructions="fixture", input_items=[], tools=[],
                                                schema_name="fixture", schema={})
            owner.finished = True
            owner.release_if_finished()
            assert runtime.owners == {owner} and owner.resources
            assert len(asyncio.all_tasks()) == 1
        finally:
            current_deadline.reset(token)
            current_owner.reset(owner_token)

    with asyncio.Runner(loop_factory=comparison_loop) as runner:
        runner.run(exercise())
    assert "cleanup incomplete: provider" in caplog.text
    assert "sensitive-close-sentinel" not in caplog.text


@pytest.mark.parametrize("status,code,category,retryable", [
    (400, "invalid_json_schema", "INVALID_REQUEST", False),
    (401, "invalid_api_key", "AUTHENTICATION", False),
    (403, "permission_denied", "PERMISSION", False),
    (404, "model_not_found", "NOT_FOUND", False),
    (408, None, "TIMEOUT", True),
    (409, None, "UNKNOWN", True),
    (422, "invalid_value", "INVALID_REQUEST", False),
    (429, "rate_limit_exceeded", "RATE_LIMIT", True),
    (429, "insufficient_quota", "RATE_LIMIT", True),
    (500, "server_error", "SERVER_ERROR", True),
    (503, "internal_server_error", "SERVER_ERROR", True),
    (599, None, "SERVER_ERROR", True),
    (418, "private-code-sentinel", "UNKNOWN", False),
])
def test_http_diagnostics_survive_sdk_normalization_without_content(
    monkeypatch, caplog, status, code, category, retryable,
) -> None:
    prepare_comparison_transport()
    requests = []

    async def handle(request):
        requests.append(request)
        return httpx.Response(status, headers={"x-request-id": "private-header-sentinel"}, json={
            "error": {"code": code, "message": "private-quote-sentinel",
                      "param": "private-param-sentinel", "type": "private-type-sentinel"},
        })

    async def exercise():
        http = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        sdk = SDKAsyncOpenAI(api_key="private-key-sentinel", max_retries=0, http_client=http)
        def factory(**kwargs):
            assert kwargs["max_retries"] == 0
            return sdk
        monkeypatch.setattr("sourcepilot.ai.client.AsyncOpenAI", factory)
        monkeypatch.setattr("sourcepilot.ai.client.httpx", SimpleNamespace(AsyncClient=lambda **_: http))
        token = current_deadline.set(ComparisonDeadline())
        try:
            client = OpenAIResponsesClient(AISettings("private-key-sentinel", "fixture"))
            with pytest.raises(ModelProviderError) as failure:
                await client._invoke_comparison(instructions="private-prompt-sentinel", input_items=[],
                                                tools=[], schema_name="fixture", schema={})
            error = failure.value
            assert error.retryable is retryable
            assert error.diagnostics == ProviderDiagnostics(
                category, "OTHER_HTTP" if status == 418 else str(status),
                code if code and status != 418 else "UNKNOWN",
            )
            assert str(error) == "Comparison model request failed."
            assert "private-" not in repr(error.diagnostics) + caplog.text
            assert len(requests) == 1 and http.is_closed
        finally:
            current_deadline.reset(token)
            await sdk.close()
    asyncio.run(exercise())


class HostileDiagnostic:
    def __str__(self):
        raise AssertionError("Diagnostic string conversion")

    def __repr__(self):
        raise AssertionError("Diagnostic repr conversion")

    def __hash__(self):
        raise AssertionError("Diagnostic hashing")


@pytest.mark.parametrize("status", [None, True, "401", 401.0, [], HostileDiagnostic(), 99, 600])
def test_malformed_sdk_status_and_code_are_not_serialized(status) -> None:
    request = httpx.Request("POST", "https://fixture.invalid")
    error = APIStatusError("private-message", response=httpx.Response(400, request=request), body=None)
    error.__dict__["status_code"] = status
    error.__dict__["code"] = HostileDiagnostic()
    assert comparison_provider_diagnostics(error) == ProviderDiagnostics()


@pytest.mark.parametrize("phase", ["construction", "request"])
@pytest.mark.parametrize("kind,category", [
    ("type", "LOCAL_CLIENT_ERROR"), ("value", "LOCAL_CLIENT_ERROR"),
    ("connection", "CONNECTION"), ("timeout", "TIMEOUT"), ("unexpected", "UNKNOWN"),
])
def test_non_http_failures_are_classified_without_guessing(monkeypatch, caplog, phase, kind, category):
    prepare_comparison_transport()
    request = httpx.Request("POST", "https://fixture.invalid/private-url-sentinel")
    errors = {
        "type": TypeError("private-type-sentinel"), "value": ValueError("private-value-sentinel"),
        "connection": APIConnectionError(message="private-connect-sentinel", request=request),
        "timeout": APITimeoutError(request), "unexpected": RuntimeError(HostileDiagnostic()),
    }
    error = errors[kind]

    async def exercise():
        http = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("Unexpected HTTP")))
        sdk = SDKAsyncOpenAI(api_key="synthetic", max_retries=0, http_client=http)
        def factory(**kwargs):
            if phase == "construction":
                raise error
            return sdk
        async def fail(*args, **kwargs):
            raise error
        monkeypatch.setattr("sourcepilot.ai.client.AsyncOpenAI", factory)
        monkeypatch.setattr("sourcepilot.ai.client.httpx", SimpleNamespace(AsyncClient=lambda **_: http))
        monkeypatch.setattr(AsyncResponses, "create", fail)
        token = current_deadline.set(ComparisonDeadline())
        try:
            client = OpenAIResponsesClient(AISettings("synthetic", "fixture"))
            with pytest.raises(ModelProviderError) as failure:
                await client._invoke_comparison(instructions="fixture", input_items=[], tools=[],
                                                schema_name="fixture", schema={})
            assert failure.value.retryable is True
            assert failure.value.diagnostics == ProviderDiagnostics(category=category)
            assert str(failure.value) == "Comparison model request failed."
            assert "private-" not in caplog.text
        finally:
            current_deadline.reset(token)
            await sdk.close()
    asyncio.run(exercise())


def test_untrusted_status_bearing_exception_is_unknown() -> None:
    error = RuntimeError(cast(Any, HostileDiagnostic()))
    error.__dict__.update(status_code=401, code="invalid_api_key")
    assert comparison_provider_diagnostics(error) == ProviderDiagnostics()


@pytest.mark.parametrize("code", sorted(PROVIDER_CODES - {"UNKNOWN"}))
def test_only_parsed_allowlisted_sdk_codes_are_retained(code) -> None:
    request = httpx.Request("POST", "https://fixture.invalid")
    error = APIStatusError("private-message", response=httpx.Response(400, request=request),
                           body={"code": code})
    assert comparison_provider_diagnostics(error) == ProviderDiagnostics("INVALID_REQUEST", "400", code)


def test_hostile_diagnostic_fields_and_lookalike_timeout_remain_unknown() -> None:
    value = HostileDiagnostic()
    assert ProviderDiagnostics(value, value, value) == ProviderDiagnostics()  # type: ignore[arg-type]
    lookalike = type("APITimeoutError", (RuntimeError,), {})(value)
    assert comparison_provider_diagnostics(lookalike) == ProviderDiagnostics()


class ScriptedNetwork:
    """Fake sockets below the real HTTPX/HTTPCore HTTP/1.1 transport."""

    def __init__(self, phase=None, action="timeout", responses=1):
        self.phase, self.action = phase, action
        self.responses = responses
        self.connections = 0
        self.closed = 0
        self.events = []

    async def fail_at(self, phase):
        import httpcore
        self.events.append(phase)
        if phase != self.phase:
            return
        if self.action == "cancel":
            task = asyncio.current_task()
            assert task is not None
            task.cancel()
            await asyncio.sleep(0)
        if self.action == "stall":
            await asyncio.sleep(60)
        kind = (httpcore.ConnectTimeout if phase in {"CONNECT_TCP", "START_TLS"} else
                httpcore.WriteTimeout if phase.startswith("SEND_") else httpcore.ReadTimeout)
        raise kind("private-network-message")

    async def connect_tcp(self, host, port, **kwargs):
        import httpcore
        network = self
        network.connections += 1
        await self.fail_at("CONNECT_TCP")

        class Stream(httpcore.AsyncMockStream):
            def __init__(self):
                body = b'{"id":"resp_fixture","object":"response","created_at":0,"model":"fixture","output":[]}'
                super().__init__([b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
                                  + str(len(body)).encode() + b"\r\n\r\n", body] * network.responses)
                self.writes = self.reads = 0

            async def start_tls(self, *args, **kwargs):
                try:
                    await network.fail_at("START_TLS")
                except BaseException:
                    await self.aclose()
                    raise
                return self

            async def write(self, buffer, timeout=None):
                self.writes += 1
                await network.fail_at("SEND_REQUEST_HEADERS" if self.writes == 1 else "SEND_REQUEST_BODY")

            async def read(self, max_bytes, timeout=None):
                self.reads += 1
                await network.fail_at("RECEIVE_RESPONSE_HEADERS" if self.reads == 1 else "RECEIVE_RESPONSE_BODY")
                return await super().read(max_bytes, timeout)

            async def aclose(self):
                network.closed += 1
                await super().aclose()

        return Stream()


def real_transport_http(network):
    import httpcore
    transport = httpx.AsyncHTTPTransport()
    # Replace only sockets; default HTTPX mapping and real HTTPCore tracing execute.
    transport._pool = httpcore.AsyncConnectionPool(network_backend=network)
    return httpx.AsyncClient(transport=transport)


@pytest.mark.parametrize("phase,origin", [
    ("CONNECT_TCP", "SDK_CONNECT"), ("START_TLS", "SDK_CONNECT"),
    ("SEND_REQUEST_HEADERS", "SDK_WRITE"), ("SEND_REQUEST_BODY", "SDK_WRITE"),
    ("RECEIVE_RESPONSE_HEADERS", "SDK_READ"), ("RECEIVE_RESPONSE_BODY", "SDK_READ"),
])
@pytest.mark.parametrize("action", ["timeout", "stall", "cancel"])
def test_real_transport_observes_failure_and_cancellation(monkeypatch, caplog, phase, origin, action):
    from sourcepilot.comparison.deadline import TimeoutDiagnostics
    network = ScriptedNetwork(phase, action)
    monkeypatch.setattr("sourcepilot.ai.client.AsyncOpenAI", SDKAsyncOpenAI)
    monkeypatch.setattr("sourcepilot.ai.client.httpx", SimpleNamespace(
        AsyncClient=lambda **kwargs: real_transport_http(network)))
    prepare_comparison_transport()

    async def exercise():
        deadline = ComparisonDeadline(ComparisonTimeouts(total=5, attempt=0.05 if action == "stall" else 2, cleanup=0.2))
        token = current_deadline.set(deadline)
        try:
            client = OpenAIResponsesClient(AISettings("private-key", "fixture"))
            expected = asyncio.CancelledError if action == "cancel" else ModelProviderError
            with pytest.raises(expected) as failure:
                await client._invoke_comparison(instructions="private-prompt", input_items=[], tools=[],
                                                schema_name="fixture", schema={})
            diagnostic = vars(failure.value)["timeout_diagnostics"]
            assert diagnostic == TimeoutDiagnostics(
                "UNKNOWN" if action == "cancel" else "APP_ATTEMPT" if action == "stall" else origin,
                phase, "FAILED",
            )
            assert network.connections == 1
            # Let the HTTP request-body generator finish cooperative finalization.
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert len(asyncio.all_tasks()) == 1
            assert "private-" not in repr(diagnostic) + caplog.text
        finally:
            current_deadline.reset(token)
    asyncio.run(exercise())


@pytest.mark.parametrize("phase", [None, "START_TLS", "RECEIVE_RESPONSE_BODY"])
def test_observation_failure_does_not_change_success_or_original_failure(monkeypatch, caplog, phase):
    from sourcepilot.ai.client import AttemptObservation
    network = ScriptedNetwork(phase)
    monkeypatch.setattr("sourcepilot.ai.client.AsyncOpenAI", SDKAsyncOpenAI)
    monkeypatch.setattr("sourcepilot.ai.client.httpx", SimpleNamespace(
        AsyncClient=lambda **kwargs: real_transport_http(network)))
    def broken(self, event):
        raise RuntimeError("private-observer-message")
    monkeypatch.setattr(AttemptObservation, "observe", broken)
    prepare_comparison_transport()

    async def exercise():
        token = current_deadline.set(ComparisonDeadline())
        try:
            client = OpenAIResponsesClient(AISettings("private-key", "fixture"))
            kwargs = {"instructions": "private-prompt", "input_items": [], "tools": [],
                      "schema_name": "fixture", "schema": {}}
            if phase is None:
                result = await client._invoke_comparison(**kwargs)
                assert result.output_items == ()
            else:
                with pytest.raises(ModelProviderError) as failure:
                    await client._invoke_comparison(**kwargs)
                assert isinstance(failure.value.__cause__, APITimeoutError)
                assert failure.value.timeout_diagnostics.transport_phase == "UNKNOWN"
                assert failure.value.timeout_diagnostics.timeout_origin == (
                    "SDK_CONNECT" if phase == "START_TLS" else "SDK_READ")
            assert network.connections == network.closed == 1
            assert "private-" not in caplog.text
        finally:
            current_deadline.reset(token)
    asyncio.run(exercise())


def test_observation_privacy_unknown_reset_and_frozen_evidence():
    from sourcepilot.ai.client import AttemptObservation
    from sourcepilot.comparison.deadline import TimeoutDiagnostics
    async def exercise():
        observation = AttemptObservation()
        request = httpx.Request("POST", "https://fixture.invalid/?secret=private-url",
                                headers={"Authorization": "private-credential"}, content="private-content")
        await observation.request(request)
        await request.extensions["trace"]("connection.start_tls.started", cast(Any, HostileDiagnostic()))
        assert observation.phase == "START_TLS"
        await observation.trace("private-unrecognized-event", cast(Any, HostileDiagnostic()))
        assert observation.phase == observation.state == "UNKNOWN"
        await observation.trace("http11.receive_response_body.complete", cast(Any, HostileDiagnostic()))
        # A new HTTP exchange cannot borrow the previous exchange's operation.
        await observation.request(request)
        assert observation.phase == observation.state == "UNKNOWN"
        await observation.trace("connection.connect_tcp.failed", cast(Any, HostileDiagnostic()))
        error = APITimeoutError(request)
        error.__cause__ = httpx.ConnectTimeout("private-message")
        snapshot = observation.freeze(error, ComparisonDeadline())
        await observation.trace("http11.receive_response_body.complete", cast(Any, HostileDiagnostic()))
        observation.cleanup_expired(ComparisonDeadline())
        assert observation.freeze(RuntimeError("private-close"), ComparisonDeadline()) is snapshot
        assert snapshot == TimeoutDiagnostics("SDK_CONNECT", "CONNECT_TCP", "FAILED")
        assert "private-" not in repr(snapshot)
        fresh = AttemptObservation()
        assert fresh.freeze(TimeoutError("private-message"), ComparisonDeadline()) == TimeoutDiagnostics()
        assert TimeoutDiagnostics(*[cast(Any, HostileDiagnostic()) for _ in range(3)]) == TimeoutDiagnostics()
    asyncio.run(exercise())


@pytest.mark.parametrize("broken", [False, True])
def test_observer_failure_preserves_external_cancellation(monkeypatch, broken):
    from sourcepilot.ai.client import AttemptObservation
    network = ScriptedNetwork("RECEIVE_RESPONSE_BODY", "cancel")
    monkeypatch.setattr("sourcepilot.ai.client.AsyncOpenAI", SDKAsyncOpenAI)
    monkeypatch.setattr("sourcepilot.ai.client.httpx", SimpleNamespace(
        AsyncClient=lambda **kwargs: real_transport_http(network)))
    if broken:
        def fail(self, event):
            raise RuntimeError("private-observer-failure")
        monkeypatch.setattr(AttemptObservation, "observe", fail)
    prepare_comparison_transport()
    async def exercise():
        token = current_deadline.set(ComparisonDeadline())
        try:
            client = OpenAIResponsesClient(AISettings("synthetic", "fixture"))
            with pytest.raises(asyncio.CancelledError) as failure:
                await client._invoke_comparison(instructions="fixture", input_items=[], tools=[],
                                                schema_name="fixture", schema={})
            assert vars(failure.value)["timeout_diagnostics"].transport_phase == (
                "UNKNOWN" if broken else "RECEIVE_RESPONSE_BODY")
            assert network.connections == network.closed == 1
        finally:
            current_deadline.reset(token)
    asyncio.run(exercise())


def test_hook_installation_failure_is_optional_and_does_not_read_payload():
    from sourcepilot.ai.client import AttemptObservation
    class BrokenClient:
        @property
        def event_hooks(self):
            raise RuntimeError("private-hook-failure")
    observation = AttemptObservation()
    observation.install(cast(Any, BrokenClient()))
    assert observation.phase == observation.state == "UNKNOWN"



def test_real_transport_reuse_reports_only_observed_operations():
    from sourcepilot.ai.client import AttemptObservation
    async def exercise():
        network = ScriptedNetwork(responses=2)
        observation = AttemptObservation()
        async with real_transport_http(network) as client:
            observation.install(client)
            await client.post("https://fixture.invalid", content=b"synthetic")
            assert (observation.phase, observation.state) == ("RECEIVE_RESPONSE_BODY", "COMPLETE")
            network.events.clear()
            await client.post("https://fixture.invalid", content=b"synthetic")
            assert network.connections == 1
            assert "CONNECT_TCP" not in network.events and "START_TLS" not in network.events
            assert (observation.phase, observation.state) == ("RECEIVE_RESPONSE_BODY", "COMPLETE")
        assert network.closed == 1
    asyncio.run(exercise())


@pytest.mark.parametrize("close_failure,origin", [
    ("expiry", "APP_CLEANUP_BUDGET"), ("timeout", "UNKNOWN"), ("error", "UNKNOWN"),
])
def test_cleanup_expiry_is_distinct_from_close_failure(monkeypatch, caplog, close_failure, origin):
    from sourcepilot.comparison.deadline import TimeoutDiagnostics
    network = ScriptedNetwork()
    class ClosingSDK(SDKAsyncOpenAI):
        async def close(self):
            await super().close()
            if close_failure == "expiry":
                await asyncio.sleep(60)
            if close_failure == "timeout":
                raise TimeoutError("private-close")
            raise RuntimeError("private-close")
    monkeypatch.setattr("sourcepilot.ai.client.AsyncOpenAI", ClosingSDK)
    monkeypatch.setattr("sourcepilot.ai.client.httpx", SimpleNamespace(
        AsyncClient=lambda **kwargs: real_transport_http(network)))
    prepare_comparison_transport()
    async def exercise():
        token = current_deadline.set(ComparisonDeadline(ComparisonTimeouts(total=5, attempt=2, cleanup=0.1)))
        try:
            client = OpenAIResponsesClient(AISettings("synthetic", "fixture"))
            with pytest.raises(ComparisonDeadlineError) as failure:
                await client._invoke_comparison(instructions="fixture", input_items=[], tools=[],
                                                schema_name="fixture", schema={})
            assert failure.value.timeout_diagnostics == TimeoutDiagnostics(
                origin, "RECEIVE_RESPONSE_BODY", "COMPLETE")
            assert network.connections == network.closed == 1
            assert "private-" not in repr(failure.value.timeout_diagnostics) + caplog.text
        finally:
            current_deadline.reset(token)
    asyncio.run(exercise())
