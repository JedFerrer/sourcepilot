"""Exercise the installed SDK with an in-process transport; no provider access."""

import asyncio
from collections.abc import AsyncIterator
from types import SimpleNamespace

import httpx
import pytest
from openai import AsyncOpenAI as SDKAsyncOpenAI
from openai.resources.responses import (
    AsyncResponses,  # noqa: F401 - load SDK resources before timing
)

from sourcepilot.ai.client import (
    AISettings,
    ModelProviderError,
    OpenAIResponsesClient,
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
