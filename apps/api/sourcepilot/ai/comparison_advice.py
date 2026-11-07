"""Versioned combined tradeoff/suggestion task over the existing read-only analyst."""

import time
from collections.abc import Callable
from typing import Any, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from sourcepilot.ai.advice_selection import SELECTION_INSTRUCTIONS, AdviceSelectionTask
from sourcepilot.ai.analyst_tools import ComparisonSnapshotResult
from sourcepilot.ai.client import StructuredModelClient
from sourcepilot.ai.supplier_explanation import MAX_MODEL_TURNS, MAX_TOOL_CALLS
from sourcepilot.ai.tradeoff_analysis import (
    TradeoffAnalysis,
    TradeoffNotReadyError,
    run_comparison_analyst,
    validate_analysis,
)
from sourcepilot.comparison.advice import SuggestedSupplierResult, validate_suggestion
from sourcepilot.comparison.execution import bounded_comparison
from sourcepilot.comparison.validation import ComparisonRejection, RejectionCode
from sourcepilot.persistence.models import ProjectSupplier

CONTRACT_VERSION = "comparison-advice-v1"
PROMPT_VERSION = "comparison-advice-v10"
INSTRUCTIONS = SELECTION_INSTRUCTIONS


class ComparisonAdviceV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis: TradeoffAnalysis
    suggestion: SuggestedSupplierResult


ComparisonAdvice = ComparisonAdviceV1


class ComparisonAdviceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: UUID


class ComparisonAdviceResponse(ComparisonAdvice):
    run_id: UUID
    snapshot_id: UUID


def validate_advice(advice: ComparisonAdvice, snapshot: ComparisonSnapshotResult) -> None:
    validate_analysis(advice.analysis, snapshot)
    if snapshot.comparison_payload is None:
        raise ComparisonRejection(RejectionCode.SNAPSHOT_MISSING, "Current comparison payload is missing.")
    try:
        validate_suggestion(advice.suggestion, cast(dict[str, Any], snapshot.comparison_payload))
    except ComparisonRejection as error:
        error.phase = "suggestion"
        raise


def check_advice_scope(session: Session, project_id: UUID, expected_id: UUID,
                       snapshot: ComparisonSnapshotResult) -> None:
    """Revalidate membership using fresh scalar reads, without revision infrastructure."""
    if snapshot.snapshot_id != expected_id or snapshot.comparison_payload is None:
        raise TradeoffNotReadyError("COMPARISON_STALE", "The comparison changed. Regenerate and retry.")
    participating = {UUID(item["supplier_id"])
                     for item in cast(list[dict[str, Any]], snapshot.comparison_payload["suppliers"])}
    with session.no_autoflush:
        current = set(session.scalars(select(ProjectSupplier.supplier_id).where(
            ProjectSupplier.project_id == project_id, ProjectSupplier.shortlisted.is_(True),
            ProjectSupplier.dismissed.is_(False),
        )))
    if not participating <= current:
        raise TradeoffNotReadyError("COMPARISON_STALE", "The shortlist changed. Regenerate and retry.")


@bounded_comparison
def analyze_comparison_advice(
    session: Session, *, demo_session_id: UUID, project_id: UUID, snapshot_id: UUID,
    client_factory: Callable[[], StructuredModelClient],
    max_model_turns: int = MAX_MODEL_TURNS, max_tool_calls: int = MAX_TOOL_CALLS,
    sleep: Callable[[float], None] = time.sleep,
) -> ComparisonAdviceResponse:
    run_id, bound_id, result = run_comparison_analyst(
        session, demo_session_id=demo_session_id, project_id=project_id,
        client_factory=client_factory, operation="comparison_advice", prompt_version=PROMPT_VERSION,
        base_instructions=INSTRUCTIONS, result_type=ComparisonAdvice, validate=validate_advice,
        check_snapshot=lambda snapshot: check_advice_scope(session, project_id, snapshot_id, snapshot),
        max_model_turns=max_model_turns, max_tool_calls=max_tool_calls, sleep=sleep,
        selection_factory=AdviceSelectionTask,
    )
    return ComparisonAdviceResponse(run_id=run_id, snapshot_id=bound_id,
                                   analysis=result.analysis, suggestion=result.suggestion)
