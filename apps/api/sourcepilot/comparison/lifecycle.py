"""Application ownership of comparison admission and incidental resolver helpers.

This is not a job runner: only comparison requests acquire slots. Underlying
executor futures retain a slot after cancellation until their actual completion.
"""
from __future__ import annotations

import asyncio
import functools
import logging
import os
import socket
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from contextvars import Context, ContextVar
from typing import Any, TypeVar

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from sourcepilot.comparison.deadline import ComparisonDeadline, current_deadline

logger = logging.getLogger(__name__)
T = TypeVar("T")


class ComparisonCapacityError(RuntimeError):
    pass


class ComparisonOwner:
    def __init__(self, runtime: ComparisonLifecycle) -> None:
        self.runtime = runtime
        self.task = asyncio.current_task()
        self.helpers: set[Future[Any]] = set()
        self.resources: dict[str, object] = {}
        self.finished = False
        self.cancelled_during_cleanup = False

    def release_if_finished(self) -> None:
        if self.finished and not self.helpers and not self.resources:
            self.runtime.owners.discard(self)

    def helper_finished(self, future: Future[Any]) -> None:
        self.helpers.discard(future)
        self.release_if_finished()


current_owner: ContextVar[ComparisonOwner | None] = ContextVar("comparison_owner", default=None)


def _allowed_helper(function: Callable[..., Any]) -> bool:
    from openai import _base_client

    if isinstance(function, functools.partial):
        if getattr(function.func, "__self__", None).__class__ is Context:
            return bool(function.args) and _allowed_helper(function.args[0])
        return _allowed_helper(function.func)
    return function in {socket.getaddrinfo, _base_client.get_platform} or (
        getattr(function, "__name__", None) == "_getaddrinfo_debug"
        and isinstance(getattr(function, "__self__", None), asyncio.BaseEventLoop)
    )


class ComparisonExecutor(ThreadPoolExecutor):
    def submit(self, fn: Callable[..., T], /, *args: Any, **kwargs: Any) -> Future[T]:
        owner = current_owner.get()
        if owner is not None and not _allowed_helper(fn):
            raise RuntimeError("Unexpected comparison executor operation.")
        future = super().submit(fn, *args, **kwargs)
        if owner is not None:
            owner.helpers.add(future)
            loop = owner.runtime.loop

            def completed(done: Future[Any]) -> None:
                try:
                    loop.call_soon_threadsafe(owner.helper_finished, done)
                except RuntimeError:
                    # Application exit cannot promise resolver-thread termination.
                    logger.warning("Comparison helper finished after application loop closure.")

            future.add_done_callback(completed)
        return future


def comparison_loop() -> asyncio.AbstractEventLoop:
    """Explicit Uvicorn loop factory: psycopg async needs Selector on Windows."""
    loop = asyncio.SelectorEventLoop()
    loop.set_default_executor(ComparisonExecutor(thread_name_prefix="sourcepilot-io"))
    return loop


class ComparisonLifecycle:
    def __init__(self, capacity: int | None = None) -> None:
        self.loop = asyncio.get_running_loop()
        if os.name == "nt" and not isinstance(self.loop, asyncio.SelectorEventLoop):
            raise RuntimeError("Comparison requires --loop sourcepilot.comparison.lifecycle:comparison_loop")
        self.capacity = capacity if capacity is not None else int(
            os.environ.get("SOURCEPILOT_ANALYSIS_CAPACITY", "2"))
        if self.capacity <= 0:
            raise ValueError("Comparison admission capacity must be a positive integer.")
        # Installed before accepting requests; do not silently replace another owner's executor.
        existing = getattr(self.loop, "_default_executor", None)
        if existing is None:
            self.loop.set_default_executor(ComparisonExecutor(thread_name_prefix="sourcepilot-io"))
        elif not isinstance(existing, ComparisonExecutor):
            raise RuntimeError("Comparison requires its configured application loop executor.")
        self.owners: set[ComparisonOwner] = set()
        self.accepting = True

    def acquire(self) -> ComparisonOwner:
        if not self.accepting or len(self.owners) >= self.capacity:
            raise ComparisonCapacityError("Comparison capacity exhausted.")
        owner = ComparisonOwner(self)
        self.owners.add(owner)
        return owner

    async def shutdown(self) -> None:
        self.accepting = False
        tasks = {owner.task for owner in self.owners if not owner.finished and owner.task is not None}
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.wait(tasks, timeout=5)
        if self.owners:
            logger.warning("Comparison shutdown has unfinished resources or resolver helpers.")


class ComparisonLifecycleMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "").split("/")
        analysis = (scope["type"] == "http" and scope.get("method") == "POST"
                    and len(path) == 5 and path[1] == "projects" and path[3] == "comparison"
                    and path[4] in {"advice", "analysis"})
        if not analysis:
            await self.app(scope, receive, send)
            return
        from sourcepilot.api_errors import error_response

        deadline = ComparisonDeadline()
        runtime = getattr(scope["app"].state, "comparison_lifecycle", None)
        try:
            if runtime is None:
                raise ComparisonCapacityError()
            owner = runtime.acquire()
        except ComparisonCapacityError:
            await error_response(503, code="COMPARISON_ANALYSIS_BUSY",
                                 message="Analysis is busy. Please try again shortly.")(scope, receive, send)
            return
        token = current_owner.set(owner)
        budget_token = current_deadline.set(deadline)
        sent = False

        async def bounded_send(message: Message) -> None:
            nonlocal sent
            if message["type"] == "http.response.start":
                if 200 <= message["status"] < 300:
                    deadline.remaining(total=True)
                sent = True
            await send(message)

        try:
            async with asyncio.timeout(deadline.remaining(total=True)):
                await self.app(scope, receive, bounded_send)
        except TimeoutError:
            if not sent:
                # One bounded error-handoff attempt; client receipt is not guaranteed.
                try:
                    async with asyncio.timeout(0):
                        await error_response(504, code="COMPARISON_ANALYSIS_TIMEOUT",
                                             message="Analysis took too long. Please retry.")(scope, receive, send)
                except TimeoutError:
                    pass
        finally:
            owner.finished = True
            owner.release_if_finished()
            current_deadline.reset(budget_token)
            current_owner.reset(token)
