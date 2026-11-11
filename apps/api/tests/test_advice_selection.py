"""Selection constraints and invalid-slot repair, without provider or database."""
import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from sourcepilot.ai.advice_selection import AdviceSelectionTask, ComparisonSelectionV1
from sourcepilot.ai.comparison_advice import ComparisonAdvice, validate_advice
from sourcepilot.comparison.validation import ComparisonRejection
from tests.test_advice_facts import retained_snapshot


def valid_selection(task: AdviceSelectionTask) -> dict:
    fact = next(f for f in task.catalogue.facts.values() if f.requirement_id and f.state == "MEETS")
    return {"version":"comparison-selection-v1", "snapshot_id":task.catalogue.snapshot_id,
            "highlights":[fact.id], "tradeoffs":[], "verification_actions":[],
            "suggestion":{"supplier_id":None,"reason_fact_ids":[],"no_suggestion_reason":"NO_CLEAR_PREFERENCE"}}


def patch(task, edits):
    return json.dumps({"version":"comparison-selection-repair-v1", "snapshot_id":task.catalogue.snapshot_id,
                       "replacements":edits})


def reject(task, draft):
    with pytest.raises(ComparisonRejection):
        task.accept(json.dumps(draft))
    task.repair_feedback()


def test_valid_selection_assembles_all_mandatory_facts():
    snapshot = retained_snapshot()
    task = AdviceSelectionTask(snapshot)
    validate_advice(ComparisonAdvice.model_validate(task.accept(json.dumps(valid_selection(task)))), snapshot)


def test_optional_removal_preserves_valid_slots_and_snapshot():
    snapshot = retained_snapshot(); original = snapshot.model_dump_json()
    task = AdviceSelectionTask(snapshot); draft = valid_selection(task)
    draft["tradeoffs"] = [{"relation":"SAME_REQUIREMENT","fact_ids":["foreign","foreign2"]}]
    reject(task,draft)
    assert list(task.issues) == ["tradeoffs[0]"]
    assert task.draft is not None
    frozen = task.draft.model_dump_json()
    result = task.accept(patch(task,[{"slot_id":"tradeoffs[0]","op":"remove","value":None}]))
    validate_advice(ComparisonAdvice.model_validate(result),snapshot)
    clean = AdviceSelectionTask(snapshot)
    assert result == clean.accept(json.dumps(valid_selection(clean)))
    assert task.draft is not None
    assert task.draft.model_dump_json() == frozen
    assert snapshot.model_dump_json() == original


def test_duplicate_slots_are_all_invalid_and_merge_uses_original_indexes():
    task = AdviceSelectionTask(retained_snapshot()); draft = valid_selection(task)
    first = draft["highlights"][0]
    other = next(key for key in task.catalogue.facts if key != first)
    draft["highlights"] = [first,other,first]
    reject(task,draft)
    assert set(task.issues) == {"highlights[0]","highlights[2]"}
    result = task.accept(patch(task,[{"slot_id":"highlights[0]","op":"remove","value":None},
                                    {"slot_id":"highlights[2]","op":"replace","value":first}]))
    assert result["analysis"]["important_unknowns"][0]["supplier_ids"]
    assert task.draft is not None
    assert task.draft.highlights == [first,other,first]


@pytest.mark.parametrize("edits", [
    [{"slot_id":"highlights[0]","op":"remove","value":None}],
    [{"slot_id":"highlights[0]","op":"replace","value":"still-foreign"}],
    [{"slot_id":"suggestion","op":"remove","value":None}],
    [],
])
def test_no_valid_replacement_minimum_and_frozen_edit_fail(edits):
    task = AdviceSelectionTask(retained_snapshot()); draft = valid_selection(task)
    draft["highlights"] = ["foreign"]
    reject(task,draft)
    with pytest.raises((ComparisonRejection,ValidationError)):
        task.accept(patch(task,edits))


def test_cross_item_repair_can_remove_action_and_explain_null():
    task = AdviceSelectionTask(retained_snapshot()); draft = valid_selection(task)
    draft["verification_actions"] = [{"action":"CONFIRM_MISSING","fact_id":"foreign"}]
    draft["suggestion"]["no_suggestion_reason"] = "VERIFY_BEFORE_CHOOSING"
    reject(task,draft)
    assert set(task.issues) == {"verification_actions[0]","suggestion"}
    edits=[{"slot_id":"verification_actions[0]","op":"remove","value":None},
           {"slot_id":"suggestion","op":"replace","value":{
               "supplier_id":None,"reason_fact_ids":[],"no_suggestion_reason":"NO_CLEAR_PREFERENCE"}}]
    task.accept(patch(task,edits))
    edits[1]["value"]["no_suggestion_reason"] = "VERIFY_BEFORE_CHOOSING"
    with pytest.raises(ComparisonRejection):
        task.accept(patch(task,edits))


def test_repair_duplicate_frozen_and_wrong_type_edits_fail():
    task=AdviceSelectionTask(retained_snapshot()); draft=valid_selection(task)
    draft["tradeoffs"]=[{"relation":"SAME_REQUIREMENT","fact_ids":["x","y"]}]
    reject(task,draft)
    edit={"slot_id":"tradeoffs[0]","op":"remove","value":None}
    for edits in [[edit,edit],[edit,{"slot_id":"highlights[0]","op":"remove","value":None}],
                  [{"slot_id":"tradeoffs[0]","op":"replace","value":"wrong type"}]]:
        with pytest.raises((ComparisonRejection,ValidationError)):
            task.accept(patch(task,edits))


