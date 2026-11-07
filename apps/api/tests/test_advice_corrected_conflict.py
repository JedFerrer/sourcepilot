"""Provider-free regression against the unchanged retained PDF acceptance case."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from sourcepilot.ai.analyst_tools import ComparisonSnapshotResult
from sourcepilot.ai.comparison_advice import ComparisonAdvice, validate_advice
from sourcepilot.comparison.advice_facts import build_catalogue, numeric_value, valid_relationship
from sourcepilot.comparison.advice_rendering import render_advice, render_fact

FIXTURE = Path(__file__).parent / "fixtures/comparison_advice"


def retained_pdf():
    return ComparisonSnapshotResult.model_validate_json(
        (FIXTURE / "corrected-pdf-snapshot.json").read_bytes(),
    )


@pytest.mark.parametrize("suggest", [False, True])
def test_retained_correction_survives_conflict_rendering_and_public_validation(suggest):
    snapshot = retained_pdf()
    original = snapshot.model_dump_json()
    assert snapshot.comparison_payload is not None
    catalogue = build_catalogue(str(snapshot.snapshot_id), snapshot.comparison_payload)
    price = next(f for f in catalogue.facts.values()
                 if f.field_key == "unit_price" and f.source.get("origin") == "USER_CORRECTED")
    saved = json.loads((FIXTURE / "corrected-pdf-confirmed.json").read_bytes())
    assert saved["values"]["unit_price"]["current_value"] == price.value == "4.50"
    assert price.source["ai_extracted_value"] == "4.22"
    currency = catalogue.quote(price, "currency")
    assert currency and price.state == currency.state == "CONFLICT"
    assert currency.value is None
    assert {e["value"] for e in currency.source["evidence"]} == {"USD", "EUR"}
    reason = next(f for f in catalogue.facts.values()
                  if f.supplier_id == price.supplier_id and f.state == "MEETS")
    output = render_advice(
        catalogue, verification_actions=[("RESOLVE_CONFLICT", price.id)],
        suggestion_id=price.supplier_id if suggest else None,
        reason_fact_ids=[reason.id] if suggest else [],
    )
    validate_advice(ComparisonAdvice.model_validate(output), snapshot)
    point = render_fact(catalogue, price)
    assert "Current user-corrected amount: 4.50 (no currency assigned)." in point["text"]
    assert f"{price.supplier_name} unit price is CONFLICT." in point["text"]
    assert f"{price.supplier_name} currency is CONFLICT." in point["text"]
    assert "4.22" not in point["text"]
    assert "USD" not in point["text"] and "EUR" not in point["text"]
    assert point["quote_fields"] == [
        {"quote_id": price.quote_id, "field_key": "unit_price"},
        {"quote_id": price.quote_id, "field_key": "currency"},
    ]
    assert point["evidence_ids"] == list(dict.fromkeys([*price.evidence_ids, *currency.evidence_ids]))
    assert point in output["analysis"]["important_conflicts"]
    action = next(p for p in output["analysis"]["key_tradeoffs"] if "Reconcile" in p["text"])
    assert point["text"] in action["text"]
    assert action["quote_fields"] == point["quote_fields"]
    assert action["evidence_ids"] == point["evidence_ids"]
    if suggest:
        assert point in output["suggestion"]["uncertainties"]
    text = " ".join(p["text"] for points in output["analysis"].values() for p in points)
    assert "No currency conversion has been performed" in text
    assert "Do not treat these prices as equivalent quantities" in text
    assert "2000" in text and "5000" in text
    other = next(f for f in catalogue.facts.values()
                 if f.field_key == "unit_price" and f.supplier_id != price.supplier_id)
    assert numeric_value(price) is None
    assert not valid_relationship(catalogue, "SAME_QUOTE_FIELD", [price.id, other.id])
    assert snapshot.model_dump_json() == original


@pytest.mark.parametrize("value", [None, True, "NaN", "Infinity", "-1", "invented prose"])
def test_conflicting_correction_does_not_render_invalid_amounts(value):
    snapshot = retained_pdf()
    assert snapshot.comparison_payload is not None
    payload: Any = snapshot.comparison_payload
    for supplier in payload["suppliers"]:
        for field in supplier["quote_fields"]:
            if field["field_key"] == "unit_price" and field["origin"] == "USER_CORRECTED":
                field["current_value"] = value
    catalogue = build_catalogue(str(snapshot.snapshot_id), snapshot.comparison_payload)
    price = next(f for f in catalogue.facts.values()
                 if f.field_key == "unit_price" and f.source.get("origin") == "USER_CORRECTED")
    assert render_fact(catalogue, price)["text"] == f"{price.supplier_name} unit price is CONFLICT."


def test_conflict_display_exception_does_not_promote_other_states_or_origins():
    snapshot = retained_pdf()
    assert snapshot.comparison_payload is not None
    catalogue = build_catalogue(str(snapshot.snapshot_id), snapshot.comparison_payload)
    price = next(f for f in catalogue.facts.values()
                 if f.field_key == "unit_price" and f.source.get("origin") == "USER_CORRECTED")
    for origin in ("AI_EXTRACTED", "USER_ENTERED"):
        source = {**price.source, "origin": origin}
        fact = replace(price, source_json=json.dumps(source))
        assert render_fact(catalogue, fact)["text"] == f"{price.supplier_name} unit price is CONFLICT."
    unknown = replace(price, state="UNKNOWN")
    assert render_fact(catalogue, unknown)["text"] == f"{price.supplier_name} unit price is UNKNOWN."
    zero = replace(price, source_json=json.dumps({**price.source, "current_value": "0.00"}))
    assert "amount: 0.00 (no currency assigned)" in render_fact(catalogue, zero)["text"]
    assert numeric_value(zero) is None
