"""Approved M6-U1 P2 controls: actor nouns, price aliases and heuristic metadata."""

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from sourcepilot.ai import clarification_eval
from sourcepilot.ai import eval_baseline as baseline
from sourcepilot.ai.clarification import ClarificationQuestion
from sourcepilot.ai.eval_scoring import check_failed, measurements, score_output


@pytest.mark.parametrize("actor", ["workshop", "workshops", "manufacturer", "manufacturers",
                                   "factory", "firm", "supplier"])
@pytest.mark.parametrize("claim,supported", [
    ("can fabricate recycled polyester bags", True),
    ("can fabricate aircraft engines", False),
    ("designs surgical implants", False),
])
def test_supplier_actor_nouns_preserve_action_and_object_support(
    actor: str, claim: str, supported: bool,
) -> None:
    case = next(case for case in baseline.load_scope(["supplier_explanation"])["supplier_explanation"]
                if case["id"] == "clear-match")
    evidence_id = case["fetched_evidence_ids"][0]
    case["evidence_texts"] = {evidence_id: "The supplier produces recycled polyester bags."}
    output = deepcopy(case["output"])
    output["concerns"] = [{"text": f"The {actor} {claim}.", "requirement_id": None,
                           "evidence_ids": [evidence_id]}]
    checks = score_output("supplier_explanation", case, output)
    assert next(check for check in checks if check["kind"] == "exact")["passed"]
    signal = next(check for check in checks if check["name"] == "supplier_free_text_capability_signal")
    assert signal["triggered"] is not supported


