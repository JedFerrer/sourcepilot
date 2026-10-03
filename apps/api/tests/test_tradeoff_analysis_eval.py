"""The offline M4-U6 golden set catches unsupported claims and source attribution."""

from copy import deepcopy
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest

from sourcepilot.ai import tradeoff_analysis_eval_live as live
from sourcepilot.ai.tradeoff_analysis import AnalysisPoint, QuoteFieldReference, validate_analysis
from sourcepilot.ai.tradeoff_analysis_eval import (
    CERT,
    LEAD,
    PDF_PRICE,
    QA,
    QB,
    QC,
    A,
    B,
    C,
    fixture_snapshot,
    load_cases,
    recorded_analysis,
    score_case,
)


@pytest.mark.parametrize("section,wording,valid", [
    (section, wording, valid)
    for wording, valid in [
    ("is unknown", True),
    ("remains undetermined", True),
    ("is no longer unknown", False),
    ("is no longer undetermined", False),
    ("is not currently unknown", False),
    ("has conflicting evidence", True),
    ("has a conflict", True),
    ("does not have conflicting evidence", False),
    ("doesn't have conflicting evidence", False),
    ("has no conflict", False),
    ]
    for section in ("supplier_summaries", "key_tradeoffs",
                    "important_conflicts" if "conflict" in wording else "important_unknowns")
])
def test_quote_only_uncertainty_uses_shared_state_semantics(
    section: str, wording: str, valid: bool,
) -> None:
    state = "conflicting" if "conflict" in wording else "missing"
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    snapshot = fixture_snapshot()
    assert snapshot.comparison_payload is not None
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    payload["suppliers"][2]["completeness"][-1]["state"] = state
    # Remove the baseline shipping claim when testing a conflicting shipping field.
    analysis.supplier_summaries = analysis.supplier_summaries[:2]
    getattr(analysis, section).append(AnalysisPoint(
        text=f"Supplier C's shipping cost {wording}.", supplier_ids=[UUID(C)],
        requirement_ids=[], quote_fields=[QuoteFieldReference(
            quote_id=UUID(QC), field_key="shipping_cost")], evidence_ids=[],
    ))
    if valid:
        validate_analysis(analysis, snapshot)
    else:
        with pytest.raises(ValueError, match="Quote-field state assertion contradicts"):
            validate_analysis(analysis, snapshot)
    assert score_case(case, analysis, snapshot) is valid


@pytest.mark.parametrize("field,label", [
    ("shipping_cost", "shipping cost"), ("shipping_time", "shipping time"),
    ("sample_lead_time", "sample lead time"),
    ("production_lead_time", "production lead time"), ("total_lead_time", "total lead time"),
])
@pytest.mark.parametrize("state", ["missing", "conflicting", "known"])
@pytest.mark.parametrize("wording,allowed", [
    ("is unknown", {"missing"}),
    ("has conflicting evidence", {"conflicting"}),
    ("is no longer unknown", {"conflicting", "known"}),
    ("has no conflict", {"missing", "known"}),
])
def test_quote_only_claims_use_field_state_even_for_requirement_kind_labels(
    field: str, label: str, state: str, wording: str, allowed: set[str],
) -> None:
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    analysis.supplier_summaries = analysis.supplier_summaries[:2]
    snapshot = fixture_snapshot()
    assert snapshot.comparison_payload is not None
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    completeness = payload["suppliers"][2]["completeness"]
    completeness[:] = [item for item in completeness if item["field_key"] != field]
    completeness.append({"field_key": field, "state": state})
    analysis.supplier_summaries.append(AnalysisPoint(
        text=f"Supplier C's {label} {wording}.", supplier_ids=[UUID(C)],
        requirement_ids=[], quote_fields=[QuoteFieldReference(
            quote_id=UUID(QC), field_key=field)], evidence_ids=[],
    ))
    if state in allowed:
        validate_analysis(analysis, snapshot)
    else:
        with pytest.raises(ValueError, match="Quote-field state assertion contradicts"):
            validate_analysis(analysis, snapshot)
    assert score_case(case, analysis, snapshot) is (state in allowed)


