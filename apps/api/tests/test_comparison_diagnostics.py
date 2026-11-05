"""Safe diagnostics cannot reveal rejected model values or exception messages."""

import json
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from sourcepilot.ai.client import AnalystModelInvocation
from sourcepilot.ai.comparison_advice import analyze_comparison_advice
from sourcepilot.ai.tracing import ERRORS, NAMES, safe_label
from sourcepilot.ai.tradeoff_analysis import TradeoffUnavailableError
from sourcepilot.comparison.validation import (
    REPAIR_FEEDBACK,
    ComparisonRejection,
    RejectionCode,
    comparison_repair_feedback,
    rejection_code,
    schema_issue_labels,
)
from sourcepilot.persistence.models import AIRun, Comparison, Project, SupplierExplanationRunStep
from tests.test_ai_tracing import Observation, run_record
from tests.test_comparison_advice import AdviceModel
from tests.test_tradeoff_analysis import client, database_url, engine, ready  # noqa: F401

# ruff: noqa: F811 -- shared isolated database fixtures.

SECRET = "private-quote-and-credential-sentinel"


@pytest.mark.parametrize("mutation,code,phase", [
    ("supplier", "SUPPLIER_REFERENCE", "analysis"),
    ("requirement", "REQUIREMENT_REFERENCE", "analysis"),
    ("evidence", "UNKNOWN_EVIDENCE", "analysis"),
    ("score", "PROHIBITED_SCORE", "analysis"),
    ("unknown", "MISSING_UNKNOWN", "analysis"),
    ("required", "MISSING_REQUIRED_FAILURE", "analysis"),
    ("quote_owner", "QUOTE_OWNER_MISMATCH", "analysis"),
    ("state", "STATE_CONTRADICTION", "analysis"),
    ("reasons", "SUGGESTION_REASONS", "suggestion"),
    ("coverage", "SUGGESTION_COVERAGE", "suggestion"),
])
def test_real_validator_rejection_reason_and_phase(mutation, code, phase) -> None:
    from sourcepilot.ai.comparison_advice import ComparisonAdvice, validate_advice
    from sourcepilot.ai.tradeoff_analysis_eval import B, fixture_snapshot
    from tests.test_comparison_advice import suggestion
    from tests.test_tradeoff_analysis import valid_output

    snapshot = fixture_snapshot()
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    assert payload is not None
    advice = ComparisonAdvice.model_validate({
        "analysis": valid_output(payload), "suggestion": suggestion(payload, B),
    })
    validate_advice(advice, snapshot)
    point = advice.analysis.supplier_summaries[0]
    if mutation == "supplier":
        point.supplier_ids = [uuid4()]
    elif mutation == "requirement":
        point.requirement_ids = [uuid4()]
    elif mutation == "evidence":
        point.evidence_ids = [uuid4()]
    elif mutation == "score":
        point.text = "Supplier A has a 95% match score."
    elif mutation == "unknown":
        advice.analysis.important_unknowns.clear()
    elif mutation == "required":
        advice.analysis.supplier_summaries.clear()
        advice.analysis.key_tradeoffs.clear()
    elif mutation == "quote_owner":
        from sourcepilot.comparison.advice import QuoteFieldReference

        point.quote_fields = [QuoteFieldReference(
            quote_id=UUID(payload["suppliers"][1]["quote_id"]), field_key="unit_price")]
    elif mutation == "state":
        unknown = advice.analysis.important_unknowns[0]
        for supplier in payload["suppliers"]:
            if UUID(supplier["supplier_id"]) in unknown.supplier_ids:
                for finding in supplier["evaluation"]["results"]:
                    if finding["requirement_id"] and UUID(finding["requirement_id"]) in unknown.requirement_ids:
                        finding["status"] = "MEETS"
    elif mutation == "reasons":
        advice.suggestion.supporting_reasons.clear()
    else:
        advice.suggestion.tradeoffs.clear()
    with pytest.raises(ComparisonRejection) as failure:
        validate_advice(advice, snapshot)
    assert failure.value.code.value == code and failure.value.phase == phase
    assert SECRET not in comparison_repair_feedback(failure.value)


