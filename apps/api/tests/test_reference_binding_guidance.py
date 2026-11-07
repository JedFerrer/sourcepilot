"""Provider-free regressions for repeated non-string requirement binding guidance."""

import json
from copy import deepcopy
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from sourcepilot.ai import comparison_advice as advice_module
from sourcepilot.ai import tradeoff_analysis as analysis_module
from sourcepilot.ai.analyst_tools import ComparisonSnapshotResult
from sourcepilot.ai.client import AnalystModelInvocation
from sourcepilot.ai.comparison_context import comparison_context
from sourcepilot.ai.tradeoff_analysis_eval import LEAD, fixture_snapshot
from sourcepilot.briefs.domain import validate_requirement_expected_value
from sourcepilot.comparison.validation import (
    REPAIR_FEEDBACK,
    ComparisonRejection,
    RejectionCode,
    comparison_repair_feedback,
)
from sourcepilot.persistence.models import AIRun, SupplierExplanationRunStep
from tests.test_comparison_advice import suggestion
from tests.test_tradeoff_analysis import semantic_repair_output

EXTRA = "33333333-3333-3333-3333-333333333339"
BRANDING = "33333333-3333-3333-3333-333333333338"


def reference_fixture(kind: str) -> tuple[ComparisonSnapshotResult, dict[str, Any], str, str]:
    snapshot = fixture_snapshot()
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    base = semantic_repair_output(payload)
    if kind == "numeric":
        requirement_id, owner_index, state = LEAD, 1, "MEETS"
        requirement_kind = "PRODUCTION_LEAD_TIME"
        first_value, second_value = {"max_days": 40}, {"max_days": 50}
        payload["brief"]["requirements"][1]["expected_value"] = (
            validate_requirement_expected_value(requirement_kind, first_value))
        # Retain the original deterministic conflict and its coverage/citation.
        base["important_conflicts"][0]["text"] = "Supplier A requirement is CONFLICT."
        base["key_tradeoffs"].append({
            **deepcopy(base["important_conflicts"][0]),
            "text": "Supplier A production lead time limit: 40 days.",
        })
        label, value_label = "production lead time", "40 production lead time"
        description = "Supplier B production lead time limit: 40 days."
    else:
        requirement_id, owner_index, state = BRANDING, 0, "DOES_NOT_MEET"
        requirement_kind = "CAPABILITY"
        first_value = {"capability_key": "CUSTOM_BRANDING", "value": False}
        second_value = {"capability_key": "PRODUCT_CATEGORY", "value": "cosmetic pouches"}
        payload["brief"]["requirements"].append({
            "id": BRANDING, "kind": requirement_kind, "importance": "PREFERRED",
            "expected_value": validate_requirement_expected_value(requirement_kind, first_value),
        })
        for row in payload["suppliers"]:
            row["evaluation"]["results"].append({
                "requirement_id": BRANDING, "status": "DOES_NOT_MEET",
            })
        label, value_label = "custom branding", "false custom branding"
        description = "Supplier A requested custom branding: false."
    payload["brief"]["requirements"].append({
        "id": EXTRA, "kind": requirement_kind, "importance": "PREFERRED",
        "expected_value": validate_requirement_expected_value(requirement_kind, second_value),
    })
    for row in payload["suppliers"]:
        row["evaluation"]["results"].append({"requirement_id": EXTRA, "status": "MEETS"})
    owner = payload["suppliers"][owner_index]
    point = {
        "text": f"{owner['supplier_name']} requirement is {state}.",
        "supplier_ids": [owner["supplier_id"]], "requirement_ids": [requirement_id],
        "quote_fields": [{"quote_id": owner["quote_id"], "field_key": "production_lead_time"}],
        "evidence_ids": [],
    }
    base["supplier_summaries"].insert(0, point)
    # The description cites the requirement itself, not an invented quote field.
    base["key_tradeoffs"].append({**deepcopy(point), "text": description, "quote_fields": []})
    return snapshot, base, label, value_label