@pytest.mark.parametrize("fields", [
    ("shipping_cost", "shipping_time"),
    ("sample_lead_time", "total_lead_time"),
])
@pytest.mark.parametrize("second_state", ["missing", "known"])
def test_separate_quote_field_claims_keep_both_references(
    fields: tuple[str, str], second_state: str,
) -> None:
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    snapshot = fixture_snapshot()
    assert snapshot.comparison_payload is not None
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    completeness = payload["suppliers"][2]["completeness"]
    completeness[:] = [item for item in completeness if item["field_key"] not in fields]
    completeness.extend([{"field_key": fields[0], "state": "missing"},
                         {"field_key": fields[1], "state": second_state}])
    analysis.key_tradeoffs.append(AnalysisPoint(
        text=f"Supplier C's {fields[0].replace('_', ' ')} is unknown and "
             f"its {fields[1].replace('_', ' ')} is unknown.",
        supplier_ids=[UUID(C)], requirement_ids=[],
        quote_fields=[QuoteFieldReference(quote_id=UUID(QC), field_key=field)
                      for field in fields], evidence_ids=[],
    ))
    if second_state == "missing":
        validate_analysis(analysis, snapshot)
    else:
        with pytest.raises(ValueError, match="Quote-field state assertion contradicts"):
            validate_analysis(analysis, snapshot)
    assert score_case(case, analysis, snapshot) is (second_state == "missing")


@pytest.mark.parametrize("fields,predicate,expected", [
    (("shipping_cost", "shipping_time"), "are unknown", "missing"),
    (("sample_lead_time", "total_lead_time"), "have conflicting evidence", "conflicting"),
])
@pytest.mark.parametrize("first_state", ["missing", "known", "conflicting"])
@pytest.mark.parametrize("second_state", ["missing", "known", "conflicting"])
def test_shared_quote_field_predicate_checks_every_explicit_field(
    fields: tuple[str, str], predicate: str, expected: str,
    first_state: str, second_state: str,
) -> None:
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    analysis.supplier_summaries = analysis.supplier_summaries[:2]
    snapshot = fixture_snapshot()
    assert snapshot.comparison_payload is not None
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    completeness = payload["suppliers"][2]["completeness"]
    completeness[:] = [item for item in completeness if item["field_key"] not in fields]
    completeness.extend([{"field_key": fields[0], "state": first_state},
                         {"field_key": fields[1], "state": second_state}])
    analysis.key_tradeoffs.append(AnalysisPoint(
        text=f"Supplier C’s {fields[0].replace('_', ' ')} and "
             f"{fields[1].replace('_', ' ')} {predicate}.",
        supplier_ids=[UUID(C)], requirement_ids=[],
        quote_fields=[QuoteFieldReference(quote_id=UUID(QC), field_key=field)
                      for field in fields], evidence_ids=[],
    ))
    valid = first_state == second_state == expected
    if valid:
        validate_analysis(analysis, snapshot)
    else:
        with pytest.raises(ValueError, match="Quote-field state assertion contradicts"):
            validate_analysis(analysis, snapshot)
    assert score_case(case, analysis, snapshot) is valid


@pytest.mark.parametrize("first_state", ["missing", "known", "conflicting"])
@pytest.mark.parametrize("second_state", ["missing", "known", "conflicting"])
def test_separate_known_and_unknown_quote_predicates_remain_independent(
    first_state: str, second_state: str,
) -> None:
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    analysis.supplier_summaries = analysis.supplier_summaries[:2]
    snapshot = fixture_snapshot()
    assert snapshot.comparison_payload is not None
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    completeness = payload["suppliers"][2]["completeness"]
    completeness[:] = [item for item in completeness
                       if item["field_key"] not in {"shipping_cost", "shipping_time"}]
    completeness.extend([{"field_key": "shipping_cost", "state": first_state},
                         {"field_key": "shipping_time", "state": second_state}])
    analysis.key_tradeoffs.append(AnalysisPoint(
        text="Supplier C's shipping cost is known and shipping time is unknown.",
        supplier_ids=[UUID(C)], requirement_ids=[],
        quote_fields=[QuoteFieldReference(quote_id=UUID(QC), field_key=field)
                      for field in ("shipping_cost", "shipping_time")], evidence_ids=[],
    ))
    valid = first_state == "known" and second_state == "missing"
    if valid:
        validate_analysis(analysis, snapshot)
    else:
        with pytest.raises(ValueError, match="Quote-field state assertion contradicts"):
            validate_analysis(analysis, snapshot)
    assert score_case(case, analysis, snapshot) is valid


