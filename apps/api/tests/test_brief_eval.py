import json

from sourcepilot.ai.brief_eval import CASES_PATH, load_cases, score_case
from sourcepilot.ai.brief_interpreter import ExtractedBrief


def test_twelve_offline_brief_cases_validate_and_match_expected_fields() -> None:
    cases = load_cases()
    outputs = json.loads((CASES_PATH.parent / "model_outputs.json").read_text(encoding="utf-8"))

    assert len(cases) == len(outputs) == 12
    assert len({case["id"] for case in cases}) == 12
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
