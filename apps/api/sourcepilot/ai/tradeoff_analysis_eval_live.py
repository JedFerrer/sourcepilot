"""Opt-in real-model M4-U6 eval; never invoked by pytest or CI."""

from __future__ import annotations

import argparse
from copy import deepcopy
from typing import Any, cast
from unittest.mock import patch
from uuid import UUID

from sourcepilot.ai.analyst_tools import AnalystToolRuntime, ComparisonSnapshotResult
from sourcepilot.ai.client import ModelProviderError, OpenAIResponsesClient
from sourcepilot.ai.tradeoff_analysis import (
    TradeoffNotReadyError,
    TradeoffUnavailableError,
    analyze_tradeoffs,
)
from sourcepilot.ai.tradeoff_analysis_eval import (
    fixture_snapshot,
    load_cases,
    recorded_analysis,
    score_case,
)
from sourcepilot.persistence.database import application_session_factory
from sourcepilot.persistence.models import Project


def _fixture_tool(snapshot: ComparisonSnapshotResult, runtime: AnalystToolRuntime,
                  name: str, arguments: object) -> dict[str, Any]:
    runtime.check_budget()
    payload = snapshot.comparison_payload
    assert payload is not None
    suppliers = cast(list[dict[str, Any]], payload["suppliers"])
    if name == "get_comparison_snapshot" and arguments == {}:
        result = snapshot.model_dump(mode="json")
    elif isinstance(arguments, dict) and name in {"get_supplier_snapshot", "get_supplier_evidence"}:
        if set(arguments) != ({"supplier_id"} if name == "get_supplier_snapshot"
                              else {"supplier_id", "claim_keys"}):
            raise ValueError("Invalid supplier tool arguments.")
        if UUID(arguments["supplier_id"]) not in runtime.context.permitted_supplier_ids:
            raise ValueError("Supplier is outside the comparison.")
        supplier = next(item for item in suppliers
                        if item["supplier_id"] == arguments["supplier_id"])
        result = supplier if name == "get_supplier_snapshot" else supplier["supplier_facts"]
    elif isinstance(arguments, dict) and name == "get_quote_evidence":
        if set(arguments) != {"quote_id", "field_key"}:
            raise ValueError("Invalid quote tool arguments.")
        if UUID(arguments["quote_id"]) not in runtime.context.permitted_quote_ids:
            raise ValueError("Quote is outside the comparison.")
        supplier = next(item for item in suppliers
                        if item["quote_id"] == arguments["quote_id"])
        field = next(item for item in supplier["quote_fields"]
                     if item["field_key"] == arguments["field_key"])
        result = {"quote_id": arguments["quote_id"], "supplier_id": supplier["supplier_id"],
                  **field}
    else:
        raise ValueError("Unrecognized fixture tool call.")
    runtime.record(name, None, None, "SUCCESS")
    return result


def live_scenarios() -> list[tuple[dict[str, Any], ComparisonSnapshotResult]]:
    """Distinct comparison inputs for actual analyst runs, separate from scorer controls."""
    scenarios: list[tuple[dict[str, Any], ComparisonSnapshotResult]] = []
    for index, (topic, price, days) in enumerate((
        ("meaningful tradeoff", "3.90", 38),
        ("required failure", "3.70", 42),
        ("user correction", "4.00", 35),
    ), start=1):
        snapshot = deepcopy(fixture_snapshot())
        snapshot.snapshot_id = UUID(f"55555555-5555-5555-5555-55555555555{index}")
        assert snapshot.comparison_payload is not None
        payload = cast(dict[str, Any], snapshot.comparison_payload)
        supplier_b = payload["suppliers"][1]
        supplier_b["quote_fields"][0]["current_value"] = price
        supplier_b["quote_fields"][1]["current_value"] = days
        scenarios.append(({"id": f"live-{index}-{topic.replace(' ', '-')}",
                           "topic": topic, "expected_grounded": True}, snapshot))
    return scenarios


def matches_expectation(case: dict[str, Any], grounded: bool) -> bool:
    return grounded is case["expected_grounded"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run opt-in real-model tradeoff eval cases.")
    parser.add_argument("--project-id", required=True, type=UUID)
    args = parser.parse_args()
    controls = load_cases()
    control_passed = sum(matches_expectation(case, score_case(
        case, recorded_analysis(case), fixture_snapshot())) for case in controls)
    print(f"Scorer regression controls: {control_passed}/{len(controls)} matched expectations")
    client = OpenAIResponsesClient.from_environment()
    scenarios = live_scenarios()
    passed = 0
    with application_session_factory()() as session:
        project = session.get(Project, args.project_id)
        if project is None:
            raise RuntimeError("The supplied project does not exist.")
        for case, snapshot in scenarios:
            with (patch("sourcepilot.ai.tradeoff_analysis._current_snapshot",
                        return_value=snapshot),
                  patch("sourcepilot.ai.tradeoff_analysis._tool_output",
                        side_effect=lambda _session, runtime, name, arguments, bound=snapshot:
                        _fixture_tool(bound, runtime, name, arguments))):
                try:
                    result = analyze_tradeoffs(
                        session, demo_session_id=project.demo_session_id, project_id=project.id,
                        client_factory=lambda: client,
                    )
                except (TradeoffNotReadyError, TradeoffUnavailableError, ModelProviderError) as error:
                    print(f"{case['id']}: failed ({type(error).__name__})")
                    continue
            grounded = score_case(case, result.analysis, snapshot)
            matched = matches_expectation(case, grounded)
            passed += matched
            print(f"{case['id']}: {'pass' if matched else 'fail'} "
                  f"(grounded={grounded}, expected={case['expected_grounded']}, "
                  f"AIRun {result.run_id})")
    print(f"Live analyst scenarios: {passed}/{len(scenarios)} matched expectations")


if __name__ == "__main__":
    main()