@pytest.mark.parametrize("text,cited_fields", [
    ("Supplier C's shipping cost and shipping time are unknown.", ["shipping_time"]),
    ("Supplier C's fields are unknown.", ["shipping_cost", "shipping_time"]),
    ("Supplier C's shipping cost versus shipping time is unknown.",
     ["shipping_cost", "shipping_time"]),
])
def test_shared_quote_predicate_still_rejects_missing_or_ambiguous_references(
    text: str, cited_fields: list[str],
) -> None:
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    snapshot = fixture_snapshot()
    assert snapshot.comparison_payload is not None
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    payload["suppliers"][2]["completeness"].append(
        {"field_key": "shipping_time", "state": "missing"})
    analysis.key_tradeoffs.append(AnalysisPoint(
        text=text, supplier_ids=[UUID(C)], requirement_ids=[],
        quote_fields=[QuoteFieldReference(quote_id=UUID(QC), field_key=field)
                      for field in cited_fields], evidence_ids=[],
    ))
    with pytest.raises(ValueError, match="Quote-field state assertion"):
        validate_analysis(analysis, snapshot)
    assert not score_case(case, analysis, snapshot)


@pytest.mark.parametrize("field,other", [
    ("shipping_time", "shipping_cost"), ("shipping_cost", "shipping_time"),
    ("sample_lead_time", "production_lead_time"),
    ("production_lead_time", "total_lead_time"),
    ("total_lead_time", "production_lead_time"),
])
def test_explicit_quote_field_cannot_bind_to_another_cited_field(field: str, other: str) -> None:
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    snapshot = fixture_snapshot()
    assert snapshot.comparison_payload is not None
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    payload["suppliers"][2]["completeness"].append({"field_key": other, "state": "missing"})
    analysis.key_tradeoffs.append(AnalysisPoint(
        text=f"Supplier C's {field.replace('_', ' ')} is unknown.",
        supplier_ids=[UUID(C)], requirement_ids=[],
        quote_fields=[QuoteFieldReference(quote_id=UUID(QC), field_key=other)], evidence_ids=[],
    ))
    with pytest.raises(ValueError, match="Quote-field state assertion lacks an unambiguous field"):
        validate_analysis(analysis, snapshot)
    assert score_case(case, analysis, snapshot) is False


@pytest.mark.parametrize("text,fields,valid", [
    ("Supplier C's shipping cost is unknown.", [(QC, "shipping_cost")], True),
    ("Shipping cost is unknown.", [(QC, "shipping_cost")], False),
    ("Supplier C's field is unknown.", [(QC, "shipping_cost")], True),
    ("Supplier C's field is unknown.", [(QC, "shipping_cost"), (QC, "unit_price")], False),
    ("Supplier C's unit price is unknown.", [(QC, "shipping_cost")], False),
    ("Supplier C's unit price is unknown.", [(QC, "unit_price")], False),
    ("Supplier C's shipping cost is unknown.", [(QA, "shipping_cost")], False),
    ("Supplier A's shipping cost is unknown.", [(QA, "shipping_cost"), (QC, "shipping_cost")],
     False),
    ("Supplier C's shipping cost is unknown; Supplier A's shipping cost has conflicting evidence.",
     [(QA, "shipping_cost"), (QC, "shipping_cost")], True),
    ("Supplier C's shipping cost is no longer unknown; Supplier A's shipping cost conflicts.",
     [(QA, "shipping_cost"), (QC, "shipping_cost")], False),
    ("Supplier A and Supplier C's shipping cost is unknown.",
     [(QA, "shipping_cost"), (QC, "shipping_cost")], False),
    ("Supplier C's shipping cost is unknown; its unit price is not unknown.",
     [(QC, "shipping_cost"), (QC, "unit_price")], True),
    ("Supplier C's shipping cost is unknown; its unit price is unknown.",
     [(QC, "shipping_cost"), (QC, "unit_price")], False),
    ("Supplier B's shipping cost is unknown.", [(QB, "shipping_cost")], False),
])
def test_quote_only_assertions_bind_supplier_field_and_structured_state(
    text: str, fields: list[tuple[str, str]], valid: bool,
) -> None:
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    snapshot = fixture_snapshot()
    assert snapshot.comparison_payload is not None
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    payload["suppliers"][0]["completeness"].append({
        "field_key": "shipping_cost", "state": "conflicting"})
    # A field reference without a structured completeness state fails closed.
    payload["suppliers"][1]["quote_fields"].append({
        "field_key": "shipping_cost", "current_value": None, "evidence": []})
    analysis.key_tradeoffs.append(AnalysisPoint(
        text=text, supplier_ids=[UUID(A), UUID(B), UUID(C)], requirement_ids=[],
        quote_fields=[QuoteFieldReference(quote_id=UUID(quote), field_key=field)
                      for quote, field in fields], evidence_ids=[],
    ))
    if valid:
        validate_analysis(analysis, snapshot)
    else:
        with pytest.raises(ValueError, match="assertion"):
            validate_analysis(analysis, snapshot)
    assert score_case(case, analysis, snapshot) is valid


