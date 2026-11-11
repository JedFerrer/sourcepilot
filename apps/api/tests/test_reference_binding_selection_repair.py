"""Real v10 entry-point repair; unlike the public-envelope prose harness."""

import json
from contextlib import nullcontext
from copy import deepcopy
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from sourcepilot.ai import comparison_advice as advice
from sourcepilot.ai import tradeoff_analysis as runtime
from sourcepilot.ai.advice_selection import AdviceSelectionTask
from sourcepilot.ai.analyst_tools import ComparisonSnapshotResult
from sourcepilot.ai.client import AnalystModelInvocation
from sourcepilot.ai.tradeoff_analysis_eval import CERT, LEAD, QA, QB, A, B, C
from sourcepilot.comparison.execution import ComparisonDeadline, current_deadline
from sourcepilot.comparison.validation import ComparisonRejection
from sourcepilot.persistence.models import AIRun, SupplierExplanationRunStep
from tests.test_reference_binding_guidance import BRANDING, EXTRA, reference_fixture

FOREIGN = "99999999-9999-9999-9999-999999999999"


def test_combined_generation_uses_selection_contract() -> None:
    assert advice.PROMPT_VERSION == "comparison-advice-v10"
    for rule in ("Return only ComparisonSelectionV1", "Do not write narrative, states, values",
                 "change only those slots", "preserve frozen entries", "Do not invent facts"):
        assert rule in " ".join(advice.INSTRUCTIONS.split())


def selection(snapshot: ComparisonSnapshotResult, kind: str) -> dict[str, Any]:
    # Literal source associations, independent of catalogue construction/indexing.
    rid = LEAD if kind == "numeric" else BRANDING
    return {
        "version": "comparison-selection-v1", "snapshot_id": str(snapshot.snapshot_id),
        "highlights": [f"R:{B}:{EXTRA}", f"R:{B}:{rid}", f"Q:{QA}:production_lead_time"],
        "tradeoffs": [{"relation": "SAME_REQUIREMENT",
                       "fact_ids": [f"R:{A}:{EXTRA}", f"R:{B}:{EXTRA}"]}],
        "verification_actions": [],
        "suggestion": {"supplier_id": None, "reason_fact_ids": [],
                       "no_suggestion_reason": "NO_CLEAR_PREFERENCE"},
    }


def replacement(slot: str, value: Any) -> dict[str, Any]:
    return {"slot_id": slot, "op": "replace", "value": value}


CASES = [
    ("quote-fixed", None), ("unknown-field", "STATE_REFERENCE"),
    ("unknown-quote", "STATE_REFERENCE"), ("owner-fixed", None),
    ("wrong-owner", "STATE_REFERENCE"), ("failed-support", "STATE_REFERENCE"),
    ("action-fixed", None), ("wrong-action", "STATE_REFERENCE"),
    ("both-fixed", None), ("partial", "STATE_REFERENCE"),
    ("duplicate-slot", "STATE_REFERENCE"), ("frozen-slot", "STATE_REFERENCE"),
    ("unknown-slot", "STATE_REFERENCE"), ("wrong-snapshot", "STATE_REFERENCE"),
    ("extra-state", "SCHEMA_INVALID"), ("extra-text", "SCHEMA_INVALID"),
    ("extra-value", "SCHEMA_INVALID"), ("malformed-fixed", None),
    ("legacy-fixed", None), ("stale-fixed", None),
    ("legacy-again", "SCHEMA_INVALID"), ("malformed-again", "SCHEMA_INVALID"),
]


