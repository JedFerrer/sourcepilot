"""Comparison I/O on the application's loop, with exclusive resource ownership."""
from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import Any, Concatenate, ParamSpec, TypeVar

from sqlalchemy import Engine, event
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from sourcepilot.comparison.deadline import (
    ComparisonDeadline,
    ComparisonDeadlineError,
    TimeoutDiagnostics,
    current_deadline,
)
from sourcepilot.comparison.lifecycle import ComparisonLifecycle, comparison_loop, current_owner

logger = logging.getLogger(__name__)
T = TypeVar("T")
P = ParamSpec("P")
_cli_runner: ContextVar[asyncio.Runner | None] = ContextVar("comparison_cli_runner", default=None)
_cli_runtime: ContextVar[ComparisonLifecycle | None] = ContextVar("comparison_cli_runtime", default=None)


async def cleanup_attempt(name: str, resource: object, action: Callable[[], Awaitable[object]],
                          deadline: ComparisonDeadline, fraction: float = 0.15,
                          on_timeout: Callable[[], None] | None = None) -> bool:
    """Independent cooperative attempt; retain ownership on unconfirmed release."""
    owner = current_owner.get()
    key = f"{name}:{id(resource)}"
    if owner is not None:
        owner.resources[key] = resource
    seconds = max(0, min(deadline.settings.cleanup * fraction,
                         deadline.started + deadline.settings.total - deadline.clock()))
    complete = False
    cleanup_timeout: asyncio.Timeout | None = None
    try:
        async with asyncio.timeout(seconds) as cleanup_timeout:
            await action()
        complete = seconds > 0 and deadline.clock() < deadline.started + deadline.settings.total
    except asyncio.CancelledError:
        task = asyncio.current_task()
        own_timeout = ((deadline.work_timeout is not None and deadline.work_timeout.expired())
                       or (deadline.total_timeout is not None and deadline.total_timeout.expired())
                       or deadline.clock() >= deadline.started + deadline.settings.total)
        if owner is not None and task is not None and task.cancelling() and not own_timeout:
            owner.cancelled_during_cleanup = True
    except TimeoutError:
        if cleanup_timeout is not None and cleanup_timeout.expired() and on_timeout is not None:
            try:
                on_timeout()
            except Exception:  # noqa: BLE001, S110 - optional observation cannot change cleanup
                pass
        complete = False
    except Exception:  # noqa: BLE001 - independent cleanup, safe log below
        complete = False
    if complete and owner is not None:
        owner.resources.pop(key, None)
    if not complete:
        logger.warning("Comparison cleanup incomplete: %s.", name)
    return complete


