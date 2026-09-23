from typing import Protocol

from sourcepilot.persistence.models import AIRun


class AIRunTracer(Protocol):
    def record(self, air_run: AIRun) -> None: ...


class NoOpAIRunTracer:
    """Optional observability must never affect SourcePilot behavior."""

    def record(self, air_run: AIRun) -> None:
        return None
