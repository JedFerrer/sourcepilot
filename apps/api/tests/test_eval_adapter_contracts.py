"""Independent semantic/provenance oracles for the executable eval adapter."""

import json
from copy import deepcopy
from typing import Any, cast
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from sourcepilot.ai import eval_live
from sourcepilot.ai.advice_selection import AdviceSelectionTask, selection_context
from sourcepilot.ai.analyst_tools import (
    AnalystToolContext,
    AnalystToolRuntime,
    get_quote_evidence,
)
from sourcepilot.ai.comparison_advice import ComparisonAdvice
from sourcepilot.ai.comparison_advice_eval import scenario_snapshot, score_case
from sourcepilot.ai.eval_baseline import load_scope
from sourcepilot.ai.eval_live import canonical_quote_field, comparison_fixture, fresh_project
from sourcepilot.ai.tradeoff_analysis_eval import CERT, LEAD, PDF_PRICE, QA, QB, QC, A, B, C
from sourcepilot.comparison.validation import ComparisonRejection
from sourcepilot.persistence.models import Comparison, Project, Quote, QuoteValue
from tests.test_eval_live import comparison_identities, scenario_selection
from tests.test_eval_live import session as _adapter_session

adapter_session = _adapter_session


def scenario(case_id: str) -> dict[str, Any]:
    return next(c for c in load_scope(["suggestion"])["suggestion"] if c["id"] == case_id)


def prepared(case_id: str = "clear-suggestion") -> tuple[Any, dict[str, Any], dict[str, str]]:
    snapshot = scenario_snapshot(scenario(case_id))
    original = deepcopy(snapshot.comparison_payload)
    assert original is not None and snapshot.comparison_payload is not None
    brief = snapshot.comparison_payload["brief"]
    suppliers = snapshot.comparison_payload["suppliers"]
    assert isinstance(brief, dict) and isinstance(suppliers, list)
    for requirement in brief["requirements"]:
        requirement["expected_value"] = (
            {"value": "GRS"} if requirement["kind"] == "CERTIFICATION" else {"max_days": 30})
    for supplier in suppliers:
        supplier["quote_fields"] = [canonical_quote_field(supplier, f)
                                    for f in supplier["quote_fields"]]
    # Independent fixture association, standing in for persisted Quote rows.
    # Never derive this oracle from the projected suppliers being tested.
    snapshot.quote_revision_snapshot = {
        A: {"quote_id": QA, "revision": 1},
        B: {"quote_id": QB, "revision": 1},
        C: {"quote_id": QC, "revision": 1},
    }
    initial = selection_context(snapshot)
    ids = comparison_identities(original, initial, str(snapshot.snapshot_id))
    return snapshot, initial, ids


def test_mapping_is_order_independent_and_preserves_completeness_only() -> None:
    snapshot, initial, _ = prepared()
    expected = {key: key for key in (str(snapshot.snapshot_id), CERT, LEAD, A, B, C,
                                    QA, QB, QC, PDF_PRICE)}
    old = cast(dict[str, Any], scenario_snapshot(scenario("clear-suggestion")).comparison_payload)
    initial["comparison_payload"]["suppliers"].reverse()
    initial["comparison_payload"]["brief"]["requirements"].reverse()
    for supplier in initial["comparison_payload"]["suppliers"]:
        supplier["quote_fields"].reverse()
    assert comparison_identities(old, initial, str(snapshot.snapshot_id)) == expected
    third = next(s for s in initial["comparison_payload"]["suppliers"] if s["supplier_id"] == C)
    shipping = next(f for f in third["quote_fields"] if f["field_key"] == "shipping_cost")
    assert shipping == {"field_key": "shipping_cost", "completeness": {"state": "missing"}}


@pytest.mark.parametrize("damage", ["missing", "duplicate", "extra", "wrong-field",
                                    "wrong-owner", "quote-collision", "fabricated-missing"])
