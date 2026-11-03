import json

import pytest

from sourcepilot.ai.brief_eval import CASES_PATH, load_cases, score_case
from sourcepilot.ai.brief_interpreter import ExtractedBrief


def test_release_brief_cases_validate_and_match_expected_fields() -> None:
    cases = load_cases()
    outputs = json.loads((CASES_PATH.parent / "model_outputs.json").read_text(encoding="utf-8"))

    assert len(cases) == len(outputs) == 24
    assert len({case["id"] for case in cases}) == 24
    for case in cases:
        result = ExtractedBrief.model_validate(outputs[case["id"]])
        matches, fields = score_case(result, case["expected"], partial=case.get("partial", False))
        assert fields == 9
        assert matches == fields, case["id"]


def test_eval_scoring_catches_a_hallucinated_missing_field() -> None:
    outputs = json.loads((CASES_PATH.parent / "model_outputs.json").read_text(encoding="utf-8"))
    result = ExtractedBrief.model_validate({**outputs["non-invention"], "destination": "Sydney"})

    expected = next(case["expected"] for case in load_cases() if case["id"] == "non-invention")
    matches, fields = score_case(result, expected)

    assert matches == fields - 1


def test_eval_scoring_catches_unexpected_requirements_and_attributes() -> None:
    outputs = json.loads((CASES_PATH.parent / "model_outputs.json").read_text(encoding="utf-8"))
    expected = next(case["expected"] for case in load_cases() if case["id"] == "missing-quantity")
    baseline = outputs["missing-quantity"]

    for unexpected in (
        {"requirements": [{"kind": "MATERIAL", "importance": None, "expected_value": {"value": "recycled"}}]},
        {"attributes": [{"subject": "COLOR", "text": "blue"}]},
        {"target_unit_price": "5"},
    ):
        result = ExtractedBrief.model_validate({**baseline, **unexpected})
        assert score_case(result, expected) == (8, 9)


def test_eval_partial_assertions_require_explicit_opt_in() -> None:
    outputs = json.loads((CASES_PATH.parent / "model_outputs.json").read_text(encoding="utf-8"))
    result = ExtractedBrief.model_validate(outputs["complete-demo"])

    assert score_case(result, {"quantity": 2000}) == (3, 9)
    assert score_case(result, {"quantity": 2000}, partial=True) == (1, 1)


def test_failed_live_result_counts_as_zero_of_all_expected_fields() -> None:
    expected = next(case["expected"] for case in load_cases() if case["id"] == "missing-quantity")

    assert score_case(None, expected) == (0, 9)


@pytest.mark.parametrize("case_id,change", [
    ("production-limit", {"requirements": [{"kind": "PRODUCTION_LEAD_TIME",
        "importance": None, "expected_value": {"max_days": 30}}]}),
    ("production-limit", {"requirements": [{"kind": "PRODUCTION_LEAD_TIME",
        "importance": "REQUIRED", "expected_value": {"max_days": 31}}]}),
    ("explicit-moq", {"quantity": 500}),
    ("explicit-moq", {"requirements": [{"kind": "MOQ", "importance": "PREFERRED",
        "expected_value": {"quantity": 500}}]}),
    ("price-currency", {"target_unit_price": None}),
    ("price-currency", {"requirements": [{"kind": "UNIT_PRICE", "importance": "REQUIRED",
        "expected_value": {"amount": "6", "currency": "USD"}}]}),
    ("ambiguous-material", {"ambiguities": []}),
    *[("ambiguous-material", {"requirements": [{"kind": "MATERIAL", "importance": None,
        "expected_value": {"value": material}}]})
      for material in ("cotton", "polyester", "cotton or polyester")],
    ("untrusted-request", {"target_unit_price": "1"}),
    ("price-currency", {"category": None}),
    ("price-currency", {"product_name": None}),
    ("relative-delivery", {"delivery_target": {"kind": "DATE", "date": "2026-12-01"}}),
])
def test_semantic_regressions_remain_scoring_failures(case_id: str, change: dict[str, object]) -> None:
    outputs = json.loads((CASES_PATH.parent / "model_outputs.json").read_text(encoding="utf-8"))
    case = next(case for case in load_cases() if case["id"] == case_id)
    baseline = ExtractedBrief.model_validate(outputs[case_id])
    assert score_case(baseline, case["expected"]) == (9, 9)
    result = ExtractedBrief.model_validate({**outputs[case_id], **change})
    assert score_case(result, case["expected"]) == (8, 9)


@pytest.mark.parametrize("material,importance", [
    ("cotton", None), ("polyester", None), ("cotton", "REQUIRED"),
])
def test_definite_material_preserves_value_and_only_stated_importance(
    material: str, importance: str | None,
) -> None:
    expected = {"product_name": "bags", "category": "bags", "requirements": [
        {"kind": "MATERIAL", "importance": importance, "expected_value": {"value": material}}
    ]}
    draft = {"product_name": None, "category": None, "quantity": None, "destination": None,
             "delivery_target": None, "target_unit_price": None, "attributes": [],
             "requirements": [], "ambiguities": [], **expected}
    result = ExtractedBrief.model_validate(draft)
    assert result.requirements[0].importance == importance
    assert result.requirements[0].expected_value.model_dump() == {"value": material}
    assert score_case(result, expected) == (9, 9)
    changed = {**draft, "requirements": [{"kind": "MATERIAL", "importance": "PREFERRED",
                                        "expected_value": {"value": material}}]}
    assert score_case(ExtractedBrief.model_validate(changed), expected) == (8, 9)


@pytest.mark.parametrize("branding", [True, False, None])
def test_branding_unknown_and_explicit_boolean_are_distinct(branding: bool | None) -> None:
    requirement = {"kind": "CAPABILITY", "importance": "REQUIRED",
                   "expected_value": {"capability_key": "CUSTOM_BRANDING", "value": branding}}
    draft = {"product_name": None, "category": None, "quantity": None, "destination": None,
             "delivery_target": None, "target_unit_price": None, "attributes": [],
             "requirements": [requirement] if branding is not None else [],
             "ambiguities": [] if branding is not None else ["Branding has not been decided."]}
    result = ExtractedBrief.model_validate(draft)
    assert score_case(result, draft) == (9, 9)
    other = {**draft, "requirements": [{**requirement, "expected_value": {
        "capability_key": "CUSTOM_BRANDING", "value": not branding}}]}
    assert score_case(ExtractedBrief.model_validate(other), draft) == (8, 9)


@pytest.mark.parametrize("importance", ["REQUIRED", "PREFERRED", None])
@pytest.mark.parametrize("currency", ["AUD", None])
def test_price_bounds_preserve_amount_currency_importance_and_qualification(
    importance: str | None, currency: str | None,
) -> None:
    draft = {"product_name": "pouches", "category": "pouches", "quantity": 100,
             "destination": None, "delivery_target": None, "target_unit_price": "6",
             "attributes": [], "ambiguities": ["Unit price below 6."],
             "requirements": [{"kind": "UNIT_PRICE", "importance": importance,
                               "expected_value": {"amount": "6", "currency": currency}}]}
    result = ExtractedBrief.model_validate(draft)
    assert result.target_unit_price == "6"
    assert result.requirements[0].importance == importance
    assert result.requirements[0].expected_value.model_dump() == {"amount": "6", "currency": currency}
    assert score_case(result, draft) == (9, 9)
    assert score_case(ExtractedBrief.model_validate({**draft, "ambiguities": []}), draft) == (8, 9)