@pytest.mark.parametrize("supplier_id,requirement_id,actual,name,label", [
    (A, CERT, "MEETS", "A", "certification"),
    (B, CERT, "DOES_NOT_MEET", "B", "certification"),
    (C, CERT, "UNKNOWN", "C", "certification"),
    (A, LEAD, "CONFLICT", "A", "lead-time evidence"),
])
@pytest.mark.parametrize("claimed,wording", [
    ("MEETS", "meets the requirement"),
    ("DOES_NOT_MEET", "does not meet the requirement"),
    ("UNKNOWN", "is unknown"),
    ("CONFLICT", "has conflicting evidence"),
])
def test_requirement_state_claims_match_all_four_states(
    supplier_id: str, requirement_id: str, actual: str, name: str, label: str,
    claimed: str, wording: str,
) -> None:
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    analysis.supplier_summaries.append(AnalysisPoint(
        text=f"Supplier {name}'s {label} {wording}.",
        supplier_ids=[UUID(supplier_id)], requirement_ids=[UUID(requirement_id)],
        quote_fields=[], evidence_ids=[],
    ))
    snapshot = fixture_snapshot()
    if actual == claimed:
        validate_analysis(analysis, snapshot)
        assert score_case(case, analysis, snapshot)
    else:
        with pytest.raises(ValueError, match="assertion contradicts"):
            validate_analysis(analysis, snapshot)
        assert not score_case(case, analysis, snapshot)


@pytest.mark.parametrize("section,text", [
    ("important_unknowns", "Supplier C's certification meets the requirement."),
    ("important_conflicts", "Supplier A's lead-time evidence has no conflict."),
    ("important_conflicts", "Supplier A's lead-time evidence does not conflict."),
    ("important_conflicts", "Supplier A's lead-time evidence is not conflicting."),
    ("important_conflicts", "Supplier A's lead-time evidence has no conflicting evidence."),
    ("important_conflicts", "Supplier A's lead-time evidence is not a conflict."),
    ("important_conflicts", "Supplier A's lead-time evidence does not have a conflict."),
    ("important_unknowns", "Supplier C's certification is not unknown."),
])
def test_done_check_probes_and_negated_states(section: str, text: str) -> None:
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    getattr(analysis, section)[0].text = text
    with pytest.raises(ValueError, match="assertion contradicts"):
        validate_analysis(analysis, fixture_snapshot())
    assert not score_case(case, analysis, fixture_snapshot())


