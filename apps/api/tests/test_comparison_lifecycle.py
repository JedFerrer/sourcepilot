"""Application-loop ownership, real helper cancellation and independent cleanup."""
import asyncio
import socket
import threading
import time

import pytest
import uvicorn

from sourcepilot.ai.client import prepare_comparison_transport
from sourcepilot.comparison.deadline import ComparisonDeadline, ComparisonTimeouts
from sourcepilot.comparison.execution import cleanup_attempt
from sourcepilot.comparison.lifecycle import (
    ComparisonCapacityError,
    ComparisonLifecycle,
    comparison_loop,
    current_owner,
)


@pytest.mark.parametrize("reload,workers", [(False, 1), (True, 1), (False, 2)])
def test_supported_uvicorn_loop_in_every_launch_mode(reload: bool, workers: int) -> None:
    config = uvicorn.Config("sourcepilot.main:app", reload=reload, workers=workers,
                            loop="sourcepilot.comparison.lifecycle:comparison_loop")
    factory = config.get_loop_factory()
    assert factory is not None
    loop = factory()
    try:
        assert isinstance(loop, asyncio.SelectorEventLoop)
    finally:
        loop.close()


def test_startup_prepares_transport_without_credentials_or_provider(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    prepare_comparison_transport.cache_clear()
    tls, platform = prepare_comparison_transport()
    assert tls and platform
    from openai import _base_client

    def unexpected_probe():
        raise AssertionError("Cold platform inspection must not run in requests")

    monkeypatch.setattr(_base_client, "get_platform", unexpected_probe)
    assert prepare_comparison_transport() == (tls, platform)


@pytest.mark.parametrize("value", ["0", "-1", "nan", "1.5"])
def test_invalid_capacity_rejected(value: str, monkeypatch) -> None:
    monkeypatch.setenv("SOURCEPILOT_ANALYSIS_CAPACITY", value)

    async def exercise():
        with pytest.raises(ValueError):
            ComparisonLifecycle()

    with asyncio.Runner(loop_factory=comparison_loop) as runner:
        runner.run(exercise())


def test_repeated_dns_timeouts_retain_capacity_until_real_helpers_finish(monkeypatch) -> None:
    monkeypatch.setenv("SOURCEPILOT_ANALYSIS_CAPACITY", "1")
    release = threading.Event()
    started = threading.Event()

    def blocked_resolver(*args, **kwargs):
        started.set()
        assert release.wait(3)
        return []

    monkeypatch.setattr(socket, "getaddrinfo", blocked_resolver)

    async def exercise():
        runtime = ComparisonLifecycle()
        assert runtime.capacity == 1
        for _ in range(3):
            release.clear()
            started.clear()
            owner = runtime.acquire()
            token = current_owner.set(owner)
            request_start = time.monotonic()
            try:
                with pytest.raises(TimeoutError):
                    async with asyncio.timeout(0.03):
                        await asyncio.get_running_loop().getaddrinfo("fixture.invalid", 443)
            finally:
                owner.finished = True
                owner.release_if_finished()
                current_owner.reset(token)
            assert started.is_set() and owner.helpers
            assert time.monotonic() - request_start < 0.25
            start = time.monotonic()
            for _ in range(5):
                with pytest.raises(ComparisonCapacityError):
                    runtime.acquire()
            assert time.monotonic() - start < 0.1
            release.set()
            for _ in range(100):
                if not runtime.owners:
                    break
                await asyncio.sleep(0.005)
            assert not runtime.owners
        await runtime.shutdown()
        with pytest.raises(ComparisonCapacityError):
            runtime.acquire()

    try:
        with asyncio.Runner(loop_factory=comparison_loop) as runner:
            runner.run(exercise())
    finally:
        release.set()


def test_sdk_platform_helper_is_tracked_and_no_provider_request_continues(monkeypatch) -> None:
    import httpx
    from openai import AsyncOpenAI, _base_client

    release = threading.Event()
    calls = []

    def blocked_platform():
        assert release.wait(3)
        return "Windows"

    monkeypatch.setattr(_base_client, "get_platform", blocked_platform)

    async def exercise():
        runtime = ComparisonLifecycle(1)
        owner = runtime.acquire()
        token = current_owner.set(owner)
        http = httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: calls.append(request) or httpx.Response(500)))
        client = AsyncOpenAI(api_key="synthetic", max_retries=0, http_client=http)
        request_start = time.monotonic()
        try:
            with pytest.raises(TimeoutError):
                async with asyncio.timeout(0.04):
                    await client.responses.create(model="fixture", input="fixture", store=False)
        finally:
            await client.close()
            owner.finished = True
            owner.release_if_finished()
            current_owner.reset(token)
        assert http.is_closed and not calls and owner.helpers
        assert time.monotonic() - request_start < 0.25
        with pytest.raises(ComparisonCapacityError):
            runtime.acquire()
        release.set()
        for _ in range(100):
            if not runtime.owners:
                break
            await asyncio.sleep(0.005)
        assert not runtime.owners and not calls

    try:
        with asyncio.Runner(loop_factory=comparison_loop) as runner:
            runner.run(exercise())
    finally:
        release.set()