def test_mapping_rejects_identity_and_evidence_damage(damage: str) -> None:
    snapshot, initial, _ = prepared()
    old = cast(dict[str, Any], scenario_snapshot(scenario("clear-suggestion")).comparison_payload)
    suppliers = initial["comparison_payload"]["suppliers"]
    fields = suppliers[0]["quote_fields"]
    if damage == "missing":
        fields.pop()
    elif damage == "duplicate":
        fields.append(deepcopy(fields[0]))
    elif damage == "extra":
        fields.append({"field_key": "invented"})
    elif damage == "wrong-field":
        fields[1]["evidence"], fields[0]["evidence"] = fields[0]["evidence"], []
    elif damage == "wrong-owner":
        suppliers[1]["quote_fields"][0]["evidence"] = fields[0]["evidence"]
        fields[0]["evidence"] = []
    elif damage == "quote-collision":
        suppliers[1]["quote_id"] = suppliers[0]["quote_id"]
    else:
        suppliers[2]["quote_fields"][-1]["current_value"] = 0
    with pytest.raises(AssertionError):
        comparison_identities(old, initial, str(snapshot.snapshot_id))


@pytest.mark.parametrize("side", ["source", "projected"])
@pytest.mark.parametrize("collision", [
    "requirement", "supplier", "quote", "requirement-supplier", "requirement-quote",
    "supplier-quote", "snapshot-requirement", "evidence-requirement", "evidence-quote",
    "evidence",
])
def test_mapping_rejects_collisions_before_binding(side: str, collision: str) -> None:
    snapshot, initial, _ = prepared()
    old = cast(dict[str, Any], deepcopy(scenario_snapshot(scenario("clear-suggestion")).comparison_payload))
    assert old is not None
    payload = old if side == "source" else initial["comparison_payload"]
    requirements = payload["brief"]["requirements"]
    suppliers = payload["suppliers"]
    if collision == "requirement":
        requirements[1]["id"] = requirements[0]["id"]
    elif collision in {"supplier", "quote"}:
        suppliers[1][f"{collision}_id"] = suppliers[0][f"{collision}_id"]
    elif collision.startswith("requirement-"):
        requirements[0]["id"] = suppliers[0][f"{collision.split('-')[1]}_id"]
    elif collision == "supplier-quote":
        suppliers[0]["quote_id"] = suppliers[0]["supplier_id"]
    elif collision == "snapshot-requirement":
        requirements[0]["id"] = str(snapshot.snapshot_id)
    else:
        evidence = suppliers[0]["quote_fields"][0]["evidence"]
        if collision == "evidence":
            suppliers[1]["quote_fields"][0]["evidence"] = deepcopy(evidence)
        else:
            evidence[0]["id"] = (requirements[0]["id"] if collision == "evidence-requirement"
                                  else suppliers[0]["quote_id"])
    with pytest.raises(AssertionError, match="Duplicate or conflicting identity"):
        comparison_identities(old, initial, str(snapshot.snapshot_id))


@pytest.mark.parametrize("side", ["source", "projected"])
def test_mapping_rejects_swapped_owners_with_equal_quote_values(side: str) -> None:
    snapshot, initial, _ = prepared("tie")
    old = cast(dict[str, Any], deepcopy(scenario_snapshot(scenario("tie")).comparison_payload))
    assert old is not None
    payload = old if side == "source" else initial["comparison_payload"]
    first, second = payload["suppliers"][:2]
    assert {f["field_key"]: f["current_value"] for f in first["quote_fields"]} == {
        f["field_key"]: f["current_value"] for f in second["quote_fields"]}
    first["quote_id"], second["quote_id"] = second["quote_id"], first["quote_id"]
    with pytest.raises(AssertionError, match="quote owner mismatch"):
        comparison_identities(old, initial, str(snapshot.snapshot_id))


