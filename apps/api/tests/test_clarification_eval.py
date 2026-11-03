"""Offline M1-U5 clarification eval baseline."""

from sourcepilot.ai.clarification import ClarificationQuestion
from sourcepilot.ai.clarification_eval import load_cases, readiness_keys, score_questions


def test_curated_clarification_cases_follow_deterministic_readiness() -> None:
    cases = load_cases()
    assert len(cases) == 12
    for case in cases:
        assert readiness_keys(case) == case["expected_keys"], case["id"]
        questions = [ClarificationQuestion.model_validate(item) for item in case["questions"]]
        scores = score_questions(questions, case["expected_keys"])
        assert scores == {
            "missing_field_coverage": 1.0,
            "redundant_question_rate": 0.0,
            "irrelevant_question_rate": 0.0,
            "clarity_rate": 1.0,
            "conciseness_rate": 1.0,
        }, case["id"]


def test_eval_scores_redundant_and_irrelevant_questions() -> None:
    questions = [
        ClarificationQuestion(field_key="quantity", question="How many?", reason="Needed."),
        ClarificationQuestion(field_key="quantity", question="How many again?", reason="Needed."),
        ClarificationQuestion(field_key="target_unit_price", question="Price?", reason="Optional."),
    ]
    scores = score_questions(questions, ["quantity"])
    assert scores["redundant_question_rate"] == 1 / 3
    assert scores["irrelevant_question_rate"] == 1 / 3
