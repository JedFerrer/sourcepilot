"""Actual rejected outputs remain negative controls for deterministic assembly."""

import json
from pathlib import Path
from uuid import UUID

import pytest

from sourcepilot.ai.advice_selection import AdviceSelectionTask
from sourcepilot.ai.comparison_advice import ComparisonAdvice, validate_advice
from sourcepilot.ai.tradeoff_analysis import _validate_state_assertions
from sourcepilot.comparison.advice import AnalysisPoint
from sourcepilot.comparison.validation import ComparisonRejection, RejectionCode
from tests.test_advice_facts import retained_snapshot
from tests.test_advice_selection import valid_selection


@pytest.mark.parametrize("version,code", [("initial", RejectionCode.STATE_REFERENCE),
                                         ("repair", RejectionCode.STATE_SYNTAX)])
def test_retained_rejections_and_application_coverage(version, code):
    path = Path(__file__).parents[1] / "evals/comparison_advice/retained_failure_cases.json"
    original_bytes = path.read_bytes()
    rejected = ComparisonAdvice.model_validate(json.loads(original_bytes)[version])
    snapshot = retained_snapshot()
    with pytest.raises(ComparisonRejection) as failure:
        validate_advice(rejected, snapshot)
    assert failure.value.code == code
    task = AdviceSelectionTask(snapshot)
    assembled = ComparisonAdvice.model_validate(task.accept(json.dumps(valid_selection(task))))
    validate_advice(assembled, snapshot)
    expected = {(f.supplier_id, f.requirement_id) for f in task.catalogue.facts.values()
                if f.requirement_id and f.state == "UNKNOWN"}
    old = {(str(sid), str(rid)) for p in rejected.analysis.important_unknowns
           for sid in p.supplier_ids for rid in p.requirement_ids}
    assert len(expected - old) == (2 if version == "initial" else 1)
    new = {(str(sid), str(rid)) for p in assembled.analysis.important_unknowns
           for sid in p.supplier_ids for rid in p.requirement_ids}
    assert new == expected
    assert any(p.text == "Sunrise Textile Lab certification is CONFLICT."
               for p in assembled.analysis.important_conflicts)
    assert any(p.text == "Moss Thread Bags material is MEETS."
               for p in assembled.analysis.supplier_summaries)
    assert path.read_bytes() == original_bytes


def test_latent_contradiction_and_unresolved_parser_gap_are_not_success():
    path = Path(__file__).parents[1] / "evals/comparison_advice/retained_failure_cases.json"
    outputs = json.loads(path.read_bytes())
    snapshot = retained_snapshot()
    payload = snapshot.comparison_payload
    assert payload is not None
    suppliers = payload["suppliers"]
    assert isinstance(suppliers, list)
    brief = payload["brief"]
    assert isinstance(brief, dict)
    requirement_rows = brief["requirements"]
    assert isinstance(requirement_rows, list)
    for requirement in requirement_rows:
        assert isinstance(requirement, dict)
        assert isinstance(requirement["id"], str)
    for supplier in suppliers:
        assert isinstance(supplier, dict)
        assert isinstance(supplier["supplier_id"], str)
        assert isinstance(supplier["quote_id"], str)
        evaluation = supplier["evaluation"]
        assert isinstance(evaluation, dict)
        results = evaluation["results"]
        assert isinstance(results, list)
        for result in results:
            assert isinstance(result, dict)
            assert result["requirement_id"] is None or isinstance(result["requirement_id"], str)
            assert isinstance(result["status"], str)
        fields = supplier["completeness"]
        assert isinstance(fields, list)
        for field in fields:
            assert isinstance(field, dict)
            assert isinstance(field["field_key"], str)
            assert isinstance(field["state"], str)
    requirements = {UUID(r["id"]): r for r in requirement_rows}
    states = {(UUID(s["supplier_id"]), UUID(r["requirement_id"])): r["status"] for s in suppliers
              for r in s["evaluation"]["results"] if r["requirement_id"] is not None}
    owners = {UUID(s["quote_id"]): UUID(s["supplier_id"]) for s in suppliers}
    completeness = {(UUID(s["quote_id"]), f["field_key"]): f["state"]
                    for s in suppliers for f in s["completeness"]}
    wrong = AnalysisPoint.model_validate(outputs["initial"]["analysis"]["important_unknowns"][3])
    with pytest.raises(ComparisonRejection) as failure:
        _validate_state_assertions(wrong, suppliers, requirements, states, owners, completeness)
    assert failure.value.code == RejectionCode.STATE_CONTRADICTION
    grouped = AnalysisPoint.model_validate(outputs["repair"]["analysis"]["key_tradeoffs"][2])
    isolated = grouped.model_copy(update={"text": grouped.text.split(".")[0] + "."})
    assert "Moss Thread Bags has an unresolved required material" in isolated.text
    # Preserve the demonstrated semantic gap; passing this parser is insufficient.
    _validate_state_assertions(isolated, suppliers, requirements, states, owners, completeness)
    material = next(f for f in AdviceSelectionTask(snapshot).catalogue.facts.values()
                    if f.supplier_name == "Moss Thread Bags" and f.requirement_id
                    and f.source["requirement"]["kind"] == "MATERIAL")
    assert material.state == "MEETS"
