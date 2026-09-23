"""Small version-controlled brief extraction dataset and deterministic scorer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sourcepilot.ai.brief_interpreter import ExtractedBrief

CASES_PATH = Path(__file__).resolve().parents[2] / "evals" / "brief" / "cases.json"
ABSENT_FIELDS: dict[str, Any] = {
    "product_name": None,
    "category": None,
    "quantity": None,
    "destination": None,
    "delivery_target": None,
    "target_unit_price": None,
    "attributes": [],
    "requirements": [],
    "ambiguities": [],
}


def load_cases() -> list[dict[str, Any]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def score_case(
    result: ExtractedBrief | None, expected: dict[str, Any], *, partial: bool = False
) -> tuple[int, int]:
    """Score every field unless the fixture explicitly requests partial scoring."""
    assertions = expected if partial else {**ABSENT_FIELDS, **expected}
    if result is None:
        return 0, len(assertions)
    actual = result.model_dump(mode="json")
    matches = sum(actual[key] == value for key, value in assertions.items())
    return matches, len(assertions)
