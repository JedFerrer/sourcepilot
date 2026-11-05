"""Explicit opt-in combined advice eval; ordinary tests never call a live provider."""

import argparse
from typing import Any
from unittest.mock import patch
from uuid import UUID

from sqlalchemy.orm import Session

from sourcepilot.ai.client import ModelProviderError, OpenAIResponsesClient, StructuredModelClient
from sourcepilot.ai.comparison_advice import analyze_comparison_advice
from sourcepilot.ai.comparison_advice_eval import (
    load_cases,
    recorded_advice,
    scenario_snapshot,
    score_case,
)
from sourcepilot.ai.tradeoff_analysis import TradeoffNotReadyError, TradeoffUnavailableError
from sourcepilot.ai.tradeoff_analysis_eval_live import _fixture_tool
from sourcepilot.persistence.database import application_session_factory
from sourcepilot.persistence.models import Project


def run_scenarios(session: Session, project: Project,
                  client: StructuredModelClient) -> list[dict[str, Any]]:
    results = []
    for case in load_cases():
        if not case["expected_grounded"]:
            continue  # Negative controls test the scorer, not expected provider behavior.
        snapshot = scenario_snapshot(case)
        assert snapshot.snapshot_id is not None
        with (patch("sourcepilot.ai.tradeoff_analysis._current_snapshot", return_value=snapshot),
              patch("sourcepilot.ai.comparison_advice.check_advice_scope"),
              patch("sourcepilot.ai.tradeoff_analysis._tool_output",
                    side_effect=lambda _session, runtime, name, arguments, bound=snapshot:
                    _fixture_tool(bound, runtime, name, arguments))):
            try:
                response = analyze_comparison_advice(
                    session, demo_session_id=project.demo_session_id, project_id=project.id,
                    snapshot_id=snapshot.snapshot_id, client_factory=lambda: client,
                )
            except (TradeoffNotReadyError, TradeoffUnavailableError, ModelProviderError) as error:
                results.append({"id": case["id"], "passed": False, "error": type(error).__name__})
                continue
        results.append({"id": case["id"], "passed": score_case(case, response, snapshot),
                        "run_id": str(response.run_id)})
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run explicit live comparison-advice evals over synthetic inputs.")
    parser.add_argument("--project-id", type=UUID, required=True)
    args = parser.parse_args()
    cases = load_cases()
    controls = sum(score_case(case, recorded_advice(case), scenario_snapshot(case))
                   is case["expected_grounded"] for case in cases)
    print(f"Scorer controls: {controls}/{len(cases)} matched expectations")
    client = OpenAIResponsesClient.from_environment()
    from sourcepilot.comparison.execution import comparison_cli_lifecycle

    with comparison_cli_lifecycle(), application_session_factory()() as session:
        project = session.get(Project, args.project_id)
        if project is None:
            raise RuntimeError("The supplied project does not exist.")
        results = run_scenarios(session, project, client)
    for result in results:
        print(result)
    if controls != len(cases) or not all(result["passed"] for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