@pytest.mark.parametrize("damage", ["absent", "missing", "extra", "swapped"])
def test_mapping_requires_complete_independent_owner_association(damage: str) -> None:
    snapshot, initial, _ = prepared()
    old = scenario_snapshot(scenario("clear-suggestion")).comparison_payload
    assert old is not None
    if damage == "absent":
        initial["quote_revision_snapshot"] = None
    elif damage == "missing":
        del initial["quote_revision_snapshot"][B]
    elif damage == "extra":
        initial["quote_revision_snapshot"][str(uuid4())] = {"quote_id": str(uuid4())}
    else:
        initial["quote_revision_snapshot"][A]["quote_id"] = QB
        initial["quote_revision_snapshot"][B]["quote_id"] = QA
    with pytest.raises(AssertionError):
        comparison_identities(old, initial, str(snapshot.snapshot_id))


@pytest.mark.parametrize("reorder", [False, True])
@pytest.mark.parametrize("remap", [False, True])
def test_mapping_matches_independent_expected_identities(reorder: bool, remap: bool) -> None:
    snapshot, initial, _ = prepared()
    old = cast(dict[str, Any], deepcopy(scenario_snapshot(scenario("clear-suggestion")).comparison_payload))
    assert old is not None
    keys = (str(snapshot.snapshot_id), CERT, LEAD, A, B, C, QA, QB, QC, PDF_PRICE)
    expected = {key: str(UUID(int=100 + i)) if remap else key for i, key in enumerate(keys)}
    initial = eval_live.remap(initial, expected)
    if reorder:
        for payload in (old, initial["comparison_payload"]):
            payload["suppliers"].reverse()
            payload["brief"]["requirements"].reverse()
            for supplier in payload["suppliers"]:
                supplier["quote_fields"].reverse()
    assert comparison_identities(old, initial, str(snapshot.snapshot_id)) == expected


@pytest.mark.parametrize("collision", ["requirement", "snapshot", "supplier", "quote", "evidence"])
def test_fixture_rejects_requirement_collisions_before_persistence(
    monkeypatch: pytest.MonkeyPatch, collision: str,
) -> None:
    case = scenario("clear-suggestion")
    snapshot = scenario_snapshot(case)
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    payload["brief"]["requirements"][1]["id"] = {
        "requirement": CERT, "snapshot": str(snapshot.snapshot_id),
        "supplier": A, "quote": QA, "evidence": PDF_PRICE,
    }[collision]
    monkeypatch.setattr(eval_live, "scenario_snapshot", lambda _case: snapshot)
    session = Mock(spec=Session)
    with pytest.raises(ValueError, match="Duplicate fixture identity"):
        comparison_fixture(session, Project(), case)
    assert session.mock_calls == []


def test_mapping_checks_persisted_quote_owners(adapter_session: Session) -> None:
    case = scenario("tie")
    _, project = fresh_project(adapter_session, case)
    original, expected = comparison_fixture(adapter_session, project, case)
    saved = adapter_session.get(Comparison, UUID(expected[case["snapshot_id"]]))
    assert saved is not None
    quotes = adapter_session.scalars(select(Quote).where(Quote.project_id == project.id)).all()
    owners = {str(q.supplier_id): str(q.id) for q in quotes}
    assert owners == {expected[A]: expected[QA], expected[B]: expected[QB], expected[C]: expected[QC]}
    for supplier_id, revision in saved.quote_revision_snapshot.items():
        assert isinstance(revision, dict)
        assert revision["quote_id"] == owners[supplier_id]
    assert set(saved.quote_revision_snapshot) == set(owners)
    bound = original.model_copy(update={"snapshot_id": saved.id,
                                        "comparison_payload": deepcopy(saved.comparison_payload),
                                        "quote_revision_snapshot": saved.quote_revision_snapshot})
    initial = selection_context(bound)
    old = cast(dict[str, Any], original.comparison_payload)
    assert comparison_identities(old, initial, str(original.snapshot_id)) == expected
    first, second = initial["comparison_payload"]["suppliers"][:2]
    first["quote_id"], second["quote_id"] = second["quote_id"], first["quote_id"]
    with pytest.raises(AssertionError, match="Projected quote owner mismatch"):
        comparison_identities(old, initial, str(original.snapshot_id))


