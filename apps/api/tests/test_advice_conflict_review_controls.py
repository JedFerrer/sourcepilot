"""Independent review controls; in-memory copies only, no database/provider."""

import json
from dataclasses import replace

from sourcepilot.ai.advice_selection import AdviceSelectionTask
from sourcepilot.comparison.advice_facts import build_catalogue, numeric_value
from sourcepilot.comparison.advice_rendering import _render_verification, render_fact
from sourcepilot.comparison.validation import ComparisonRejection
from tests.test_advice_corrected_conflict import retained_pdf


def test_other_conflicts_and_support_remain_rejected() -> None:
    snapshot = retained_pdf()
    assert snapshot.comparison_payload is not None
    catalogue = build_catalogue(str(snapshot.snapshot_id), snapshot.comparison_payload)
    price = next(
        f
        for f in catalogue.facts.values()
        if f.field_key == "unit_price" and f.source.get("origin") == "USER_CORRECTED"
    )
    checks = []
    for key in (
        "currency",
        "shipping_cost",
        "tooling_cost",
        "production_lead_time",
        "quoted_quantity",
        "moq",
    ):
        original = catalogue.quote(price, key)
        assert original is not None
        fact = replace(
            original,
            state="CONFLICT",
            source_json=json.dumps(
                {**original.source, "origin": "USER_CORRECTED", "current_value": "0.00"}
            ),
        )
        point = render_fact(catalogue, fact)
        assert point["text"] == f"{fact.supplier_name} {key.replace('_', ' ')} is CONFLICT."
        assert point["quote_fields"] == [{"quote_id": fact.quote_id, "field_key": key}]
        assert point["evidence_ids"] == list(fact.evidence_ids)
        action = _render_verification(catalogue, "RESOLVE_CONFLICT", fact)
        assert (
            action["text"]
            == point["text"]
            + f" Reconcile the source records for {fact.supplier_name}'s {key.replace('_', ' ')} before proceeding."
        )
        assert action["quote_fields"] == point["quote_fields"]
        assert numeric_value(fact) is None
        checks.append(key)
    task = AdviceSelectionTask(snapshot)
    draft = {
        "version": "comparison-selection-v1",
        "snapshot_id": str(snapshot.snapshot_id),
        "highlights": [price.id],
        "tradeoffs": [],
        "verification_actions": [],
        "suggestion": {
            "supplier_id": price.supplier_id,
            "reason_fact_ids": [price.id],
            "no_suggestion_reason": None,
        },
    }
    try:
        task.accept(json.dumps(draft))
    except ComparisonRejection:
        pass
    else:
        raise AssertionError("Conflicting amount became eligible support")
