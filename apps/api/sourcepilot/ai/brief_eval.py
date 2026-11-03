"""Small version-controlled brief extraction dataset and deterministic scorer."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
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
    result: ExtractedBrief | None,
    expected: dict[str, Any],
    *,
    partial: bool = False,
    aliases: dict[str, list[str]] | None = None,
) -> tuple[int, int]:
    """Score every field unless the fixture explicitly requests partial scoring."""
    assertions = expected if partial else {**ABSENT_FIELDS, **expected}
    if result is None:
        return 0, len(assertions)
    actual = result.model_dump(mode="json")
    matches = sum(
        field_matches(key, actual[key], value, aliases or {}) for key, value in assertions.items()
    )
    return matches, len(assertions)


def field_matches(key: str, actual: Any, expected: Any, aliases: dict[str, list[str]]) -> bool:
    """Only explicit aliases, decimal equivalence and unordered structured lists."""
    if key == "target_unit_price" and actual is not None and expected is not None:
        return Decimal(actual) == Decimal(expected)
    if key in {"requirements", "attributes"}:
        def comparable(value: dict[str, Any]) -> dict[str, Any]:
            value = json.loads(json.dumps(value))
            if key == "requirements" and value.get("kind") == "UNIT_PRICE":
                amount = value.get("expected_value", {}).get("amount")
                if amount is not None:
                    try:
                        value["expected_value"]["amount"] = str(Decimal(str(amount)).normalize())
                    except InvalidOperation:
                        pass
            return value

        encode = lambda values: sorted(json.dumps(comparable(value), sort_keys=True) for value in values)
        return encode(actual) == encode(expected)
    if key == "ambiguities" and key in aliases:
        if not isinstance(actual, list) or not isinstance(expected, list):
            return False
        accepted = {value.casefold().strip() for value in [*expected, *aliases[key]]}
        return len(actual) == len(expected) and all(
            value.casefold().strip() in accepted for value in actual
        )
    if key in aliases and isinstance(actual, str):
        return actual.casefold().strip() in {
            str(expected).casefold().strip(),
            *(value.casefold().strip() for value in aliases[key]),
        }
    return actual == expected
