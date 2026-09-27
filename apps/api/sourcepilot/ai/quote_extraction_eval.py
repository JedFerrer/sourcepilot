"""Versioned, offline quote-extraction cases and deterministic scoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sourcepilot.ai.quote_extractor import QuoteExtraction
from sourcepilot.quotes.domain import QUOTE_FIELD_KEYS, QUOTE_INTEGER_FIELDS, QUOTE_MONEY_FIELDS

EVAL_DIRECTORY = Path(__file__).resolve().parents[2] / "evals" / "quote_extraction"


def load_cases() -> list[dict[str, Any]]:
    return json.loads((EVAL_DIRECTORY / "cases.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def load_recorded_outputs() -> dict[str, dict[str, Any]]:
    return json.loads((EVAL_DIRECTORY / "model_outputs.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def score_case(result: QuoteExtraction, case: dict[str, Any]) -> dict[str, float]:
    """Score all fields, including unspecified fields as explicitly unknown."""
    actual = result.model_dump(mode="json")["fields"]
    known = case["known"]
    unknown_sources = case["unknown_sources"]
    conflicts = case["conflicts"]
    field_matches = source_matches = unknown_matches = conflict_matches = 0
    numeric_matches = currency_matches = 0
    numeric_total = sum(key in QUOTE_INTEGER_FIELDS | QUOTE_MONEY_FIELDS for key in known)
    currency_total = int("currency" in known)
    invented = 0
    for key in QUOTE_FIELD_KEYS:
        field = actual[key]
        if key in known:
            value, references = known[key]
            field_match = field["state"] == "KNOWN" and field["extracted_value"] == value
            source_match = field["source_block_ids"] == references
            if key in QUOTE_INTEGER_FIELDS | QUOTE_MONEY_FIELDS:
                numeric_matches += int(field_match)
            if key == "currency":
                currency_matches += int(field_match)
        elif key in conflicts:
            alternatives = conflicts[key]
            field_match = field["state"] == "CONFLICT" and field["extracted_value"] is None
            conflict_match = field_match and [
                [item["value"], item["source_block_ids"]] for item in field["conflicting_values"]
            ] == alternatives
            conflict_matches += int(conflict_match)
            source_match = field["source_block_ids"] == [
                reference for _, references in alternatives for reference in references
            ]
        else:
            field_match = field["state"] == "UNKNOWN" and field["extracted_value"] is None
            unknown_matches += int(field_match)
            source_match = field["source_block_ids"] == unknown_sources.get(key, [])
            invented += int(field["state"] == "KNOWN")
        field_matches += int(field_match)
        source_matches += int(source_match)
    unknown_total = len(QUOTE_FIELD_KEYS) - len(known) - len(conflicts)
    return {
        "field_accuracy": field_matches / len(QUOTE_FIELD_KEYS),
        "numeric_accuracy": numeric_matches / numeric_total if numeric_total else 1.0,
        "currency_accuracy": currency_matches / currency_total if currency_total else 1.0,
        "unknown_detection": unknown_matches / unknown_total if unknown_total else 1.0,
        "conflict_detection": conflict_matches / len(conflicts) if conflicts else 1.0,
        "source_block_accuracy": source_matches / len(QUOTE_FIELD_KEYS),
        "hallucination_rate": invented / unknown_total if unknown_total else 0.0,
    }