@pytest.mark.parametrize("text", [
    "Supplier B and Supplier A meet the certification.",
    "Supplier A and Supplier B meet the certification.",
    "Supplier B, Supplier A and Supplier C meet the certification.",
])
@pytest.mark.parametrize("both_meet", [False, True])
def test_coordinated_subject_checks_every_supplier(text: str, both_meet: bool) -> None:
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    snapshot = fixture_snapshot()
    assert snapshot.comparison_payload is not None
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    if both_meet:
        for supplier in payload["suppliers"]:
            supplier["evaluation"]["results"][0]["status"] = "MEETS"
        analysis.supplier_summaries[1].text = "Supplier B meets the certification."
        analysis.important_unknowns = [
            point for point in analysis.important_unknowns if not point.requirement_ids
        ]
    analysis.key_tradeoffs.append(AnalysisPoint(
        text=text, supplier_ids=[UUID(A), UUID(B), UUID(C)],
        requirement_ids=[UUID(CERT)], quote_fields=[], evidence_ids=[],
    ))
    if both_meet:
        validate_analysis(analysis, snapshot)
    else:
        with pytest.raises(ValueError, match="assertion contradicts"):
            validate_analysis(analysis, snapshot)
    assert score_case(case, analysis, snapshot) is both_meet


@pytest.mark.parametrize("section,wording,valid", [
    ("important_unknowns", "is unknown", True),
    ("important_unknowns", "remains unknown", True),
    ("important_unknowns", "is no longer unknown", False),
    ("important_unknowns", "is no longer undetermined", False),
    ("important_unknowns", "is not currently unknown", False),
    ("important_conflicts", "has conflicting evidence", True),
    ("important_conflicts", "has a conflict", True),
    ("important_conflicts", "does not have conflicting evidence", False),
    ("important_conflicts", "doesn't have conflicting evidence", False),
    ("important_conflicts", "has no conflict", False),
])
def test_bounded_positive_and_negated_uncertainty(
    section: str, wording: str, valid: bool,
) -> None:
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    label = "Supplier C's certification" if section == "important_unknowns" else (
        "Supplier A's lead-time evidence")
    getattr(analysis, section)[0].text = f"{label} {wording}."
    snapshot = fixture_snapshot()
    if valid:
        validate_analysis(analysis, snapshot)
    else:
        with pytest.raises(ValueError, match="assertion contradicts"):
            validate_analysis(analysis, snapshot)
    assert score_case(case, analysis, snapshot) is valid


@pytest.mark.parametrize("text", [
    "Supplier B fails to provide a lower lead time than Supplier A.",
    "Supplier A fails to provide a lower unit price than Supplier B.",
    ("Supplier B is cheaper at USD 3.90 versus Supplier A at USD 4.50, "
     "but fails to provide a lower lead time than Supplier A."),
])
def test_supported_comparative_prose_is_not_a_requirement_failure(text: str) -> None:
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    point = deepcopy(analysis.key_tradeoffs[0])
    point.text = text
    point.requirement_ids = []
    analysis.key_tradeoffs.append(point)
    validate_analysis(analysis, fixture_snapshot())
    assert score_case(case, analysis, fixture_snapshot())


@pytest.mark.parametrize("wording", [
    "fails the requirement", "fails the certification", "fails to meet the requirement",
    "fails to satisfy the requirement", "does not meet the requirement",
])
@pytest.mark.parametrize("supplier_id,valid", [(B, True), (A, False)])
def test_genuine_requirement_failure_is_still_validated(
    wording: str, supplier_id: str, valid: bool,
) -> None:
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    name = "B" if supplier_id == B else "A"
    analysis.supplier_summaries.append(AnalysisPoint(
        text=f"Supplier {name}'s certification {wording}.",
        supplier_ids=[UUID(supplier_id)], requirement_ids=[UUID(CERT)],
        quote_fields=[], evidence_ids=[],
    ))
    snapshot = fixture_snapshot()
    if valid:
        validate_analysis(analysis, snapshot)
    else:
        with pytest.raises(ValueError, match="assertion contradicts"):
            validate_analysis(analysis, snapshot)
    assert score_case(case, analysis, snapshot) is valid