@pytest.mark.parametrize("kind", ["numeric", "boolean"])
@pytest.mark.parametrize("case,terminal", CASES)
def test_real_combined_entry_point_preserving_repair(
    monkeypatch: pytest.MonkeyPatch, kind: str, case: str, terminal: str | None,
) -> None:
    snapshot, base, _, _ = reference_fixture(kind)
    # The old prose fixture omits this definition in its boolean variant. Supply
    # the domain-valid value needed by verification rendering on this local copy.
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    payload["brief"]["requirements"][1].setdefault("expected_value", {"max_days": 40})
    original, base_before = deepcopy(snapshot), deepcopy(base)
    good = selection(snapshot, kind)
    draft = deepcopy(good)
    draft["highlights"][2] = f"Q:{QA}:max_days"
    edits = [replacement("highlights[2]", f"Q:{QA}:production_lead_time")]
    slots = ["highlights[2]"]
    corrected = deepcopy(good)
    if case in {"owner-fixed", "wrong-owner", "failed-support"}:
        draft = deepcopy(good)
        draft["suggestion"] = {"supplier_id": A, "reason_fact_ids": [f"R:{B}:{EXTRA}"],
                               "no_suggestion_reason": None}
        corrected["suggestion"] = {"supplier_id": A, "reason_fact_ids": [f"R:{A}:{EXTRA}"],
                                   "no_suggestion_reason": None}
        edits = [replacement("suggestion", corrected["suggestion"])]
        slots = ["suggestion"]
        if case == "wrong-owner":
            edits[0]["value"] = deepcopy(draft["suggestion"])
        elif case == "failed-support":
            edits[0]["value"] = {**corrected["suggestion"], "reason_fact_ids": [f"R:{A}:{LEAD}"]}
    if case in {"action-fixed", "wrong-action", "both-fixed", "partial"}:
        if case in {"action-fixed", "wrong-action"}:
            draft = deepcopy(good)
            edits, slots = [], []
        draft["verification_actions"] = [{"action": "CONFIRM_MISSING", "fact_id": f"R:{A}:{LEAD}"}]
        corrected["verification_actions"] = [{"action": "RESOLVE_CONFLICT", "fact_id": f"R:{A}:{LEAD}"}]
        slots.append("verification_actions[0]")
        if case != "partial":
            edits.append(replacement("verification_actions[0]", corrected["verification_actions"][0]))
        if case == "wrong-action":
            edits[0]["value"] = deepcopy(draft["verification_actions"][0])
    if case == "unknown-field":
        edits[0]["value"] = f"Q:{QA}:max_days"
    elif case == "unknown-quote":
        edits[0]["value"] = f"Q:{FOREIGN}:production_lead_time"
    elif case == "duplicate-slot":
        edits.append(deepcopy(edits[0]))
    elif case == "frozen-slot":
        edits.append(replacement("highlights[0]", f"R:{A}:{EXTRA}"))
    elif case == "unknown-slot":
        edits.append(replacement("highlights[99]", f"R:{A}:{EXTRA}"))
    patch: dict[str, Any] = {"version": "comparison-selection-repair-v1",
                             "snapshot_id": str(snapshot.snapshot_id), "replacements": edits}
    if case == "wrong-snapshot":
        patch["snapshot_id"] = FOREIGN
    if case.startswith("extra-"):
        patch[case.removeprefix("extra-")] = "untrusted sentinel"
    full_repair = case in {"malformed-fixed", "legacy-fixed", "stale-fixed",
                           "legacy-again", "malformed-again"}
    first = json.dumps(draft)
    second = json.dumps(patch)
    initial_code, initial_phase = "STATE_REFERENCE", "analysis_initial"
    if full_repair:
        second = json.dumps(good)
        if case == "stale-fixed":
            draft = {**good, "snapshot_id": FOREIGN}
            first = json.dumps(draft)
        else:
            first = ("{" if case.startswith("malformed") else json.dumps({"analysis": base}))
            initial_code, initial_phase = "SCHEMA_INVALID", "schema_initial"
        if case in {"legacy-again", "malformed-again"}:
            second = first
    responses = [first, second]
    inputs_before = deepcopy((good, draft, patch, responses))
    requests: list[dict[str, Any]] = []
    stored: list[Any] = []
    tasks: list[AdviceSelectionTask] = []
    freshness: list[dict[str, Any]] = []
    membership_queries: list[Any] = []

    class MemorySession:
        no_autoflush = nullcontext()

        def add(self, item: Any) -> None:
            if isinstance(item, AIRun):
                item.id = uuid4()
            stored.append(item)

        def commit(self) -> None:
            pass

        def scalars(self, query: Any) -> list[UUID]:
            membership_queries.append(query)
            return [UUID(A), UUID(B), UUID(C)]

    class Model:
        model = "provider-blocked-real-v10-entry-point"

        def invoke_with_tools(self, **kwargs: Any) -> AnalystModelInvocation:
            requests.append(deepcopy(kwargs))
            return AnalystModelInvocation(responses[min(len(requests) - 1, 1)], (), 2, 1)

    def current(*args: Any, **kwargs: Any) -> ComparisonSnapshotResult:
        freshness.append(kwargs)
        return snapshot

    def capture_task(bound: ComparisonSnapshotResult) -> AdviceSelectionTask:
        task = AdviceSelectionTask(bound)
        tasks.append(task)
        return task

    monkeypatch.setenv("SOURCEPILOT_LANGFUSE_ENABLED", "false")
    monkeypatch.setattr(runtime, "_current_snapshot", current)
    monkeypatch.setattr(advice, "AdviceSelectionTask", capture_task)
    project_id, session_id = uuid4(), uuid4()
    assert snapshot.snapshot_id is not None
    # Existing nested-deadline path avoids acquiring a real DB connection; the
    # public wrapper, membership validator, shared runtime and selection task run.
    token = current_deadline.set(ComparisonDeadline())
    result = None
    try:
        if terminal is None:
            result = advice.analyze_comparison_advice(
                cast(Session, MemorySession()), demo_session_id=session_id, project_id=project_id,
                snapshot_id=snapshot.snapshot_id, client_factory=cast(Any, Model))
        else:
            with pytest.raises(runtime.TradeoffUnavailableError):
                advice.analyze_comparison_advice(
                    cast(Session, MemorySession()), demo_session_id=session_id, project_id=project_id,
                    snapshot_id=snapshot.snapshot_id, client_factory=cast(Any, Model))
    finally:
        current_deadline.reset(token)
    run = next(item for item in stored if isinstance(item, AIRun))
    steps = [item for item in stored if isinstance(item, SupplierExplanationRunStep)]
    assert len(requests) == run.model_turn_count == run.attempts == 2
    assert run.tool_call_count == 0
    assert run.status == ("COMPLETED" if terminal is None else "VALIDATION_FAILED")
    assert run.validation_status == ("REPAIRED" if terminal is None else "INVALID")
    assert run.error_type == terminal
    assert run.prompt_version == "comparison-advice-v10"
    assert run.operation == "comparison_advice"
    assert [s.name for s in steps if s.kind == "validation" and s.outcome == "INVALID"] == (
        [initial_code] + ([] if terminal is None else [terminal]))
    assert [s.name for s in steps if s.kind == "validation_phase"] == (
        [initial_phase] + ([] if terminal is None else [
            "schema_repair" if terminal == "SCHEMA_INVALID" else "analysis_repair"]))
    assert sum(s.kind == "retry" and s.outcome == "REPAIR" for s in steps) == 1
    assert [r["schema_name"] for r in requests] == [
        "ComparisonSelectionV1", "ComparisonSelectionV1" if full_repair else "SelectionRepairV1"]
    assert requests[1]["input_items"] == requests[0]["input_items"] + [
        {"role": "assistant", "content": first}]
    assert first not in requests[1]["instructions"]
    assert "untrusted sentinel" not in requests[1]["instructions"]
    context = json.loads(requests[0]["input_items"][0]["content"])
    rid = LEAD if kind == "numeric" else BRANDING
    assert context["fact_catalogue"][f"R:{B}:{EXTRA}"]["supplier_index"] == 1
    assert context["fact_catalogue"][f"R:{B}:{rid}"]["supplier_index"] == 1
    assert context["fact_catalogue"][f"Q:{QA}:production_lead_time"]["supplier_index"] == 0
    assert len(tasks) == 1
    if not full_repair:
        task = tasks[0]
        assert task.draft is not None
        assert task.draft.model_dump(mode="json") == draft  # Frozen original never overwritten.
        assert list(task.issues) == slots
        schema_slots = {v["properties"]["slot_id"]["enum"][0] for v in
                        requests[1]["schema"]["properties"]["replacements"]["items"]["anyOf"]}
        assert schema_slots == set(slots)
        assert "All other slots are frozen" in requests[1]["instructions"]
    assert len(membership_queries) == 2
    assert all(project_id in query.compile().params.values() for query in membership_queries)
    assert len(freshness) == 2
    assert all(call["project_id"] == project_id and call["demo_session_id"] == session_id
               for call in freshness)
    assert freshness[1]["expected"] is snapshot
    assert snapshot == original and base == base_before
    assert (good, draft, patch, responses) == inputs_before
    if terminal is None:
        assert result is not None, "Successful repair must return an advice response."
        assert result.snapshot_id == snapshot.snapshot_id and result.run_id == run.id
        advice.validate_advice(result, snapshot)
        summaries = result.analysis.supplier_summaries
        assert str(summaries[0].requirement_ids[0]) == EXTRA
        assert str(summaries[0].supplier_ids[0]) == B
        assert summaries[0].text == "Supplier B requirement is MEETS."
        repeated = (summaries[1] if kind == "numeric" else result.analysis.key_tradeoffs[0])
        assert [str(value) for value in repeated.requirement_ids] == [rid]
        assert [str(value) for value in repeated.supplier_ids] == [B]
        assert repeated.text == ("Supplier B requirement is MEETS." if kind == "numeric"
                                 else "Supplier B requirement is DOES_NOT_MEET.")
        assert any(str(p.supplier_ids[0]) == A and str(p.requirement_ids[0]) == LEAD
                   and "CONFLICT" in p.text for p in result.analysis.important_conflicts)
        assert any(str(p.supplier_ids[0]) == C and str(p.requirement_ids[0]) == CERT
                   and "UNKNOWN" in p.text for p in result.analysis.important_unknowns)
        assert str(result.suggestion.supplier_id) == (A if case == "owner-fixed" else "None")
        assert any([str(value) for value in point.supplier_ids] == [A, B]
                   and [str(value) for value in point.requirement_ids] == [EXTRA]
                   and "Supplier A requirement is MEETS." in point.text
                   and "Supplier B requirement is MEETS." in point.text
                   for point in result.analysis.key_tradeoffs)
        assert any([str(value) for value in point.supplier_ids] == [A]
                   and [(str(ref.quote_id), ref.field_key) for ref in point.quote_fields]
                   == [(QA, "production_lead_time")]
                   and "25 days" in point.text for point in summaries)
        if case in {"action-fixed", "both-fixed"}:
            action = next(point for point in result.analysis.key_tradeoffs
                          if "Reconcile the source records" in point.text)
            assert [str(value) for value in action.supplier_ids] == [A]
            assert [str(value) for value in action.requirement_ids] == [LEAD]
            assert "40" in action.text and "CONFLICT" in action.text
        if case == "owner-fixed":
            assert all([str(value) for value in point.supplier_ids] == [A]
                       for point in result.suggestion.supporting_reasons)
            assert any([str(value) for value in point.requirement_ids] == [EXTRA]
                       for point in result.suggestion.supporting_reasons)
        # Independent negative controls against the actual assembled public result.
        for mutation, code in (("state", "STATE_CONTRADICTION"),
                               ("owner", "QUOTE_OWNER_MISMATCH"), ("field", "QUOTE_REFERENCE")):
            changed = result.model_copy(deep=True)
            point = changed.analysis.supplier_summaries[0]
            if mutation == "state":
                point.text = "Supplier B requirement is UNKNOWN."
            else:
                point.quote_fields = [runtime.QuoteFieldReference(
                    quote_id=UUID(QA if mutation == "owner" else QB),
                    field_key="production_lead_time" if mutation == "owner" else "max_days")]
            with pytest.raises(ComparisonRejection) as failure:
                advice.validate_advice(changed, snapshot)
            assert failure.value.code.value == code
