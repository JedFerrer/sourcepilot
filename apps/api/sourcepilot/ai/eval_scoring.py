"""Eval-only exact assertions and bounded heuristic signals."""

from __future__ import annotations

import json
from typing import Any

from sourcepilot.ai import (
    brief_eval,
    clarification_eval,
    comparison_advice_eval,
    quote_extraction_eval,
    supplier_explanation_eval,
    tradeoff_analysis_eval,
)
from sourcepilot.ai.brief_interpreter import ExtractedBrief
from sourcepilot.ai.clarification import (
    ClarificationQuestion,
    ClarificationSet,
    validate_field_coverage,
)
from sourcepilot.ai.comparison_advice import ComparisonAdvice, validate_advice
from sourcepilot.ai.quote_extractor import QuoteExtraction, validate_source_references
from sourcepilot.ai.tradeoff_analysis import TradeoffAnalysis, validate_analysis


def assertion(
    name: str, passed: bool, *, critical: bool = True, detail: str | None = None
) -> dict[str, Any]:
    return {"name": name, "kind": "exact", "passed": passed,
            "critical": critical, "detail": detail}


def heuristic_signal(name: str, details: list[str], *, critical: bool = True) -> dict[str, Any]:
    return {"name": name, "kind": "heuristic", "triggered": bool(details),
            "critical": critical, "detail": "; ".join(details) if details else None,
            "interpretation": "suspicious_output" if details else "no_signal"}


def check_failed(check: dict[str, Any]) -> bool:
    return check["triggered"] if check["kind"] == "heuristic" else not check["passed"]


def _validation(name: str, function: Any) -> dict[str, Any]:
    try:
        function()
    except ValueError as error:
        return assertion(name, False, detail=str(error))
    return assertion(name, True)


def score_output(category: str, case: dict[str, Any], output: Any) -> list[dict[str, Any]]:
    """Score produced output, never replace it with fixture expectations."""
    if category == "brief":
        result = ExtractedBrief.model_validate(output)
        actual = result.model_dump(mode="json")
        expected = {**brief_eval.ABSENT_FIELDS, **case["expected"]}
        return [
            assertion(
                f"brief.{key}",
                brief_eval.field_matches(key, actual[key], value, case.get("aliases", {})),
                detail=None
                if actual[key] == value
                else f"expected={value!r}; actual={actual[key]!r}",
            )
            for key, value in expected.items()
        ]
    if category == "clarification":
        questions = [ClarificationQuestion.model_validate(item) for item in output["questions"]]
        keys = case["expected_keys"]
        checks = [assertion("readiness_keys", clarification_eval.readiness_keys(case) == keys)]
        if keys:
            checks.append(
                _validation(
                    "field_coverage",
                    lambda: validate_field_coverage(
                        ClarificationSet(questions=questions), set(keys)
                    ),
                )
            )
        else:
            checks.append(assertion("no_questions_when_ready", not questions))
        for name, value in clarification_eval.score_questions(questions, keys).items():
            if name in clarification_eval.WORDING_HEURISTICS:
                signal = heuristic_signal(
                    name, [] if value == 1.0 else [f"{name}={value}; inspect question wording."],
                    critical=False,
                )
                signal.update(value=value, definition=clarification_eval.WORDING_HEURISTICS[name])
                checks.append(signal)
            else:
                checks.append(assertion(
                    name, value == (0.0 if name.endswith("question_rate") else 1.0),
                ))
        return checks
    if category == "supplier_explanation":
        if "rendered_explanation" in output:
            rendered = output["rendered_explanation"]
            return [
                assertion(
                    "rendered_states_and_evidence",
                    supplier_explanation_eval.score_rendered(case, rendered,
                                                             check_narrative=False),
                ),
                heuristic_signal("supplier_free_text_capability_signal",
                                 supplier_explanation_eval.free_text_signals(case, rendered)),
            ]
        candidate = {**case, "output": output}
        return [
            assertion(
                "states_and_evidence", supplier_explanation_eval.score_case(
                    candidate, check_narrative=False),
            ),
            heuristic_signal("supplier_free_text_capability_signal",
                             supplier_explanation_eval.free_text_signals(case, output)),
        ]
    if category == "quote_extraction":
        result = QuoteExtraction.model_validate(output)
        checks = []
        source_ids = set(quote_extraction_eval.document_blocks(case))
        evaluated = quote_extraction_eval.field_evaluations(result, case)
        checks.append(
            _validation("source_references", lambda: validate_source_references(result, source_ids))
        )
        for name, value in quote_extraction_eval.score_case(result, case).items():
            checks.append(assertion(name, value == (0.0 if name == "hallucination_rate" else 1.0)))
        for key, field in result.model_dump(mode="json")["fields"].items():
            expected = case["known"].get(key)
            if expected:
                checks.append(assertion(
                    f"field.{key}.value", evaluated[key]["field_match"],
                    detail=json.dumps({"rule": evaluated[key]["rule"], "expected": expected[0],
                                       "actual": field["extracted_value"],
                                       "uncertainty": field["uncertainty"]}, sort_keys=True),
                ))
                checks.append(assertion(
                    f"field.{key}.sources", evaluated[key]["source_match"],
                    detail=json.dumps({"expected": expected[1], "actual": field["source_block_ids"],
                                       "rule": evaluated[key]["source_rule"] or "evidence_mismatch"}, sort_keys=True),
                ))
            elif key in case["conflicts"]:
                checks.append(assertion(f"field.{key}.conflict", evaluated[key]["field_match"]))
            else:
                checks.append(
                    assertion(
                        f"field.{key}.unknown",
                        field["state"] == "UNKNOWN" and field["extracted_value"] is None,
                    )
                )
        for key, evaluation in evaluated.items():
            classification = evaluation["classification"]
            if classification in {
                "field_assignment", "unsupported_value", "unresolved_support", "misattributed_evidence",
            }:
                checks.append(assertion(
                    f"field.{key}.{classification}", False,
                    detail=json.dumps({
                        **evaluation, "field": key,
                        "actual": result.model_dump(mode="json")["fields"][key],
                        "expected": case["known"].get(key, "CONFLICT" if key in case["conflicts"] else "UNKNOWN"),
                    }, sort_keys=True),
                ))
        return checks
    snapshot = (
        comparison_advice_eval.scenario_snapshot(case)
        if "snapshot_id" in case
        else tradeoff_analysis_eval.fixture_snapshot()
    )
    if category == "comparison":
        result = TradeoffAnalysis.model_validate(output)
        signals = tradeoff_analysis_eval.narrative_signals(result, snapshot)
        return [
            _validation(
                "analysis_contract_states_references", lambda: validate_analysis(result, snapshot)
            ),
            heuristic_signal("incomparable_price_ranking_signal",
                             signals.get("incomparable_price_ranking", [])),
            heuristic_signal("lead_time_context_signal",
                             signals.get("lead_time_context_mismatch", [])),
            heuristic_signal("bounded_comparison_narrative_signal", [] if
                             tradeoff_analysis_eval.score_case(
                                 {"topic": case.get("topic", "references-only")},
                                 result, snapshot, check_price=False, check_lead=False)
                             else ["Recognized numeric, disclosure or topic check failed; inspect output."]),
        ]
    if category == "suggestion":
        advice = ComparisonAdvice.model_validate(output)
        joined = advice.analysis.model_copy(deep=True)
        joined.supplier_summaries.extend(
            advice.suggestion.supporting_reasons + advice.suggestion.tradeoffs
            + advice.suggestion.uncertainties
        )
        signals = tradeoff_analysis_eval.narrative_signals(joined, snapshot)
        selected = str(advice.suggestion.supplier_id) if advice.suggestion.supplier_id else None
        return [
            _validation(
                "advice_contract_states_references", lambda: validate_advice(advice, snapshot)
            ),
            assertion("allowed_suggestion_choice",
                      selected in case.get("live_allowed_supplier_ids", case["allowed_supplier_ids"])),
            heuristic_signal("incomparable_price_ranking_signal",
                             signals.get("incomparable_price_ranking", [])),
            heuristic_signal("lead_time_context_signal",
                             signals.get("lead_time_context_mismatch", [])),
            heuristic_signal("bounded_suggestion_narrative_signal", [] if
                             comparison_advice_eval.score_case(
                                 case, advice, snapshot, check_price=False, check_lead=False)
                             else ["Recognized narrative, disclosure or suggestion check failed; inspect output."]),
        ]
    raise ValueError(f"Unknown eval category: {category}")