def test_repeated_requirement_kind_needs_the_explicit_schema_value() -> None:
    snapshot = fixture_snapshot()
    assert snapshot.comparison_payload is not None
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    second_cert = UUID("33333333-3333-3333-3333-333333333339")
    payload["brief"]["requirements"][0]["expected_value"] = {"value": "GOTS"}
    payload["brief"]["requirements"].append({
        "id": str(second_cert), "kind": "CERTIFICATION", "importance": "PREFERRED",
        "expected_value": {"value": "OEKO-TEX"},
    })
    for supplier in payload["suppliers"]:
        supplier["evaluation"]["results"].append({
            "requirement_id": str(second_cert), "status": "MEETS",
        })
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    # Qualify the existing claims now that the snapshot contains two certifications.
    analysis.supplier_summaries[1].text = "Supplier B does not meet the GOTS certification."
    analysis.important_unknowns[0].text = "Supplier C's GOTS certification is unknown."
    point = AnalysisPoint(
        text="Supplier C's OEKO-TEX certification meets.", supplier_ids=[UUID(C)],
        requirement_ids=[second_cert], quote_fields=[], evidence_ids=[],
    )
    analysis.supplier_summaries.append(point)
    validate_analysis(analysis, snapshot)
    assert score_case(case, analysis, snapshot)
    point.text = "Supplier C's GOTS certification meets."
    with pytest.raises(ValueError, match="assertion lacks"):
        validate_analysis(analysis, snapshot)
    assert not score_case(case, analysis, snapshot)


@pytest.mark.parametrize("unknown,conflict", [
    ("is unknown", "conflicts"),
    ("is undetermined", "has conflicting evidence"),
    ("has insufficient evidence", "is in conflict"),
    ("has not enough information", "has a conflict"),
])
def test_valid_unknown_and_conflict_wording(unknown: str, conflict: str) -> None:
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    analysis.important_unknowns[0].text = f"Supplier C's certification {unknown}."
    analysis.important_conflicts[0].text = f"Supplier A's lead-time evidence {conflict}."
    validate_analysis(analysis, fixture_snapshot())
    assert score_case(case, analysis, fixture_snapshot())


@pytest.mark.parametrize("text,valid", [
    ("Supplier A meets the certification and Supplier B does not meet the certification.", True),
    ("Supplier A does not meet the certification and Supplier B meets the certification.", False),
    ("Supplier A's certification meets; its lead-time evidence conflicts.", True),
    ("Supplier A's certification conflicts; its lead-time evidence meets.", False),
    ("Supplier A meets the certification. Supplier B meets the certification.", False),
    ("Supplier A meets the certification. Supplier B does not currently meet the certification.", True),
])
def test_each_state_assertion_binds_its_supplier_and_requirement(text: str, valid: bool) -> None:
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    analysis.key_tradeoffs.append(AnalysisPoint(
        text=text, supplier_ids=[UUID(A), UUID(B)],
        requirement_ids=[UUID(CERT), UUID(LEAD)], quote_fields=[], evidence_ids=[],
    ))
    if valid:
        validate_analysis(analysis, fixture_snapshot())
    else:
        with pytest.raises(ValueError, match="assertion contradicts"):
            validate_analysis(analysis, fixture_snapshot())
    assert score_case(case, analysis, fixture_snapshot()) is valid


@pytest.mark.parametrize("supplier_ids,requirement_ids,text", [
    ([C], [CERT], "Supplier A's certification meets."),
    ([A], [LEAD], "Supplier A's certification conflicts."),
    ([A], [], "Supplier A meets the certification."),
    ([A], [], "Supplier A meets the requirement."),
    ([A, B], [CERT], "The certification meets."),
    ([A], [CERT, LEAD], "The requirement meets."),
])
def test_unbound_or_ambiguous_requirement_assertions_fail_closed(
    supplier_ids: list[str], requirement_ids: list[str], text: str,
) -> None:
    case = load_cases()[0]
    analysis = deepcopy(recorded_analysis(case))
    analysis.key_tradeoffs.append(AnalysisPoint(
        text=text, supplier_ids=[UUID(value) for value in supplier_ids],
        requirement_ids=[UUID(value) for value in requirement_ids], quote_fields=[], evidence_ids=[],
    ))
    with pytest.raises(ValueError, match="assertion"):
        validate_analysis(analysis, fixture_snapshot())
    assert not score_case(case, analysis, fixture_snapshot())