@pytest.mark.parametrize("case_id,choice,reason,highlight,action", [
    ("clear-suggestion", A, f"Q:{QA}:unit_price", f"R:{A}:{CERT}", None),
    ("tie", None, None, f"R:{B}:{CERT}", None),
    ("critical-unknown", None, None, f"R:{A}:{CERT}", "CONFIRM_MISSING"),
    ("required-failure", B, f"Q:{QB}:unit_price", f"R:{B}:{CERT}", None),
    ("incomplete-evidence", None, None, f"R:{C}:{CERT}", "CONFIRM_MISSING"),
    ("user-correction", A, f"Q:{QA}:unit_price", f"Q:{QA}:unit_price", None),
    ("incomparable-prices", None, None, f"Q:{QB}:unit_price", None),
    ("general-vs-project", A, f"Q:{QA}:unit_price", f"Q:{QA}:production_lead_time", None),
    ("mixed-currencies", None, None, f"Q:{QB}:currency", None),
    ("unequal-quantities", None, None, f"Q:{QB}:quoted_quantity", None),
    ("required-conflict", None, None, f"R:{B}:{CERT}", "RESOLVE_CONFLICT"),
])
def test_scenario_choices_and_support_are_fixed(
    case_id: str, choice: str | None, reason: str | None, highlight: str, action: str | None,
) -> None:
    snapshot, initial, ids = prepared(case_id)
    draft = scenario_selection(case_id, initial, ids)
    assert draft["suggestion"]["supplier_id"] == choice
    assert draft["suggestion"]["reason_fact_ids"] == ([reason] if reason else [])
    assert highlight in draft["highlights"]
    if action:
        assert {"action": action, "fact_id": highlight} in draft["verification_actions"]
    advice = ComparisonAdvice.model_validate(AdviceSelectionTask(snapshot).accept(json.dumps(draft)))
    assert (str(advice.suggestion.supplier_id) if advice.suggestion.supplier_id else None) == choice
    if reason:
        assert "4.50" in advice.suggestion.supporting_reasons[0].text if choice == A else (
            "3.90" in advice.suggestion.supporting_reasons[0].text)
    if case_id == "tie":
        for supplier in snapshot.comparison_payload["suppliers"]:
            assert {f["field_key"]: f["current_value"] for f in supplier["quote_fields"]} == {
                "unit_price": "4.50", "production_lead_time": 25, "quoted_quantity": 2000, "moq": 500}
    if case_id == "user-correction":
        assert "user-corrected" in advice.suggestion.supporting_reasons[0].text
    if case_id == "general-vs-project":
        first = snapshot.comparison_payload["suppliers"][0]
        assert first["supplier_facts"]["general_lead_time_days"] == 50
        assert next(f["current_value"] for f in first["quote_fields"]
                    if f["field_key"] == "production_lead_time") == 25
    if case_id == "incomparable-prices":
        assert snapshot.comparison_payload["price_comparable"] is False
        assert draft["tradeoffs"] == []
    if case_id == "mixed-currencies":
        assert [next(f["current_value"] for f in s["quote_fields"] if f["field_key"] == "currency")
                for s in snapshot.comparison_payload["suppliers"]] == ["USD", "AUD", "USD"]
    if case_id == "unequal-quantities":
        assert initial["comparison_payload"]["suppliers"][1]["quote_fields"][2]["current_value"] == 5000


@pytest.mark.parametrize("damage", ["legacy", "foreign", "owner", "snapshot"])
def test_selection_boundary_remains_strict(damage: str) -> None:
    snapshot, initial, ids = prepared()
    draft = scenario_selection("clear-suggestion", initial, ids)
    if damage == "legacy":
        draft = scenario("clear-suggestion")["output"]
    elif damage == "foreign":
        draft["highlights"] = ["foreign"]
    elif damage == "owner":
        draft["suggestion"]["reason_fact_ids"] = [f"R:{B}:{LEAD}"]
    else:
        draft["snapshot_id"] = str(uuid4())
    with pytest.raises((ComparisonRejection, ValidationError)):
        AdviceSelectionTask(snapshot).accept(json.dumps(draft))