def measurements(category: str, case: dict[str, Any], output: Any) -> dict[str, dict[str, Any]]:
    """Actual metric counts, separate from binary assertion pass rates."""
    if category == "quote_extraction":
        counts = quote_extraction_eval.metric_counts(QuoteExtraction.model_validate(output), case)
    elif category == "brief":
        result = ExtractedBrief.model_validate(output).model_dump(mode="json")
        expected = {**brief_eval.ABSENT_FIELDS, **case["expected"]}
        counts = {
            f"{key}_accuracy": (
                int(brief_eval.field_matches(key, result[key], value, case.get("aliases", {}))),
                1,
            )
            for key, value in expected.items()
        }
        absent = [key for key, value in expected.items() if value is None or value == []]
        counts["hallucinated_field_rate"] = (
            sum(result[key] not in (None, []) for key in absent),
            len(absent),
        )
    elif category == "clarification":
        questions = output["questions"]
        keys = [item["field_key"] for item in questions]
        expected_keys = case["expected_keys"]
        counts = {
            "missing_field_coverage": (len(set(keys) & set(expected_keys)), len(expected_keys)),
            "redundant_question_rate": (len(keys) - len(set(keys)), len(keys)),
            "irrelevant_question_rate": (sum(key not in expected_keys for key in keys), len(keys)),
            "clarity_heuristic": (
                sum(
                    item["question"].endswith("?") and len(item["question"].split()) >= 3
                    for item in questions
                ),
                len(questions),
            ),
            "conciseness_heuristic": (
                sum(len(item["question"]) <= 120 for item in questions),
                len(questions),
            ),
        }
    else:
        counts = {}
    return {
        name: {
            "kind": "heuristic" if category == "clarification"
            and name in {"clarity_heuristic", "conciseness_heuristic"} else "exact",
            "numerator": numerator, "denominator": denominator,
        }
        for name, (numerator, denominator) in counts.items()
    }