def test_tradeoff_groundedness_cases() -> None:
    cases = load_cases()
    assert len(cases) == 8
    assert len({case["id"] for case in cases}) == len(cases)
    assert {case["topic"] for case in cases} == {
        "meaningful tradeoff", "required failure", "Unknown and Conflict",
        "user correction", "incomplete evidence", "omitted critical fact", "unsupported claim",
        "unsupported source attribution",
    }
    for case in cases:
        assert score_case(case, recorded_analysis(case), fixture_snapshot()) is case["expected_grounded"], case["id"]


def test_scorer_checks_the_produced_analysis_not_case_text() -> None:
    case = load_cases()[0]
    original = recorded_analysis(case)
    assert score_case(case, original, fixture_snapshot())
    changed = deepcopy(original)
    changed.key_tradeoffs[0].text = "Supplier B is cheaper at USD 300 and has a longer lead time."
    assert not score_case(case, changed, fixture_snapshot())

    correction = next(item for item in load_cases() if item["id"] == "corrected-quote-provenance")
    changed = deepcopy(recorded_analysis(correction))
    changed.supplier_summaries[0].evidence_ids = []
    assert not score_case(correction, changed, fixture_snapshot())


def test_groundedness_binds_supplier_field_and_provenance() -> None:
    case = load_cases()[0]
    original = recorded_analysis(case)
    assert score_case(case, original, fixture_snapshot())
    for old, new in (
        ("Supplier B is cheaper at USD 3.90 versus Supplier A at USD 4.50",
         "Supplier B is cheaper at USD 4.50 versus Supplier A at USD 3.90"),
        ("38 days versus 25 days", "25 days versus 38 days"),
        ("Supplier B is cheaper", "Supplier A is cheaper"),
    ):
        changed = deepcopy(original)
        changed.key_tradeoffs[0].text = changed.key_tradeoffs[0].text.replace(old, new)
        assert not score_case(case, changed, fixture_snapshot()), (old, new)

    for old, new in (
        ("confirmed unit price is USD 4.50; its PDF had USD 4.22",
         "confirmed unit price is USD 4.22; its PDF had USD 4.50"),
        ("confirmed unit price is USD 4.50", "confirmed shipping cost is USD 4.50"),
    ):
        changed = deepcopy(original)
        changed.supplier_summaries[0].text = changed.supplier_summaries[0].text.replace(old, new)
        assert not score_case(case, changed, fixture_snapshot()), (old, new)


def test_each_provenance_assertion_is_checked_independently() -> None:
    case = load_cases()[0]
    original = recorded_analysis(case)
    assert score_case(case, original, fixture_snapshot())
    mixed = deepcopy(original)
    mixed.supplier_summaries[0].text = (
        "Supplier A's PDF price is 4.22 and its confirmed current price is 4.50."
    )
    assert score_case(case, mixed, fixture_snapshot())

    contradicted = deepcopy(mixed)
    contradicted.supplier_summaries[0].text = (
        "Supplier A's PDF price is 4.22 and its confirmed current price is 4.22."
    )
    # The correct current value remains in a separate tradeoff point.
    assert "4.50" in contradicted.key_tradeoffs[0].text
    assert not score_case(case, contradicted, fixture_snapshot())


def test_provenance_before_or_after_supplier_and_value() -> None:
    case = load_cases()[0]
    original = recorded_analysis(case)
    for text in (
        "PDF shows Supplier A at USD 4.22; its confirmed current price is USD 4.50.",
        "Supplier A PDF/source price is USD 4.22; its current price is USD 4.50.",
        "Supplier A price is USD 4.22 per PDF; its price is USD 4.50 confirmed.",
        "Supplier A confirmed current price is USD 4.50, and its PDF price is USD 4.22.",
    ):
        changed = deepcopy(original)
        changed.supplier_summaries[0].text = text
        assert score_case(case, changed, fixture_snapshot()), text

    for text in (
        "Supplier A confirmed current price is USD 4.22.",
        "Supplier A PDF/source price is USD 4.22; its current price is USD 4.22.",
        "Supplier A current price is USD 4.22; its PDF price is USD 4.22.",
    ):
        changed = deepcopy(original)
        changed.supplier_summaries[0].text = text
        assert not score_case(case, changed, fixture_snapshot()), text