def test_exported_validation_diagnostics_are_actionable_and_content_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sourcepilot.ai import tracing

    calls = []
    monkeypatch.setattr(tracing, "langfuse_client", lambda: Observation(calls))
    run = run_record()
    run.operation = "comparison_advice"
    run.status = "VALIDATION_FAILED"
    run.error_type = "STATE_CONTRADICTION"
    observation = tracing.RunObservations(run, {})
    observation.step("validation_phase", "INVALID", "analysis_initial", 1)
    observation.step("validation", "INVALID", "STATE_CONTRADICTION", 2)
    observation.step("validation_schema", "INVALID", SECRET, 3)
    observation.record(run)
    serialized = json.dumps(calls)
    assert "STATE_CONTRADICTION" in serialized and "analysis_initial" in serialized
    assert SECRET not in serialized
    assert all("input" not in call and "output" not in call for call in calls)


@pytest.mark.parametrize("code", list(RejectionCode))
def test_reason_feedback_is_fixed_and_allowlisted(code: RejectionCode) -> None:
    error = ComparisonRejection(code, SECRET)
    assert rejection_code(error) == code
    assert safe_label(code.value, ERRORS) == code.value
    assert safe_label(code.value, NAMES) == code.value
    assert SECRET not in comparison_repair_feedback(error)
    assert REPAIR_FEEDBACK[code] in comparison_repair_feedback(error)


def test_unknown_exception_and_mutated_reason_fail_closed() -> None:
    error = ComparisonRejection(RejectionCode.STATE_REFERENCE, SECRET)
    error.code = SECRET  # type: ignore[assignment] - malicious/nonconforming boundary value
    for candidate in (error, ValueError(SECRET)):
        assert rejection_code(candidate) == RejectionCode.UNKNOWN_REJECTION
        assert SECRET not in comparison_repair_feedback(candidate)
    assert safe_label(SECRET, NAMES) == "OTHER"


def test_schema_reason_does_not_export_inputs_context_or_extra_field_names() -> None:
    class Output(BaseModel):
        model_config = ConfigDict(extra="forbid")
        count: int

    with pytest.raises(ValidationError) as raised:
        Output.model_validate({"count": SECRET, SECRET: SECRET})
    assert SECRET in str(raised.value)
    assert rejection_code(raised.value) == RejectionCode.SCHEMA_INVALID
    feedback = comparison_repair_feedback(raised.value)
    assert "schema validation" in feedback
    assert SECRET not in feedback
    assert all(SECRET not in label and safe_label(label, NAMES) == label
               for label in schema_issue_labels(raised.value))


@pytest.mark.parametrize("phase,expected", [
    ("analysis", "SUPPLIER_REFERENCE"), ("suggestion", "NULL_EXPLANATION"),
    ("schema", "SCHEMA_INVALID"),
])
def test_both_rejections_have_safe_reason_and_phase(
    client, engine: Engine, phase: str, expected: str,
) -> None:
    class RejectedModel(AdviceModel):
        def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
            # Produce independent invalid finals, preserving the original input.
            result = super().invoke_with_tools(**kwargs)
            output = json.loads(result.output_text)
            if phase == "analysis":
                output["analysis"]["supplier_summaries"][0]["supplier_ids"] = []
                output["analysis"]["supplier_summaries"][0]["text"] = SECRET
            elif phase == "suggestion":
                output["suggestion"]["uncertainties"] = []
            else:
                output[SECRET] = SECRET
            return AnalystModelInvocation(json.dumps(output), (), 1, 1)

    project_id, _, _ = ready(client)
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        snapshot = session.scalar(select(Comparison.id).where(Comparison.project_id == project.id))
        assert snapshot is not None
        with pytest.raises(TradeoffUnavailableError):
            analyze_comparison_advice(session, demo_session_id=project.demo_session_id,
                                      project_id=project.id, snapshot_id=snapshot,
                                      client_factory=RejectedModel)
        run = session.scalar(select(AIRun).where(AIRun.project_id == project.id))
        assert run is not None and run.error_type == expected and run.model_turn_count == 2
        steps = session.scalars(select(SupplierExplanationRunStep).where(
            SupplierExplanationRunStep.air_run_id == run.id).order_by(SupplierExplanationRunStep.sequence)).all()
        assert [step.name for step in steps if step.kind == "validation"] == [expected, expected]
        assert [step.name for step in steps if step.kind == "validation_phase"] == [
            f"{phase}_initial", f"{phase}_repair",
        ]
        assert SECRET not in json.dumps([(step.kind, step.outcome, step.name) for step in steps])
