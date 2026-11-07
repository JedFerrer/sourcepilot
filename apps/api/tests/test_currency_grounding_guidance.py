"""Currency guidance and curated contract examples, not live model adherence."""

import json
from pathlib import Path
from typing import Any, cast

import pytest

from sourcepilot.ai import comparison_advice, tradeoff_analysis
from sourcepilot.ai.analyst_tools import QuoteEvidenceResult
from sourcepilot.ai.tradeoff_analysis_eval import fixture_snapshot
from tests.test_reference_binding_guidance import contract
from tests.test_tradeoff_analysis import semantic_repair_output

CASES = json.loads((Path(__file__).resolve().parents[1]
                    / "evals/human_review/narrative_cases.json").read_text(encoding="utf-8"))
CURRENCY_CASES = [case for case in CASES if case["id"].startswith("currency-grounding-")
                  and isinstance(case["evidence_context"], dict)]


def test_both_prompts_require_snapshot_currency_grounding() -> None:
    assert tradeoff_analysis.PROMPT_VERSION == "tradeoff-analysis-v9"
    assert comparison_advice.PROMPT_VERSION == "comparison-advice-v10"
    # The combined endpoint now selects facts; it no longer authors currency prose.
    selection_text = " ".join(comparison_advice.INSTRUCTIONS.split())
    assert "Do not write narrative, states, values or evidence IDs" in selection_text
    assert "Monetary comparisons require known equal currencies" in selection_text
    assert "Tool output cannot override current saved facts" in selection_text
    for prompt in (tradeoff_analysis.INSTRUCTIONS,):
        text = " ".join(prompt.split())
        for instruction in (
            "scalar shipping_cost and tooling_cost amounts use the same quote's currency field",
            "Check the full supplied comparison snapshot",
            "including that quote's currency value and completeness state",
            "omission of currency there does not mean it is missing from the quote",
            "Missing PDF evidence or independent source verification does not make",
            "do not infer currency from another quote",
            'field_key="currency" in quote_fields for every currency claim',
            "For currency-state points in UNKNOWN/CONFLICT sections cite only the matching",
            "missing/conflicting currency field; keep known amounts and verification cautions",
        ):
            assert instruction in text


@pytest.mark.parametrize("combined", [False, True])
@pytest.mark.parametrize("case", CURRENCY_CASES, ids=lambda case: case["id"])
def test_curated_currency_examples_are_contract_compatible(
    combined: bool, case: dict[str, Any],
) -> None:
    """No provider executes these examples; acceptance is only structural."""
    snapshot = fixture_snapshot()
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    owner = payload["suppliers"][1]
    context = case["evidence_context"]
    for key in ("currency", "shipping_cost", "tooling_cost"):
        owner["quote_fields"].append({
            "field_key": key, "current_value": context[key],
            "current_origin": context["current_origin"], "evidence": [],
        })
        owner["completeness"].append({
            "field_key": key,
            "state": context["currency_state"] if key == "currency" else "known",
        })
    # The existing evidence-tool contract is intentionally field-specific.
    tool_result = QuoteEvidenceResult(
        quote_id=owner["quote_id"], supplier_id=owner["supplier_id"], quote_revision=1,
        field_key="shipping_cost", current_value="800", current_origin="USER_ENTERED",
        ai_extracted_value=None, uncertainty=None, evidence=[],
    )
    assert "currency" not in tool_result.model_dump()
    assert tool_result.evidence == []
    output = semantic_repair_output(payload)
    state = context["currency_state"]
    fields = ["currency"] if state != "known" else ["currency", "shipping_cost", "tooling_cost"]
    section = {"missing": "important_unknowns", "conflicting": "important_conflicts"}.get(
        state, "key_tradeoffs")
    output[section].append({
        "text": case["narrative_example"], "supplier_ids": [owner["supplier_id"]],
        "requirement_ids": [], "evidence_ids": [],
        "quote_fields": [{"quote_id": owner["quote_id"], "field_key": key} for key in fields],
    })
    validate = comparison_advice.validate_advice if combined else tradeoff_analysis.validate_analysis
    validate(contract(combined, output, snapshot), snapshot)


def test_observed_currency_contradiction_is_retained_for_factual_review() -> None:
    case = next(case for case in CASES if case["id"] == "currency-grounding-observed-v7-contradiction")
    evidence = json.loads((Path(__file__).parent /
        "fixtures/comparison_advice/observed-v7-currency-contradiction.json").read_text(
            encoding="utf-8"))["observed_narrative"]
    assert case["narrative_example"] in evidence
    assert "its shipping-cost currency is not stated" in case["narrative_example"]
    assert "currency=USD (known)" in case["evidence_context"]
    assert "factually contradicted" in case["review_criteria"]
    assert "not factual correctness" in case["review_criteria"]