def test_neighboring_provenance_cannot_rescue_unsupported_pdf_claim() -> None:
    case = load_cases()[0]
    changed = deepcopy(recorded_analysis(case))
    changed.key_tradeoffs[0].text += " PDF source shows Supplier B at USD 3.90."
    # A's valid PDF citation cannot support B's asserted PDF price.
    changed.key_tradeoffs[0].evidence_ids.append(UUID(PDF_PRICE))
    assert not score_case(case, changed, fixture_snapshot())


def test_quantity_assertions_bind_supplier_and_semantic_field() -> None:
    case = load_cases()[0]
    original = recorded_analysis(case)
    for supplier_index, quote_id, quantity, moq in (
        (0, "22222222-2222-2222-2222-222222222221", 2000, 500),
        (1, "22222222-2222-2222-2222-222222222222", 5000, 1000),
    ):
        valid = deepcopy(original)
        point = valid.supplier_summaries[supplier_index]
        name = "A" if supplier_index == 0 else "B"
        point.text += f" Supplier {name}'s quoted quantity is {quantity} and MOQ is {moq}."
        point.quote_fields.extend([
            QuoteFieldReference(quote_id=UUID(quote_id), field_key="quoted_quantity"),
            QuoteFieldReference(quote_id=UUID(quote_id), field_key="moq"),
        ])
        assert score_case(case, valid, fixture_snapshot())

        wrong_quantity = deepcopy(valid)
        wrong_quantity.supplier_summaries[supplier_index].text = point.text.replace(
            f"quoted quantity is {quantity}",
            f"quoted quantity is {5000 if quantity == 2000 else 2000}")
        assert not score_case(case, wrong_quantity, fixture_snapshot())

        invented = deepcopy(valid)
        invented.supplier_summaries[supplier_index].text = point.text.replace(
            f"MOQ is {moq}", "MOQ is 999999")
        assert not score_case(case, invented, fixture_snapshot())

        swapped = deepcopy(valid)
        swapped.supplier_summaries[supplier_index].text = point.text.replace(
            f"MOQ is {moq}", f"MOQ is {1000 if moq == 500 else 500}")
        assert not score_case(case, swapped, fixture_snapshot())

    requested = deepcopy(original)
    requested.key_tradeoffs[0].text += " Requested quantity is 2000."
    assert score_case(case, requested, fixture_snapshot())
    requested.key_tradeoffs[0].text = requested.key_tradeoffs[0].text.replace(
        "Requested quantity is 2000", "Requested quantity is 999999")
    assert not score_case(case, requested, fixture_snapshot())


def test_live_scenarios_have_distinct_inputs_and_expectation_logic() -> None:
    scenarios = live.live_scenarios()
    assert len(scenarios) == 3
    assert len({snapshot.snapshot_id for _, snapshot in scenarios}) == 3
    assert len({str(snapshot.comparison_payload) for _, snapshot in scenarios}) == 3
    assert {case["topic"] for case, _ in scenarios} == {
        "meaningful tradeoff", "required failure", "user correction"}
    assert not live.matches_expectation({"expected_grounded": False}, True)
    assert live.matches_expectation({"expected_grounded": False}, False)


def test_live_command_scores_each_analyst_result_against_its_scenario(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def get(self, _model, _project_id):
            return SimpleNamespace(id=UUID("66666666-6666-6666-6666-666666666661"),
                                   demo_session_id=UUID("66666666-6666-6666-6666-666666666662"))

    seen: list[str] = []

    def analyst(_session, **_kwargs):
        seen.append("called")
        return SimpleNamespace(analysis=recorded_analysis(load_cases()[0]),
                               run_id=UUID("77777777-7777-7777-7777-777777777771"))

    monkeypatch.setattr(live, "application_session_factory", lambda: FakeSession)
    monkeypatch.setattr(live.OpenAIResponsesClient, "from_environment", lambda: object())
    monkeypatch.setattr(live, "analyze_tradeoffs", analyst)
    monkeypatch.setattr("sys.argv", ["eval", "--project-id",
                                     "66666666-6666-6666-6666-666666666661"])
    live.main()
    output = capsys.readouterr().out
    assert len(seen) == 3
    assert "Scorer regression controls: 8/8" in output
    assert "Live analyst scenarios: 1/3" in output
