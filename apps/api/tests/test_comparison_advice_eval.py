"""Scoring evaluates actual produced advice against each synthetic scenario."""

from copy import deepcopy
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from sourcepilot.ai import comparison_advice_eval_live as live
from sourcepilot.ai.comparison_advice_eval import (
    load_cases,
    recorded_advice,
    scenario_snapshot,
    score_case,
)


@pytest.mark.parametrize("case", load_cases(), ids=lambda case: case["id"])
def test_recorded_produced_results(case: dict[str, Any]) -> None:
    assert score_case(case, recorded_advice(case), scenario_snapshot(case)) is case["expected_grounded"]


def test_scorer_reads_actual_result_not_metadata() -> None:
    case = load_cases()[0]
    original = recorded_advice(case)
    assert score_case(case, original, scenario_snapshot(case))
    altered = deepcopy(original)
    altered.suggestion.supporting_reasons[0].text = "Supplier A confirmed current unit price is USD 99.99."
    assert not score_case(case, altered, scenario_snapshot(case))
    altered = deepcopy(original)
    altered.suggestion.supplier_id = None
    assert not score_case(case, altered, scenario_snapshot(case))
    altered = deepcopy(original)
    altered.suggestion.supporting_reasons[0].text = "Supplier A has a 92% match."
    assert not score_case(case, altered, scenario_snapshot(case))


def test_live_workflow_scores_each_actual_response(monkeypatch: pytest.MonkeyPatch) -> None:
    cases = [case for case in load_cases() if case["expected_grounded"]]
    called = []
    def fake_run(_session: object, **kwargs: Any) -> Any:
        case = next(case for case in cases if UUID(case["snapshot_id"]) == kwargs["snapshot_id"])
        called.append(case["id"])
        output = recorded_advice(case)
        if case["id"] == "clear-suggestion":
            output.suggestion.supporting_reasons[0].text = "Supplier A current unit price is USD 99.99."
        return SimpleNamespace(analysis=output.analysis, suggestion=output.suggestion,
                               run_id=uuid4())
    monkeypatch.setattr(live, "analyze_comparison_advice", fake_run)
    # Return a genuine contract to the scorer, while preserving the fake run id.
    actual_score = live.score_case
    def score(case: dict[str, Any], output: Any, snapshot: Any) -> bool:
        from sourcepilot.ai.comparison_advice import ComparisonAdvice
        return actual_score(case, ComparisonAdvice(analysis=output.analysis, suggestion=output.suggestion), snapshot)
    monkeypatch.setattr(live, "score_case", score)
    project = SimpleNamespace(id=uuid4(), demo_session_id=uuid4())
    results = live.run_scenarios(cast(Any, None), cast(Any, project), cast(Any, None))
    assert called == [case["id"] for case in cases]
    assert not results[0]["passed"] and all(result["passed"] for result in results[1:])
