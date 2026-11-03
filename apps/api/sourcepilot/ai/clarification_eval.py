"""Version-controlled clarification cases and small deterministic quality measures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sourcepilot.ai.clarification import MAX_QUESTIONS, ClarificationQuestion
from sourcepilot.briefs.readiness import (
    ReadinessRequirement,
    evaluate_brief_readiness,
)

CASES_PATH = Path(__file__).resolve().parents[2] / "evals" / "clarification" / "cases.json"
WORDING_HEURISTICS = {
    "clarity_rate": "Fraction of questions ending in '?' with at least three words.",
    "conciseness_rate": "Fraction of questions with at most 120 characters.",
}


def load_cases() -> list[dict[str, Any]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def readiness_keys(case: dict[str, Any]) -> list[str]:
    brief = case["brief"]
    readiness = evaluate_brief_readiness(
        product_name=brief["product_name"],
        category=brief["category"],
        quantity=brief["quantity"],
        destination=brief["destination"],
        delivery_target=brief["delivery_target"],
        requirements=tuple(
            ReadinessRequirement(kind=item["kind"], expected_value=item["expected_value"])
            for item in brief["requirements"]
        ),
    )
    return [field.field_key for field in readiness.missing_fields[:MAX_QUESTIONS]]


def score_questions(
    questions: list[ClarificationQuestion], expected_keys: list[str]
) -> dict[str, float]:
    """Score field coverage and lightweight wording signals for initial evals."""
    keys = [item.field_key for item in questions]
    total = len(questions)
    return {
        "missing_field_coverage": 1.0 if not expected_keys else len(set(keys) & set(expected_keys)) / len(expected_keys),
        "redundant_question_rate": 0.0 if not total else (total - len(set(keys))) / total,
        "irrelevant_question_rate": 0.0 if not total else sum(key not in expected_keys for key in keys) / total,
        "clarity_rate": 1.0 if not total else sum(item.question.endswith("?") and len(item.question.split()) >= 3 for item in questions) / total,
        "conciseness_rate": 1.0 if not total else sum(len(item.question) <= 120 for item in questions) / total,
    }