def test_legacy_conversion_is_explicit_and_does_not_mutate_source() -> None:
    old = cast(dict[str, Any], scenario_snapshot(scenario("user-correction")).comparison_payload)
    supplier = old["suppliers"][0]
    field = supplier["quote_fields"][0]
    before = deepcopy(field)
    converted = canonical_quote_field(supplier, field)
    assert converted["origin"] == "USER_CORRECTED"
    assert converted["current_value"] == "4.50"
    assert converted["ai_extracted_value"] == "4.22"
    assert field == before
    field["ai_extracted_value"] = None
    assert canonical_quote_field(supplier, field)["ai_extracted_value"] is None
    field["ai_extracted_value"] = "4.20"
    result = canonical_quote_field(supplier, field)
    assert result["ai_extracted_value"] == "4.20"
    assert result["evidence"][0]["evidence_value"] == "4.22"


@pytest.mark.parametrize("origin,extraction,expected", [
    ("AI_EXTRACTED", {}, "4.50"),
    ("AI_EXTRACTED", {"extracted_value": None}, None),
    ("AI_EXTRACTED", {"ai_extracted_value": "4.50"}, "4.50"),
    ("USER_ENTERED", {}, None),
    ("USER_CORRECTED", {}, None),
])
def test_explicit_origins_and_absent_versus_null(
    origin: str, extraction: dict[str, Any], expected: Any,
) -> None:
    field = {"field_key": "unit_price", "current_value": "4.50", "origin": origin,
             "evidence": [], **extraction}
    assert canonical_quote_field({}, field)["ai_extracted_value"] == expected


@pytest.mark.parametrize("changes", [
    {"origin": "USER_ENTERED"}, {"origin": None},
    {"ai_extracted_value": None, "extracted_value": "4.22"},
    {"current_value": "9.99"},
    {"evidence": [{"id": PDF_PRICE, "evidence_value": "8.00"}]},
])
def test_conflicting_aliases_and_ambiguous_inference_rejected(changes: dict[str, Any]) -> None:
    supplier = cast(dict[str, Any], scenario_snapshot(scenario("user-correction")).comparison_payload)["suppliers"][0]
    field = {**supplier["quote_fields"][0], **changes}
    with pytest.raises(ValueError):
        canonical_quote_field(supplier, field)


def test_one_evidence_item_does_not_establish_extraction() -> None:
    field = {"field_key": "unit_price", "current_value": "4.50",
             "evidence": [{"id": PDF_PRICE, "evidence_value": "4.22"}]}
    with pytest.raises(ValueError, match="origin"):
        canonical_quote_field({}, field)
    field["origin"] = "USER_ENTERED"
    with pytest.raises(ValueError, match="Manual"):
        canonical_quote_field({}, field)
    field["origin"] = "USER_CORRECTED"
    with pytest.raises(ValueError, match="Ambiguous"):
        canonical_quote_field({"supplier_id": B, "quote_id": QB}, field)


@pytest.mark.parametrize("wording", ["DOES_NOT_MEET", "does not meet"])
def test_required_failure_spelling_is_accepted(wording: str) -> None:
    snapshot, initial, ids = prepared("required-failure")
    advice = ComparisonAdvice.model_validate(AdviceSelectionTask(snapshot).accept(
        json.dumps(scenario_selection("required-failure", initial, ids))))
    advice.suggestion.tradeoffs[0].text = f"Supplier B {wording} the required certification."
    assert score_case(scenario("required-failure"), advice, snapshot)