async def run_async_comparison(session: Session, operation: Callable[[Session], T]) -> T:
    deadline = current_deadline.get() or ComparisonDeadline()
    token = current_deadline.set(deadline)
    bind = session.get_bind()
    url = bind.url if isinstance(bind, Engine) else bind.engine.url
    engine = create_async_engine(url, poolclass=NullPool)
    owned = AsyncSession(engine, expire_on_commit=False)
    connections: list[object] = []
    try:
        @event.listens_for(engine.sync_engine, "connect")
        def remember_connection(connection: object, record: object) -> None:
            connections.append(connection)

        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def before_statement(connection: Any, cursor: Any, statement: str,
                             parameters: Any, context: Any, executemany: bool) -> None:
            milliseconds = max(1, int(deadline.remaining() * 1000))
            # Driver-level execution avoids recursively entering this SQLAlchemy
            # event. Fixed keys and generated durations contain no user content.
            cursor.execute("SELECT set_config('statement_timeout', %s, true), "
                           "set_config('lock_timeout', %s, true)",
                           (f"{milliseconds}ms", f"{milliseconds}ms"))
            deadline.check()

        @event.listens_for(engine.sync_engine, "commit")
        def before_commit(*args: object) -> None:
            deadline.check()

        async with asyncio.timeout(deadline.remaining(total=True)) as terminal_timeout:
            deadline.total_timeout = terminal_timeout
            async with asyncio.timeout(deadline.remaining()) as work_timeout:
                deadline.work_timeout = work_timeout
                result = await owned.run_sync(operation)
                deadline.remaining(total=True)
                return result
    except TimeoutError as error:
        diagnostics = (error.timeout_diagnostics if isinstance(error, ComparisonDeadlineError)
                       else TimeoutDiagnostics(deadline.timeout_origin()))
        raise ComparisonDeadlineError("Comparison analysis deadline exceeded.",
                                      diagnostics=diagnostics) from error
    except DBAPIError as error:
        if getattr(error.orig, "sqlstate", None) in {"57014", "55P03"}:
            raise ComparisonDeadlineError("Comparison database wait exceeded its budget.") from error
        raise
    finally:
        primary_error = sys.exception()
        deadline.work_timeout = None
        deadline.total_timeout = None
        # Each attempt is clamped to the original total, outside spent contexts.
        try:
            closed = await cleanup_attempt("session", owned, owned.close, deadline)
        finally:
            try:
                disposed = await cleanup_attempt("engine", engine, engine.dispose, deadline)
            finally:
                current_deadline.reset(token)
        if not closed or not disposed:
            # NullPool + this request's psycopg connections only. libpq finish
            # closes local sockets without starting a rollback/query or waiting.
            released = True
            for connection in connections:
                try:
                    driver = getattr(connection, "driver_connection")  # noqa: B009 - narrow driver boundary
                    driver.pgconn.finish()
                    released = released and driver.closed
                except Exception:  # noqa: BLE001 - retain slot if force release is unconfirmed
                    released = False
            owner = current_owner.get()
            if released and owner is not None:
                owner.resources.pop(f"session:{id(owned)}", None)
                owner.resources.pop(f"engine:{id(engine)}", None)
            if owner is not None and owner.cancelled_during_cleanup:
                raise asyncio.CancelledError()
            if primary_error is None:
                raise ComparisonDeadlineError("Comparison cleanup incomplete.")
        if primary_error is None:
            deadline.remaining(total=True)
        owner = current_owner.get()
        if owner is not None and owner.cancelled_during_cleanup:
            raise asyncio.CancelledError()


@contextmanager
def comparison_cli_lifecycle() -> Iterator[asyncio.Runner]:
    """One CLI/eval lifecycle; shutdown can wait for OS resolver helpers."""
    from sourcepilot.ai.client import prepare_comparison_transport

    prepare_comparison_transport()
    with asyncio.Runner(loop_factory=comparison_loop) as runner:
        async def initialize() -> ComparisonLifecycle:
            return ComparisonLifecycle()

        runtime_token = _cli_runtime.set(runner.run(initialize()))
        token = _cli_runner.set(runner)
        try:
            yield runner
        finally:
            _cli_runner.reset(token)
            _cli_runtime.reset(runtime_token)


def run_bounded_comparison(session: Session, operation: Callable[[Session], T]) -> T:
    if current_deadline.get() is not None:
        return operation(session)

    async def execute() -> T:
        runtime = _cli_runtime.get() or ComparisonLifecycle()
        owner = runtime.acquire()
        token = current_owner.set(owner)
        try:
            return await run_async_comparison(session, operation)
        finally:
            owner.finished = True
            owner.release_if_finished()
            current_owner.reset(token)

    runner = _cli_runner.get()
    if runner is not None:
        return runner.run(execute())
    # Single direct invocation compatibility. HTTP never enters this branch.
    with comparison_cli_lifecycle() as runner:
        return runner.run(execute())


def bounded_comparison(operation: Callable[Concatenate[Session, P], T]
                       ) -> Callable[Concatenate[Session, P], T]:
    @wraps(operation)
    def invoke(session: Session, *args: P.args, **kwargs: P.kwargs) -> T:
        return run_bounded_comparison(session, lambda owned: operation(owned, *args, **kwargs))
    return invoke