@pytest.mark.parametrize("mode", ["timeout", "error", "cancel", "exhausted"])
def test_cleanup_attempts_are_independent_and_incomplete_is_not_release(mode, caplog) -> None:
    async def exercise():
        runtime = ComparisonLifecycle(1)
        owner = runtime.acquire()
        token = current_owner.set(owner)
        deadline = ComparisonDeadline(ComparisonTimeouts(1, 0.5, 0.2))
        if mode == "exhausted":
            deadline.started -= 2
        events = []
        first, second = object(), object()

        async def close():
            events.append("close")
            if mode == "error":
                raise RuntimeError("sensitive-sentinel")
            if mode == "cancel":
                raise asyncio.CancelledError()
            await asyncio.sleep(1)

        async def dispose():
            events.append("dispose")
            await asyncio.sleep(0)

        try:
            assert not await cleanup_attempt("session", first, close, deadline)
            disposed = await cleanup_attempt("engine", second, dispose, deadline)
            assert disposed == (mode != "exhausted")
            assert events == ["close", "dispose"]
            owner.finished = True
            owner.release_if_finished()
            with pytest.raises(ComparisonCapacityError):
                runtime.acquire()
            assert f"session:{id(first)}" in owner.resources
        finally:
            current_owner.reset(token)

    with asyncio.Runner(loop_factory=comparison_loop) as runner:
        runner.run(exercise())
    assert "cleanup incomplete" in caplog.text
    assert "sensitive-sentinel" not in caplog.text


def test_unrelated_executor_work_is_unchanged_and_write_helpers_fail_closed() -> None:
    async def exercise():
        assert await asyncio.to_thread(lambda: 42) == 42
        runtime = ComparisonLifecycle(1)
        owner = runtime.acquire()
        token = current_owner.set(owner)
        called = []
        try:
            with pytest.raises(RuntimeError, match="Unexpected comparison executor"):
                await asyncio.to_thread(lambda: called.append(True))
            assert not called
        finally:
            current_owner.reset(token)

    with asyncio.Runner(loop_factory=comparison_loop) as runner:
        runner.run(exercise())


def test_shutdown_cancels_request_but_retains_running_helper_until_completion(monkeypatch) -> None:
    release = threading.Event()
    started = threading.Event()

    def resolve(*args, **kwargs):
        started.set()
        assert release.wait(3)
        return []

    monkeypatch.setattr(socket, "getaddrinfo", resolve)

    async def exercise():
        runtime = ComparisonLifecycle(1)

        async def request():
            owner = runtime.acquire()
            token = current_owner.set(owner)
            try:
                await asyncio.get_running_loop().getaddrinfo("fixture.invalid", 443)
            finally:
                owner.finished = True
                owner.release_if_finished()
                current_owner.reset(token)

        task = asyncio.create_task(request())
        while not started.is_set():
            await asyncio.sleep(0.005)
        await runtime.shutdown()
        assert task.cancelled() and len(runtime.owners) == 1
        with pytest.raises(ComparisonCapacityError):
            runtime.acquire()
        release.set()
        for _ in range(100):
            if not runtime.owners:
                break
            await asyncio.sleep(0.005)
        assert not runtime.owners

    try:
        with asyncio.Runner(loop_factory=comparison_loop) as runner:
            runner.run(exercise())
    finally:
        release.set()