@pytest.mark.parametrize("damage", ["omitted", "supplier", "requirement", "section", "state", "substring"])
def test_required_failure_negative_controls(damage: str) -> None:
    snapshot, initial, ids = prepared("required-failure")
    advice = ComparisonAdvice.model_validate(AdviceSelectionTask(snapshot).accept(
        json.dumps(scenario_selection("required-failure", initial, ids))))
    point = advice.suggestion.tradeoffs[0]
    if damage == "omitted":
        advice.suggestion.tradeoffs.clear()
    elif damage == "supplier":
        point.supplier_ids = [UUID(A)]
    elif damage == "requirement":
        point.requirement_ids = [UUID(LEAD)]
    elif damage == "section":
        advice.suggestion.uncertainties.append(advice.suggestion.tradeoffs.pop(0))
    elif damage == "state":
        point.text = "Supplier B MEETS the required certification."
    else:
        point.text = "Supplier B xDOES_NOT_MEETx the required certification."
    assert not score_case(scenario("required-failure"), advice, snapshot)


@pytest.mark.parametrize("extraction", ["legacy", None, "4.20", "AI_EXTRACTED", "multiple"])
def test_persisted_provenance_and_real_evidence_tool_agree(
    adapter_session: Session, extraction: str | None,
) -> None:
    session = adapter_session
    case = scenario("user-correction")
    expected_extraction = "4.22"
    expected_origin = "USER_CORRECTED"
    if extraction != "legacy":
        payload = deepcopy(scenario_snapshot(case).comparison_payload)
        assert payload is not None
        suppliers = payload["suppliers"]
        assert isinstance(suppliers, list)
        case["payload"] = payload
        source_field = suppliers[0]["quote_fields"][0]
        if extraction == "AI_EXTRACTED":
            expected_origin = "AI_EXTRACTED"
            expected_extraction = "4.50"
            source_field["current_origin"] = expected_origin
        elif extraction == "multiple":
            source_field["evidence"].append({"id": str(uuid4()), "evidence_value": "4.23"})
        else:
            expected_extraction = extraction
        source_field["ai_extracted_value"] = expected_extraction
    original = deepcopy(case)
    owner, project = fresh_project(session, case)
    _, ids = comparison_fixture(session, project, case)
    saved = session.get(Comparison, UUID(ids[case["snapshot_id"]]))
    assert saved is not None
    suppliers = saved.comparison_payload["suppliers"]
    assert isinstance(suppliers, list)
    supplier = suppliers[0]
    field = supplier["quote_fields"][0]
    value = session.scalar(select(QuoteValue).where(
        QuoteValue.quote_id == UUID(ids[QA]), QuoteValue.field_key == "unit_price"))
    assert value is not None
    assert field["current_value"] == value.current_value == "4.50"
    assert field["origin"] == value.current_origin == expected_origin
    assert field["ai_extracted_value"] == value.ai_extracted_value == expected_extraction
    runtime = AnalystToolRuntime(AnalystToolContext(
        demo_session_id=owner.id, project_id=project.id,
        permitted_supplier_ids=frozenset({UUID(ids[A]), UUID(ids[B])}),
        permitted_quote_ids=frozenset({UUID(ids[QA]), UUID(ids[QB])})))
    evidence = get_quote_evidence(session, runtime, UUID(ids[QA]), "unit_price")
    assert evidence.current_value == "4.50" and evidence.ai_extracted_value == expected_extraction
    assert evidence.evidence[0].role == (
        "supporting" if expected_origin == "AI_EXTRACTED" else "provenance")
    assert evidence.evidence[0].evidence_value == "4.22"
    assert evidence.evidence[0].untrusted_source_text == "Synthetic original unit_price: 4.22"
    if extraction == "multiple":
        assert [e.evidence_value for e in evidence.evidence] == ["4.22", "4.23"]
        assert len({e.document_block_id for e in evidence.evidence}) == 2
    manual = get_quote_evidence(session, runtime, UUID(ids[QB]), "unit_price")
    assert manual.current_origin == "USER_ENTERED"
    assert manual.ai_extracted_value is None and manual.evidence == []
    assert case == original