def price_example(category: str, identifier: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    case = next(case for case in baseline.load_scope([category])[category]
                if case["id"] == identifier)
    output = deepcopy(case["output"])
    point = (output["supplier_summaries"][0] if category == "comparison"
             else output["suggestion"]["uncertainties"][0])
    point["supplier_ids"] = ["11111111-1111-1111-1111-111111111111",
                             "11111111-1111-1111-1111-111111111112"]
    point["quote_fields"] = [
        {"quote_id": "22222222-2222-2222-2222-222222222221", "field_key": "unit_price"},
        {"quote_id": "22222222-2222-2222-2222-222222222222", "field_key": "unit_price"},
    ]
    return case, output, point


@pytest.mark.parametrize("category", ["comparison", "suggestion"])
def test_human_review_price_warning_accepts_contextual_aliases(category: str) -> None:
    case, output, point = price_example(category, "mixed-currencies")
    example = next(case for case in baseline.read_json(baseline.HUMAN_REVIEW)
                   if case["id"] == "mixed-currency-warning")
    point["text"] = example["narrative_example"]
    assert not any(check_failed(check) for check in score_output(category, case, output))
    for wrong in (point["text"].replace("USD 4.50", "USD 9.99"),
                  point["text"].replace("AUD 3.90", "EUR 3.90")):
        point["text"] = wrong
        assert any(check_failed(check) and check["name"] == f"bounded_{category}_narrative_signal"
                   for check in score_output(category, case, output))
    point["text"] = example["narrative_example"]
    point["quote_fields"] = point["quote_fields"][:1]
    assert any(check_failed(check) for check in score_output(category, case, output))


@pytest.mark.parametrize("category", ["comparison", "suggestion"])
def test_price_aliases_require_named_scenario_context(category: str) -> None:
    case, output, point = price_example(category, "mixed-currencies")
    point["text"] = "A quotes USD 4.50 and B quotes AUD 3.90; prices cannot be directly compared."
    case["payload"]["suppliers"][0]["supplier_name"] = "Unrelated manufacturer"
    assert any(check_failed(check) and check["name"] == f"bounded_{category}_narrative_signal"
               for check in score_output(category, case, output))


@pytest.mark.parametrize("category", ["comparison", "suggestion"])
@pytest.mark.parametrize("identifier", ["mixed-currencies", "unequal-quantities"])
@pytest.mark.parametrize("prefix", ["", "Supplier "])
@pytest.mark.parametrize("warning", ["", "; prices cannot be directly compared",
                                     ", despite the currency or quantity mismatch"])
def test_incomparable_price_rankings_still_signal_with_warnings(
    category: str, identifier: str, prefix: str, warning: str,
) -> None:
    case, output, point = price_example(category, identifier)
    point["text"] = f"{prefix}B wins on price over {prefix}A{warning}."
    checks = score_output(category, case, output)
    assert not any(check_failed(check) for check in checks if check["kind"] == "exact")
    signal = next(check for check in checks if check["name"] == "incomparable_price_ranking_signal")
    assert signal["kind"] == "heuristic" and signal["triggered"]
    assert point["text"] in signal["detail"]


@pytest.mark.parametrize("category", ["comparison", "suggestion"])
@pytest.mark.parametrize("identifier", ["mixed-currencies", "unequal-quantities"])
@pytest.mark.parametrize("text,triggered", [
    ("We cannot conclude that B is cheaper than A because the currencies differ.", False),
    ("We can't determine whether Supplier B has the lowest unit price.", False),
    ("We are unable to establish that B wins on price over A.", False),
    ("There is no basis to conclude that B is cheaper than A.", False),
    ("There is insufficient information to say that B is cheaper than A.", False),
    ("It is unclear whether B is cheaper than A.", False),
    ("It is not clear whether Supplier B is lower priced than Supplier A.", False),
    ("It is uncertain whether B has the better unit price.", False),
    ("Do not rank B as cheaper than A: the quotes use different currencies.", False),
    ("B is cheaper than A; the currencies differ.", True),
    ("B is not cheaper than A.", True),
    ("We cannot conclude that B is cheaper than A, but A is cheaper than B.", True),
    ("We cannot conclude that B is cheaper than A and A wins on price over B.", True),
    ("We cannot conclude that B is cheaper than A; A has the lowest unit price.", True),
    ("B wins on price over A, although we cannot conclude that A is cheaper than B.", True),
    ("We cannot conclude that B is cheaper than A. B wins on price over A.", True),
    ("It is unclear whether B is cheaper than A, yet A has the better unit price.", True),
])
def test_price_ranking_rejection_is_local_to_each_recognized_claim(
    category: str, identifier: str, text: str, triggered: bool,
) -> None:
    case, output, point = price_example(category, identifier)
    point["text"] = text
    checks = score_output(category, case, output)
    assert not any(check_failed(check) for check in checks if check["kind"] == "exact")
    signal = next(check for check in checks if check["name"] == "incomparable_price_ranking_signal")
    assert signal["kind"] == "heuristic" and signal["triggered"] is triggered
    if not triggered:
        assert not any(check_failed(check) for check in checks)


@pytest.mark.parametrize("question", ["Where should the order be delivered?", "Where?", "Where " * 30 + "now?"])
def test_clarification_wording_is_heuristic_with_original_values(question: str) -> None:
    case = next(case for case in baseline.load_scope(["clarification"])["clarification"]
                if case["id"] == "missing-destination")
    output = deepcopy(case["output"])
    output["questions"][0]["question"] = question
    original = clarification_eval.score_questions(
        [ClarificationQuestion.model_validate(item) for item in output["questions"]],
        case["expected_keys"],
    )
    checks = score_output("clarification", case, output)
    for name in ("clarity_rate", "conciseness_rate"):
        check = next(check for check in checks if check["name"] == name)
        assert check["kind"] == "heuristic" and "passed" not in check
        assert check["value"] == original[name]
        assert check["definition"] == clarification_eval.WORDING_HEURISTICS[name]
        assert check["triggered"] == (original[name] != 1.0)
        assert not check["critical"]
    exact = {check["name"] for check in checks if check["kind"] == "exact"}
    assert exact == {"readiness_keys", "field_coverage", "missing_field_coverage",
                     "redundant_question_rate", "irrelevant_question_rate"}
    assert not any(check_failed(check) for check in checks if check["kind"] == "exact")
    counts = measurements("clarification", case, output)
    for name in ("clarity", "conciseness"):
        assert counts[f"{name}_heuristic"]["kind"] == "heuristic"
        assert counts[f"{name}_heuristic"]["numerator"] == original[f"{name}_rate"]
        assert counts[f"{name}_heuristic"]["denominator"] == 1


def test_clarification_report_classification_and_measurements_are_consistent(tmp_path: Path) -> None:
    result, code = baseline.execute("offline", ["clarification"], tmp_path)
    assert code == 0 and result["expected_case_count"] == 12
    persisted = baseline.read_json(tmp_path / "results.json")
    assert persisted["cases"] == result["cases"]
    assert persisted["metrics"] == result["metrics"]
    assert persisted["measurements"] == result["measurements"]
    assert persisted["heuristic_signals"] == result["heuristic_signals"]
    for name in ("clarity_rate", "conciseness_rate"):
        assert name not in result["metrics"]["clarification"]
        assert result["heuristic_signals"]["clarification"][name]["triggered"] == 0
        assert result["heuristic_signals"]["clarification"][name]["inspected"] == 12
    for name in ("clarity_heuristic", "conciseness_heuristic"):
        assert result["measurements"]["clarification"][name] == {
            "kind": "heuristic", "numerator": 14, "denominator": 14, "measured_case_count": 12,
        }
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    exact_section = summary.split("## Exact deterministic assertions")[1].split("## Measured metrics")[0]
    assert "clarity_rate" not in exact_section and "conciseness_rate" not in exact_section
    for name in ("clarity", "conciseness"):
        assert f"| clarification | {name}_heuristic | heuristic | 14 / 14 | 12 |" in summary
        assert f"| clarification | {name}_rate | 0 / 12 |" in summary


def test_fractional_clarification_wording_measurements_are_preserved() -> None:
    case = next(case for case in baseline.load_scope(["clarification"])["clarification"]
                if len(case["expected_keys"]) == 2)
    output = deepcopy(case["output"])
    output["questions"][0]["question"] = "Why?"
    checks = score_output("clarification", case, output)
    clarity = next(check for check in checks if check["name"] == "clarity_rate")
    assert clarity["kind"] == "heuristic" and clarity["triggered"]
    assert clarity["value"] == 0.5
    assert measurements("clarification", case, output)["clarity_heuristic"] == {
        "kind": "heuristic", "numerator": 1, "denominator": 2,
    }
    assert not any(check_failed(check) for check in checks if check["kind"] == "exact")
