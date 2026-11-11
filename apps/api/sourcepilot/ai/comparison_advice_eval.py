"""Versioned synthetic advice scenarios and scoring of produced structured results."""

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from sourcepilot.ai.analyst_tools import ComparisonSnapshotResult
from sourcepilot.ai.comparison_advice import ComparisonAdvice, validate_advice
from sourcepilot.ai.tradeoff_analysis_eval import fixture_snapshot
from sourcepilot.ai.tradeoff_analysis_eval import score_case as score_tradeoffs

CASES_PATH = Path(__file__).resolve().parents[2] / "evals" / "comparison_advice" / "cases.json"
OUTPUTS_PATH = CASES_PATH.with_name("model_outputs.json")


def load_cases() -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], json.loads(CASES_PATH.read_text(encoding="utf-8")))


def scenario_snapshot(case: dict[str, Any]) -> ComparisonSnapshotResult:
    snapshot = deepcopy(fixture_snapshot())
    snapshot.snapshot_id = UUID(case["snapshot_id"])
    snapshot.brief_revision = case["brief_revision"]
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    if "payload" in case:
        snapshot.comparison_payload = deepcopy(case["payload"])
        return snapshot
    for supplier in payload["suppliers"]:
        for result in supplier["evaluation"]["results"]:
            override = case.get("states", {}).get(supplier["supplier_id"], {}).get(result["requirement_id"])
            if override is not None:
                result["status"] = override
        for field in supplier["quote_fields"]:
            override = case.get("fields", {}).get(supplier["supplier_id"], {}).get(field["field_key"])
            if override is not None:
                field["current_value"] = override
            if field["field_key"] == "unit_price":
                field["current_value"] = case["prices"][supplier["supplier_id"]]
    payload["price_comparable"] = case["price_comparable"]
    return snapshot


def recorded_advice(case: dict[str, Any]) -> ComparisonAdvice:
    outputs = json.loads(OUTPUTS_PATH.read_text(encoding="utf-8"))
    return ComparisonAdvice.model_validate(outputs[case["id"]])


def score_case(case: dict[str, Any], advice: ComparisonAdvice,
               snapshot: ComparisonSnapshotResult, *, check_price: bool = True,
               check_lead: bool = True) -> bool:
    """Check structured advice and recognized narrative hazards, not all prose meaning."""
    try:
        validate_advice(advice, snapshot)
        # Offline narrative checks reuse the M4-U6 evaluator, never runtime parsing.
        joined = advice.analysis.model_copy(deep=True)
        joined.supplier_summaries.extend(advice.suggestion.supporting_reasons
                                        + advice.suggestion.tradeoffs + advice.suggestion.uncertainties)
        if not score_tradeoffs({"topic": "references-only"}, joined, snapshot,
                               check_price=check_price, check_lead=check_lead):
            return False
    except (ValueError, KeyError, StopIteration):
        return False
    selected = str(advice.suggestion.supplier_id) if advice.suggestion.supplier_id else None
    all_text = " ".join(point.text for point in joined.supplier_summaries + joined.key_tradeoffs
                        + joined.important_unknowns + joined.important_conflicts)
    if re.search(r"\bis (?:objectively |definitively )?(?:the )?best supplier\b",
                 all_text, re.IGNORECASE):
        return False
    if selected not in case.get("live_allowed_supplier_ids", case["allowed_supplier_ids"]):
        return False
    if selected:
        payload = cast(dict[str, Any], snapshot.comparison_payload)
        requirements = {item["id"]: item for item in payload["brief"]["requirements"]}
        supplier = next(item for item in payload["suppliers"] if item["supplier_id"] == selected)
        for result in supplier["evaluation"]["results"]:
            requirement_id = result["requirement_id"]
            if requirement_id is None or requirements[requirement_id]["importance"] != "REQUIRED":
                continue
            state = result["status"]
            section = (advice.suggestion.tradeoffs if state == "DOES_NOT_MEET"
                       else advice.suggestion.uncertainties)
            if state != "MEETS":
                pattern = {"DOES_NOT_MEET": r"does not meet|\bDOES_NOT_MEET\b|fails|failure",
                           "UNKNOWN": r"unknown|unverified|missing",
                           "CONFLICT": r"conflict"}[state]
                if not any(UUID(requirement_id) in point.requirement_ids
                           and UUID(selected) in point.supplier_ids
                           and re.search(pattern, point.text, re.IGNORECASE) for point in section):
                    return False
    return True
