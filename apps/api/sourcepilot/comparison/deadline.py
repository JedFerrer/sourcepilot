"""One comparison budget shared by provider, database, tools and cleanup."""

from __future__ import annotations

import asyncio
import math
import os
import time
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field


class ComparisonDeadlineError(TimeoutError):
    """The comparison's work or terminal bookkeeping budget was exhausted."""


@dataclass(frozen=True)
class ComparisonTimeouts:
    total: float = 180
    attempt: float = 60
    cleanup: float = 5

    def __post_init__(self) -> None:
        if not all(math.isfinite(value) and value > 0
                   for value in (self.total, self.attempt, self.cleanup)):
            raise ValueError("Comparison timeouts must be positive finite seconds.")
        if self.total <= self.cleanup:
            raise ValueError("Comparison total timeout must exceed its cleanup reserve.")

    @classmethod
    def from_environment(cls) -> ComparisonTimeouts:
        # The total is intentionally public and shared with the browser/proxy.
        return cls(
            total=float(os.environ.get("NEXT_PUBLIC_SOURCEPILOT_ANALYSIS_TIMEOUT_SECONDS", "180")),
            attempt=float(os.environ.get("SOURCEPILOT_ANALYSIS_ATTEMPT_SECONDS", "60")),
            cleanup=float(os.environ.get("SOURCEPILOT_ANALYSIS_CLEANUP_SECONDS", "5")),
        )


@dataclass
class ComparisonDeadline:
    settings: ComparisonTimeouts = field(default_factory=ComparisonTimeouts.from_environment)
    clock: Callable[[], float] = time.monotonic
    started: float = field(init=False)
    cleaning_up: bool = False
    work_timeout: asyncio.Timeout | None = None
    total_timeout: asyncio.Timeout | None = None
    cleanup_end: float | None = None

    def __post_init__(self) -> None:
        self.started = self.clock()

    def remaining(self, *, total: bool = False) -> float:
        limit = self.settings.total
        if not total and not self.cleaning_up:
            limit -= self.settings.cleanup
        end = self.started + limit
        if self.cleanup_end is not None and not total:
            end = min(end, self.cleanup_end)
        remaining = end - self.clock()
        if remaining <= 0:
            raise ComparisonDeadlineError("Comparison analysis deadline exceeded.")
        return remaining

    def check(self) -> None:
        self.remaining()

    def attempt_seconds(self) -> float:
        return min(self.settings.attempt, self.remaining())

    def begin_cleanup(self) -> None:
        if self.cleaning_up:
            return
        # Preserve independent resource and response reserves after bookkeeping.
        remaining = max(0, min(self.settings.cleanup * 0.4,
                               self.started + self.settings.total - self.clock()))
        self.cleaning_up = True
        self.cleanup_end = self.clock() + remaining
        if self.total_timeout is not None and not self.total_timeout.expired():
            self.total_timeout.reschedule(asyncio.get_running_loop().time() + remaining)
        if self.work_timeout is not None and not self.work_timeout.expired():
            self.work_timeout.reschedule(None)


current_deadline: ContextVar[ComparisonDeadline | None] = ContextVar(
    "comparison_deadline", default=None,
)


def check_deadline() -> None:
    deadline = current_deadline.get()
    if deadline is not None:
        deadline.check()