def mutate_output(base: dict[str, Any], mutation: str, snapshot: ComparisonSnapshotResult,
                  label: str, value_label: str) -> dict[str, Any]:
    output = deepcopy(base)
    point = output["supplier_summaries"][0]
    if mutation == "kind-only":
        point["text"] = point["text"].replace("requirement", label)
    elif mutation == "value-in-state":
        point["text"] = point["text"].replace("requirement", value_label)
    elif mutation == "ambiguous-ids":
        point["requirement_ids"].append(EXTRA)
    elif mutation == "wrong-state":
        point["text"] = point["text"].replace("DOES_NOT_MEET", "MEETS") if (
            "DOES_NOT_MEET" in point["text"]) else point["text"].replace("MEETS", "UNKNOWN")
    elif mutation == "unknown-pair":
        point["quote_fields"][0]["field_key"] = "max_days"
    elif mutation == "unknown-quote":
        point["quote_fields"][0]["quote_id"] = "99999999-9999-9999-9999-999999999999"
    elif mutation == "wrong-owner":
        payload = cast(dict[str, Any], snapshot.comparison_payload)
        other = next(row for row in payload["suppliers"]
                     if row["supplier_id"] not in point["supplier_ids"])
        point["quote_fields"][0]["quote_id"] = other["quote_id"]
    elif mutation == "missing-id":
        point["requirement_ids"] = []
    elif mutation == "description-state":
        output["key_tradeoffs"][-1]["text"] = point["text"].replace("requirement", label)
    return output


def contract(combined: bool, output: dict[str, Any], snapshot: ComparisonSnapshotResult) -> Any:
    if combined:
        return advice_module.ComparisonAdvice.model_validate({
            "analysis": output, "suggestion": suggestion(cast(dict[str, Any], snapshot.comparison_payload)),
        })
    return analysis_module.TradeoffAnalysis.model_validate(output)


@pytest.mark.parametrize("combined", [False, True])
@pytest.mark.parametrize("kind", ["numeric", "boolean"])
@pytest.mark.parametrize("mutation,code", [
    ("valid", None), ("kind-only", "STATE_REFERENCE"),
    ("value-in-state", "STATE_SYNTAX"), ("ambiguous-ids", "STATE_REFERENCE"),
    ("wrong-state", "STATE_CONTRADICTION"), ("unknown-pair", "QUOTE_REFERENCE"),
    ("unknown-quote", "QUOTE_REFERENCE"), ("wrong-owner", "QUOTE_OWNER_MISMATCH"),
    ("missing-id", "STATE_REFERENCE"), ("description-state", "STATE_REFERENCE"),
])
def test_repeated_nonstring_reference_contract(
    combined: bool, kind: str, mutation: str, code: str | None,
) -> None:
    snapshot, base, label, value_label = reference_fixture(kind)
    output = mutate_output(base, mutation, snapshot, label, value_label)
    validate = advice_module.validate_advice if combined else analysis_module.validate_analysis
    if code is None:
        validate(contract(combined, output, snapshot), snapshot)
    else:
        with pytest.raises(ComparisonRejection) as failure:
            validate(contract(combined, output, snapshot), snapshot)
        assert failure.value.code.value == code


def test_generation_and_repair_share_nonstring_binding_guidance() -> None:
    assert analysis_module.PROMPT_VERSION == "tradeoff-analysis-v9"
    assert advice_module.PROMPT_VERSION == "comparison-advice-v9"
    for text in (
        analysis_module.INSTRUCTIONS, advice_module.INSTRUCTIONS,
        *(comparison_repair_feedback(ComparisonRejection(code, "untrusted sentinel"))
          for code in (RejectionCode.STATE_SYNTAX, RejectionCode.STATE_REFERENCE)),
    ):
        normalized = " ".join(text.split())
        for guidance in (
            "nonempty string expected_value.value", "uniquely identify",
            "numeric limits and boolean values", "Supplier A requirement is MEETS.",
            "exactly one matching requirement ID", "separate cited point",
            "same supplier and single requirement ID", "another state assertion",
        ):
            assert guidance in normalized
        assert "untrusted sentinel" not in text


