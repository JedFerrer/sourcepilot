"""Combined advice facts preserve the bound snapshot and source distinctions."""
import json
from pathlib import Path
from typing import Any

import pytest

from sourcepilot.ai.analyst_tools import ComparisonSnapshotResult
from sourcepilot.ai.comparison_context import comparison_context
from sourcepilot.comparison.advice_facts import build_catalogue, catalogue_index, valid_relationship


def retained_snapshot() -> ComparisonSnapshotResult:
    path = Path(__file__).parents[1] / "evals/comparison_advice/retained_failure_cases.json"
    return ComparisonSnapshotResult.model_validate(json.loads(path.read_text())["snapshot"])


def retained_catalogue():
    snapshot = retained_snapshot()
    assert snapshot.comparison_payload is not None
    return build_catalogue(str(snapshot.snapshot_id), snapshot.comparison_payload)


def test_catalogue_is_immutable_and_index_resolves_original_facts():
    snapshot = retained_snapshot()
    original = snapshot.model_dump_json()
    catalogue = retained_catalogue()
    context = comparison_context(snapshot)
    index = catalogue_index(context)
    assert set(index) == set(catalogue.facts)
    for key, location in index.items():
        supplier = context["comparison_payload"]["suppliers"][location["supplier_index"]]
        fact = catalogue.facts[key]
        assert fact.supplier_id == supplier["supplier_id"]
        if "result_index" in location:
            assert supplier["evaluation"]["results"][location["result_index"]]["status"] == fact.state
        else:
            field = supplier["quote_fields"][location["quote_field_index"]]
            assert fact.field_key == field["field_key"]
            assert fact.value == field.get("current_value")
    with pytest.raises(TypeError):
        catalogue.facts["bad"] = next(iter(catalogue.facts.values()))  # type: ignore[index]
    view = next(iter(catalogue.facts.values())).source
    view.clear()
    assert next(iter(catalogue.facts.values())).source
    assert snapshot.model_dump_json() == original


def test_required_state_is_not_missing_quote_certification():
    catalogue = retained_catalogue()
    sunrise = [f for f in catalogue.facts.values() if f.supplier_name == "Sunrise Textile Lab"]
    assert next(f for f in sunrise if f.requirement_id and f.source["requirement"]["kind"] == "CERTIFICATION").state == "CONFLICT"
    assert next(f for f in sunrise if f.field_key == "certifications").state == "UNKNOWN"


@pytest.mark.parametrize("mode", ["different", "missing", "quantity", "overlap", "foreign"])
def test_price_time_relations_require_actual_compatible_tradeoff(mode: str):
    snapshot = retained_snapshot()
    payload: Any = snapshot.comparison_payload
    a, b = payload["suppliers"][2], payload["suppliers"][1]
    ids = [f"Q:{s['quote_id']}:{field}" for s in [a,b] for field in ["unit_price", "production_lead_time"]]
    catalogue = build_catalogue(str(snapshot.snapshot_id), payload)
    assert valid_relationship(catalogue, "PRICE_AND_PRODUCTION", ids)
    for field in b["quote_fields"]:
        if mode in {"different", "missing"} and field["field_key"] == "currency":
            field["current_value"] = "EUR" if mode == "different" else None
        if mode == "quantity" and field["field_key"] == "quoted_quantity":
            field["current_value"] = 5000
        if mode == "overlap" and field["field_key"] == "production_lead_time":
            field["current_value"] = "30-40 days"
    if mode == "foreign":
        ids[0] = "Q:outside:unit_price"
    assert not valid_relationship(build_catalogue(str(snapshot.snapshot_id), payload), "PRICE_AND_PRODUCTION", ids)