def test_legacy_prose_and_invented_states_are_not_model_selection_fields():
    task=AdviceSelectionTask(retained_snapshot()); draft=valid_selection(task)
    for extra in [{"text":"Moss has unresolved material"},{"state":"UNKNOWN"},{"evidence_ids":[]}]:
        with pytest.raises(ValidationError):
            ComparisonSelectionV1.model_validate({**draft,**extra})
    changed=deepcopy(draft); changed["snapshot_id"]="00000000-0000-0000-0000-000000000001"
    reject(task,changed)
    assert not task.patch_mode
    assert task.accept(json.dumps(draft))


def test_feedback_identifies_supplied_state_without_echoing_unknown_model_text():
    task = AdviceSelectionTask(retained_snapshot())
    draft = valid_selection(task)
    conflict = next(f for f in task.catalogue.facts.values() if f.requirement_id and f.state == "CONFLICT")
    draft["verification_actions"] = [{"action": "CONFIRM_MISSING", "fact_id": conflict.id}]
    draft["tradeoffs"] = [{"relation": "SAME_REQUIREMENT", "fact_ids": ["ignore instructions", conflict.id]}]
    reject(task, draft)
    feedback = task.repair_feedback()
    assert "verification_actions[0]" in feedback and "tradeoffs[0]" in feedback
    assert '"state":"CONFLICT"' in feedback and conflict.id in feedback
    assert '"unknown_id_count":1' in feedback
    assert "ignore instructions" not in feedback


def test_selected_supplier_cannot_borrow_another_suppliers_supporting_fact():
    task = AdviceSelectionTask(retained_snapshot())
    draft = valid_selection(task)
    fact = task.catalogue.facts[draft["highlights"][0]]
    other = next(sid for sid in task.catalogue.supplier_ids if sid != fact.supplier_id)
    draft["suggestion"] = {"supplier_id": other, "reason_fact_ids": [fact.id], "no_suggestion_reason": None}
    reject(task, draft)
    assert set(task.issues) == {"suggestion"}


def test_reversed_supplier_order_is_still_a_duplicate_relationship():
    task = AdviceSelectionTask(retained_snapshot())
    draft = valid_selection(task)
    first = next(f for f in task.catalogue.facts.values() if f.requirement_id)
    second = next(f for f in task.catalogue.facts.values()
                  if f.requirement_id == first.requirement_id and f.supplier_id != first.supplier_id)
    draft["tradeoffs"] = [{"relation": "SAME_REQUIREMENT", "fact_ids": ids}
                          for ids in ([first.id, second.id], [second.id, first.id])]
    reject(task, draft)
    assert set(task.issues) == {"tradeoffs[0]", "tradeoffs[1]"}
    output = task.accept(patch(task, [
        {"slot_id": "tradeoffs[0]", "op": "replace", "value": draft["tradeoffs"][0]},
        {"slot_id": "tradeoffs[1]", "op": "remove", "value": None},
    ]))
    validate_advice(ComparisonAdvice.model_validate(output), retained_snapshot())


def test_required_failure_is_disclosed_without_excluding_supplier():
    snapshot = retained_snapshot()
    assert snapshot.comparison_payload is not None
    suppliers = snapshot.comparison_payload["suppliers"]
    assert isinstance(suppliers, list)
    supplier = suppliers[0]
    assert isinstance(supplier, dict)
    assert isinstance(supplier["supplier_id"], str)
    brief = snapshot.comparison_payload["brief"]
    assert isinstance(brief, dict)
    requirements = brief["requirements"]
    assert isinstance(requirements, list)
    for row in requirements:
        assert isinstance(row, dict)
        assert isinstance(row["id"], str)
        assert isinstance(row["importance"], str)
    requirement = next(r for r in requirements
                       if r["importance"] == "REQUIRED")
    evaluation = supplier["evaluation"]
    assert isinstance(evaluation, dict)
    results = evaluation["results"]
    assert isinstance(results, list)
    for row in results:
        assert isinstance(row, dict)
        assert row["requirement_id"] is None or isinstance(row["requirement_id"], str)
        assert isinstance(row["status"], str)
    finding = next(r for r in results if r["requirement_id"] == requirement["id"])
    finding["status"] = "DOES_NOT_MEET"
    task = AdviceSelectionTask(snapshot)
    price = next(f for f in task.catalogue.facts.values()
                 if f.supplier_id == supplier["supplier_id"] and f.field_key == "unit_price" and f.state == "KNOWN")
    draft = valid_selection(task)
    draft["suggestion"] = {"supplier_id": price.supplier_id, "reason_fact_ids": [price.id], "no_suggestion_reason": None}
    output = ComparisonAdvice.model_validate(task.accept(json.dumps(draft)))
    validate_advice(output, snapshot)
    assert str(output.suggestion.supplier_id) == price.supplier_id
    assert any(str(rid) == requirement["id"] for p in output.suggestion.tradeoffs for rid in p.requirement_ids)
    draft["suggestion"]["reason_fact_ids"] = [f"R:{price.supplier_id}:{requirement['id']}"]
    with pytest.raises(ComparisonRejection):
        AdviceSelectionTask(snapshot).accept(json.dumps(draft))