@pytest.mark.parametrize("combined", [False, True])
@pytest.mark.parametrize("kind", ["numeric", "boolean"])
@pytest.mark.parametrize("initial", ["unknown-pair", "kind-only", "value-in-state"])
@pytest.mark.parametrize("repair", [
    "valid", "pair-only", "ambiguous-ids", "wrong-state", "unknown-pair", "wrong-owner",
])
def test_nonstring_reference_runtime_repair(
    monkeypatch: pytest.MonkeyPatch, combined: bool, kind: str, initial: str, repair: str,
) -> None:
    snapshot, base, label, value_label = reference_fixture(kind)
    original = deepcopy(snapshot)
    stored: list[Any] = []

    class MemorySession:
        def add(self, item: Any) -> None:
            if isinstance(item, AIRun):
                item.id = uuid4()
            stored.append(item)

        def commit(self) -> None:
            pass

    initial_code = {"unknown-pair": RejectionCode.QUOTE_REFERENCE,
                    "kind-only": RejectionCode.STATE_REFERENCE,
                    "value-in-state": RejectionCode.STATE_SYNTAX}[initial]

    class RepairModel:
        model = "provider-free-reference-binding"

        def __init__(self) -> None:
            self.calls = 0
            self.rejected = ""
            self.items: list[dict[str, Any]] = []

        def invoke_with_tools(self, **kwargs: Any) -> AnalystModelInvocation:
            self.calls += 1
            assert self.calls <= 2
            if self.calls == 1:
                self.items = deepcopy(kwargs["input_items"])
                assert json.loads(self.items[0]["content"]) == comparison_context(snapshot)
                output = mutate_output(base, initial, snapshot, label, value_label)
                if initial == "unknown-pair":
                    # Both defects coexist: fixing only the quote key exposes the
                    # repeated-kind binding rejection on the next validation.
                    output["supplier_summaries"][0]["text"] = (
                        base["supplier_summaries"][0]["text"].replace("requirement", label))
                self.rejected = contract(combined, output, snapshot).model_dump_json()
                return AnalystModelInvocation(self.rejected, (), 2, 1)
            assert kwargs["input_items"] == self.items + [{"role": "assistant", "content": self.rejected}]
            assert REPAIR_FEEDBACK[initial_code] in kwargs["instructions"]
            assert "Supplier A requirement is MEETS." in kwargs["instructions"]
            assert self.rejected not in kwargs["instructions"]
            final = json.loads(self.rejected)
            output = final["analysis"] if combined else final
            # Correct only the offending point in the actual rejected final.
            corrected = mutate_output(base, "kind-only" if repair == "pair-only" else repair,
                                      snapshot, label, value_label)
            output["supplier_summaries"][0] = corrected["supplier_summaries"][0]
            assert output == corrected  # All descriptions, disclosures and other citations survive.
            return AnalystModelInvocation(json.dumps(final), (), 2, 1)

    monkeypatch.setenv("SOURCEPILOT_LANGFUSE_ENABLED", "false")
    monkeypatch.setattr(analysis_module, "_current_snapshot", lambda *args, **kwargs: snapshot)
    model = RepairModel()
    module = advice_module if combined else analysis_module
    kwargs: dict[str, Any] = {
        "demo_session_id": uuid4(), "project_id": uuid4(), "client_factory": lambda: model,
        "operation": "comparison_advice" if combined else "tradeoff_analysis",
        "prompt_version": module.PROMPT_VERSION, "base_instructions": module.INSTRUCTIONS,
        "result_type": advice_module.ComparisonAdvice if combined else analysis_module.TradeoffAnalysis,
        "validate": advice_module.validate_advice if combined else analysis_module.validate_analysis,
    }
    if repair == "valid":
        analysis_module.run_comparison_analyst(cast(Session, MemorySession()), **kwargs)
    else:
        with pytest.raises(analysis_module.TradeoffUnavailableError):
            analysis_module.run_comparison_analyst(cast(Session, MemorySession()), **kwargs)
    run = next(item for item in stored if isinstance(item, AIRun))
    steps = [item for item in stored if isinstance(item, SupplierExplanationRunStep)]
    codes = [item.name for item in steps if item.kind == "validation" and item.outcome == "INVALID"]
    terminal = {"pair-only": "STATE_REFERENCE", "ambiguous-ids": "STATE_REFERENCE",
                "wrong-state": "STATE_CONTRADICTION",
                "unknown-pair": "QUOTE_REFERENCE", "wrong-owner": "QUOTE_OWNER_MISMATCH"}
    assert codes == [initial_code.value] + ([] if repair == "valid" else [terminal[repair]])
    assert run.status == ("COMPLETED" if repair == "valid" else "VALIDATION_FAILED")
    assert run.validation_status == ("REPAIRED" if repair == "valid" else "INVALID")
    assert run.model_turn_count == model.calls == 2
    assert run.tool_call_count == 0
    assert sum(item.kind == "retry" and item.outcome == "REPAIR" for item in steps) == 1
    assert snapshot == original
