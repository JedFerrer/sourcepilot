"""M4-U2 deterministic evaluator contracts and warning metadata."""

from uuid import uuid4

import pytest

from sourcepilot.briefs.domain import RequirementKind
from sourcepilot.comparison.evaluation import ComparisonWarningCode, evaluate_comparison
from sourcepilot.comparison.facts import (
    confirmed_quote_currency,
    resolve_commercial_facts,
    resolve_delivery_commitment,
    resolve_quoted_quantity,
)
from sourcepilot.comparison.source_resolution import (
    FactContext,
    PriceValue,
    SourceFact,
    SourceResolution,
    SourceResolutionStatus,
    resolve_sources,
)
from sourcepilot.persistence.models import Quote, QuoteFieldEvidence, QuoteValue, Supplier
from sourcepilot.quotes.domain import QuoteStatus, QuoteValueOrigin
from sourcepilot.suppliers.evaluation import (
    EvaluationEvidence,
    EvaluationRequirement,
    EvaluationStatus,
    SupplierEvaluationFacts,
)


def _requirement(kind: RequirementKind, value: dict[str, object]) -> EvaluationRequirement:
    return EvaluationRequirement(uuid4(), kind, value)


def _fact(field: str, value: object, *, conflict: bool = False) -> SourceFact:
    return SourceFact(
        field, value, FactContext.PROJECT_QUOTE, f"quote:{field}",
        has_same_context_conflict=conflict,
    )


def _resolved(field: str, value: object | None = None, *, conflict: bool = False) -> SourceResolution:
    return resolve_sources(field, project_facts=(_fact(field, value, conflict=conflict),)
                           if value is not None or conflict else ())


def _run(
    requirements: list[EvaluationRequirement],
    *,
    quantity: SourceResolution | None = None,
    price: SourceResolution | None = None,
    lead: SourceResolution | None = None,
    moq: SourceResolution | None = None,
    delivery: SourceResolution | None = None,
    supplier: SupplierEvaluationFacts | None = None,
    quote_currency: str | None = "USD",
    currencies: tuple[str | None, ...] = ("USD", "USD"),
):
    return evaluate_comparison(
        requirements,
        requested_quantity=2000,
        supplier=supplier or SupplierEvaluationFacts(frozenset(), None, ()),
        commercial_facts={
            "moq": moq or _resolved("moq"),
            "unit_price": price or _resolved("unit_price"),
            "production_lead_time": lead or _resolved("production_lead_time"),
        },
        quoted_quantity=quantity or _resolved("quoted_quantity", 2000),
        delivery_commitment=delivery or _resolved("delivery_date"),
        quote_currency=quote_currency,
        quote_currencies=currencies,
    )


def _codes(result) -> set[ComparisonWarningCode]:
    return {warning.code for warning in result.warnings}


def test_quantity_alignment_and_warning_are_separate_from_status() -> None:
    requirement = _requirement(RequirementKind.QUANTITY, {"quantity": 2000})
    matched = _run([requirement])
    assert matched.results[0].status is EvaluationStatus.MEETS
    assert matched.warnings == ()

    mismatched = _run([requirement], quantity=_resolved("quoted_quantity", 5000))
    assert mismatched.results[0].status is EvaluationStatus.DOES_NOT_MEET
    assert _codes(mismatched) == {ComparisonWarningCode.QUANTITY_MISMATCH}
    assert mismatched.results[0].selected_fact is not None
    assert mismatched.results[0].selected_fact.value == 5000

    assert _run([requirement], quantity=_resolved("quoted_quantity")).results[0].status is EvaluationStatus.UNKNOWN
    conflict = _run([requirement], quantity=_resolved("quoted_quantity", 2000, conflict=True))
    assert conflict.results[0].status is EvaluationStatus.CONFLICT
    assert conflict.results[0].conflicting_facts[0].source_reference == "quote:quoted_quantity"


@pytest.mark.parametrize(
    ("quoted_quantity", "expected_status", "expected_warnings"),
    [
        (2000, EvaluationStatus.MEETS, set()),
        (5000, EvaluationStatus.DOES_NOT_MEET, {ComparisonWarningCode.QUANTITY_MISMATCH}),
    ],
)
def test_approved_quantity_controls_result_and_warning_when_requirement_diverges(
    quoted_quantity: int,
    expected_status: EvaluationStatus,
    expected_warnings: set[ComparisonWarningCode],
) -> None:
    requirement = _requirement(RequirementKind.QUANTITY, {"quantity": 5000})
    result = _run([requirement], quantity=_resolved("quoted_quantity", quoted_quantity))
    assert result.results[0].status is expected_status
    assert _codes(result) == expected_warnings


def test_price_requires_explicit_target_currency_and_aligned_quantity() -> None:
    target = _requirement(RequirementKind.UNIT_PRICE, {"amount": "4.50", "currency": "USD"})
    price = _resolved("unit_price", PriceValue("4.5000", "USD"))
    result = _run([target], price=price)
    assert result.results[0].status is EvaluationStatus.MEETS
    assert result.results[0].selected_fact == price.selected
    assert _run([target], price=_resolved("unit_price", PriceValue("4.51", "USD"))).results[0].status is EvaluationStatus.DOES_NOT_MEET

    no_currency = _requirement(RequirementKind.UNIT_PRICE, {"amount": "4.50"})
    missing = _run([no_currency], price=price)
    assert missing.results[0].status is EvaluationStatus.UNKNOWN
    assert _codes(missing) == {ComparisonWarningCode.TARGET_CURRENCY_MISSING}

    different = _run([target], price=_resolved("unit_price", PriceValue("4.00", "EUR")),
                     quote_currency="EUR", currencies=("EUR", "EUR"))
    assert different.results[0].status is EvaluationStatus.UNKNOWN
    assert _codes(different) == {
        ComparisonWarningCode.TARGET_CURRENCY_MISMATCH,
        ComparisonWarningCode.SELECTED_PRICE_CURRENCY_MISMATCH,
    }

    incomplete = _run([target], price=_resolved("unit_price", PriceValue("4.00", None)))
    assert incomplete.results[0].status is EvaluationStatus.UNKNOWN
    assert _codes(incomplete) == {ComparisonWarningCode.PRICE_CURRENCY_MISSING}

    mismatched_quantity = _run([target], price=price, quantity=_resolved("quoted_quantity", 5000))
    assert mismatched_quantity.results[0].status is EvaluationStatus.UNKNOWN
    assert ComparisonWarningCode.QUANTITY_MISMATCH in _codes(mismatched_quantity)


def test_mixed_quote_currencies_block_price_but_preserve_other_results() -> None:
    target = _requirement(RequirementKind.UNIT_PRICE, {"amount": "5.00", "currency": "USD"})
    quantity = _requirement(RequirementKind.QUANTITY, {"quantity": 2000})
    result = _run([target, quantity], price=_resolved("unit_price", PriceValue("4.00", "USD")),
                  currencies=("USD", "EUR"))
    assert [item.status for item in result.results[:2]] == [EvaluationStatus.UNKNOWN, EvaluationStatus.MEETS]
    assert _codes(result) == {ComparisonWarningCode.MIXED_QUOTE_CURRENCIES}


def test_missing_quote_currency_and_source_conflict() -> None:
    target = _requirement(RequirementKind.UNIT_PRICE, {"amount": "5.00", "currency": "USD"})
    missing = _run([target], price=_resolved("unit_price", PriceValue("4.00", "USD")),
                   currencies=("USD", None))
    assert missing.results[0].status is EvaluationStatus.UNKNOWN
    assert _codes(missing) == {ComparisonWarningCode.PRICE_CURRENCY_MISSING}
    conflict = _run([target], price=_resolved("unit_price", PriceValue("4.00", "USD"), conflict=True))
    assert conflict.results[0].status is EvaluationStatus.CONFLICT
    assert conflict.results[0].conflicting_facts[0].source_reference == "quote:unit_price"


def test_own_quote_currency_differs_from_target_even_with_catalog_fallback() -> None:
    target = _requirement(RequirementKind.UNIT_PRICE, {"amount": "5.00", "currency": "USD"})
    result = _run([target], price=_resolved("unit_price", PriceValue("4.00", "USD")),
                  quote_currency="EUR", currencies=("EUR", "EUR"))
    assert result.results[0].status is EvaluationStatus.UNKNOWN
    assert _codes(result) == {ComparisonWarningCode.TARGET_CURRENCY_MISMATCH}


def test_catalog_price_currency_mismatch_is_distinct_from_quote_currency() -> None:
    target = _requirement(RequirementKind.UNIT_PRICE, {"amount": "5.00", "currency": "USD"})
    supplier = Supplier(
        id=uuid4(), name="Catalog fallback", country="Test", description="Fixture",
        indicative_price_amount="4.00", indicative_price_currency="EUR",
        evidence=[], capabilities=[],
    )
    quote = Quote(
        id=uuid4(), project_id=uuid4(), supplier_id=supplier.id,
        entry_type="MANUAL", status=QuoteStatus.CONFIRMED.value,
        values=[QuoteValue(
            id=uuid4(), field_key="currency", current_value="USD",
            current_origin=QuoteValueOrigin.USER_ENTERED.value, evidence=[],
        )],
    )
    price = resolve_commercial_facts(supplier, quote)["unit_price"]
    quote_currency = confirmed_quote_currency(quote)
    result = _run(
        [target], price=price, quote_currency=quote_currency, currencies=("USD", "USD"),
    )

    assert price.status is SourceResolutionStatus.SELECTED
    assert price.project_facts == ()
    assert price.general_facts == (price.selected,)
    assert result.results[0].status is EvaluationStatus.UNKNOWN
    assert result.results[0].selected_fact == price.selected
    assert result.results[0].selected_fact is not None
    assert result.results[0].selected_fact.context is FactContext.GENERAL_SUPPLIER
    assert result.results[0].selected_fact.value == PriceValue("4.00", "EUR")
    assert result.results[0].selected_fact.source_reference == f"supplier:{supplier.id}:unit_price"
    assert _codes(result) == {ComparisonWarningCode.SELECTED_PRICE_CURRENCY_MISMATCH}
    assert result.warnings[0].requirement_id == target.id


@pytest.mark.parametrize("price", [
    _resolved("unit_price"),
    _resolved("unit_price", PriceValue("4.00", "EUR"), conflict=True),
])
def test_currency_mismatch_warning_survives_missing_or_conflicting_price(
    price: SourceResolution,
) -> None:
    target = _requirement(RequirementKind.UNIT_PRICE, {"amount": "5.00", "currency": "USD"})
    result = _run([target], price=price, quote_currency="EUR", currencies=("EUR", "EUR"))
    assert result.results[0].status is (
        EvaluationStatus.CONFLICT if price.status is SourceResolutionStatus.CONFLICT
        else EvaluationStatus.UNKNOWN
    )
    assert _codes(result) == {ComparisonWarningCode.TARGET_CURRENCY_MISMATCH}


@pytest.mark.parametrize("price", [
    _resolved("unit_price"),
    _resolved("unit_price", PriceValue("4.00", "EUR"), conflict=True),
])
def test_no_target_mismatch_when_own_quote_currency_is_unavailable(
    price: SourceResolution,
) -> None:
    target = _requirement(RequirementKind.UNIT_PRICE, {"amount": "5.00", "currency": "USD"})
    result = _run([target], price=price, quote_currency=None, currencies=(None, "EUR"))
    assert ComparisonWarningCode.TARGET_CURRENCY_MISMATCH not in _codes(result)
    assert ComparisonWarningCode.PRICE_CURRENCY_MISSING in _codes(result)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("25 days", EvaluationStatus.MEETS), ("25 days after sample approval", EvaluationStatus.MEETS),
     ("25–30 days", EvaluationStatus.MEETS), ("25–30 days after sample approval", EvaluationStatus.MEETS),
     ("30-35 days", EvaluationStatus.UNKNOWN), ("35 days", EvaluationStatus.DOES_NOT_MEET),
     ("about a month", EvaluationStatus.UNKNOWN), ("35-30 days", EvaluationStatus.UNKNOWN)],
)
def test_lead_time_bounds(value: str, expected: EvaluationStatus) -> None:
    requirement = _requirement(RequirementKind.PRODUCTION_LEAD_TIME, {"max_days": 30})
    result = _run([requirement], lead=_resolved("production_lead_time", value))
    assert result.results[0].status is expected


def test_lead_time_missing_and_conflicting() -> None:
    requirement = _requirement(RequirementKind.PRODUCTION_LEAD_TIME, {"max_days": 30})
    assert _run([requirement]).results[0].status is EvaluationStatus.UNKNOWN
    assert _run([requirement], lead=_resolved("production_lead_time", "25 days", conflict=True)).results[0].status is EvaluationStatus.CONFLICT


def test_primary_three_quote_values_evaluate_deterministically_without_changing_fixtures() -> None:
    price_target = _requirement(RequirementKind.UNIT_PRICE, {"amount": "4.50", "currency": "USD"})
    lead_target = _requirement(RequirementKind.PRODUCTION_LEAD_TIME, {"max_days": 35})
    primary_values = (
        ("4.60", "32 days after sample approval", EvaluationStatus.DOES_NOT_MEET, EvaluationStatus.MEETS),
        ("4.20", "40 days after sample approval", EvaluationStatus.MEETS, EvaluationStatus.DOES_NOT_MEET),
        ("4.45", "25 days after sample approval", EvaluationStatus.MEETS, EvaluationStatus.MEETS),
    )
    for amount, lead, expected_price, expected_lead in primary_values:
        result = _run([price_target, lead_target],
                      price=_resolved("unit_price", PriceValue(amount, "USD")),
                      lead=_resolved("production_lead_time", lead))
        assert [item.status for item in result.results[:2]] == [expected_price, expected_lead]
        assert result.warnings == ()


@pytest.mark.parametrize(
    ("target", "committed", "expected"),
    [
        ({"kind": "DATE", "date": "2026-11-15"}, "2026-11-15", EvaluationStatus.MEETS),
        ({"kind": "DATE", "date": "2026-11-15"}, "2026-11-16", EvaluationStatus.DOES_NOT_MEET),
        ({"kind": "PERIOD", "label": "November", "start_date": "2026-11-01", "end_date": "2026-11-30"}, "2026-11-20", EvaluationStatus.MEETS),
        ({"kind": "PERIOD", "label": "November", "start_date": "2026-11-01", "end_date": "2026-11-30"}, "2026-12-01", EvaluationStatus.DOES_NOT_MEET),
        ({"kind": "PERIOD", "label": "November", "start_date": "2026-11-01", "end_date": "2026-11-30"}, "2026-10-31", EvaluationStatus.UNKNOWN),
        ({"kind": "PERIOD", "label": "Reversed", "start_date": "2026-11-30", "end_date": "2026-11-01"}, "2026-10-31", EvaluationStatus.UNKNOWN),
        ({"kind": "PERIOD", "label": "Reversed", "start_date": "2026-11-30", "end_date": "2026-11-01"}, "2026-11-15", EvaluationStatus.UNKNOWN),
        ({"kind": "PERIOD", "label": "Reversed", "start_date": "2026-11-30", "end_date": "2026-11-01"}, "2026-12-01", EvaluationStatus.UNKNOWN),
        ({"kind": "PERIOD", "label": "One day", "start_date": "2026-11-15", "end_date": "2026-11-15"}, "2026-11-15", EvaluationStatus.MEETS),
        ({"kind": "PERIOD", "label": "One day", "start_date": "2026-11-15", "end_date": "2026-11-15"}, "2026-11-16", EvaluationStatus.DOES_NOT_MEET),
        ({"kind": "PERIOD", "label": "November", "start_date": None, "end_date": "2026-11-30"}, "2026-11-20", EvaluationStatus.UNKNOWN),
        ({"kind": "PERIOD", "label": "November", "start_date": None, "end_date": "2026-11-30"}, "2026-11-30", EvaluationStatus.UNKNOWN),
        ({"kind": "PERIOD", "label": "November", "start_date": None, "end_date": "2026-11-30"}, "2026-12-01", EvaluationStatus.DOES_NOT_MEET),
        ({"kind": "PERIOD", "label": "November", "start_date": "2026-11-01", "end_date": None}, "2026-11-20", EvaluationStatus.UNKNOWN),
        ({"kind": "PERIOD", "label": "November", "start_date": None, "end_date": None}, "2026-11-20", EvaluationStatus.UNKNOWN),
    ],
)
def test_explicit_dated_delivery_contract(
    target: dict[str, object], committed: str, expected: EvaluationStatus,
) -> None:
    requirement = _requirement(RequirementKind.DELIVERY, target)
    result = _run([requirement], delivery=_resolved("delivery_date", committed))
    assert result.results[0].status is expected
    assert result.results[0].selected_fact is not None


def test_delivery_absence_and_conflict() -> None:
    requirement = _requirement(RequirementKind.DELIVERY, {"kind": "DATE", "date": "2026-11-15"})
    assert _run([requirement]).results[0].status is EvaluationStatus.UNKNOWN
    conflict = _run([requirement], delivery=_resolved("delivery_date", "2026-11-10", conflict=True))
    assert conflict.results[0].status is EvaluationStatus.CONFLICT
    assert conflict.results[0].conflicting_facts[0].source_reference == "quote:delivery_date"


def test_moq_uses_project_value_and_general_requires_support() -> None:
    requirement = _requirement(RequirementKind.MOQ, {"quantity": 1500})
    project = _run([requirement], moq=_resolved("moq", 1400))
    assert project.results[0].status is EvaluationStatus.MEETS
    assert project.results[0].selected_fact is not None
    general = resolve_sources("moq", general_facts=(SourceFact(
        "moq", 1400, FactContext.GENERAL_SUPPLIER, "supplier:moq",
    ),))
    assert _run([requirement], moq=general).results[0].status is EvaluationStatus.UNKNOWN
    assert _run([requirement], moq=_resolved("moq", 1400, conflict=True)).results[0].status is EvaluationStatus.CONFLICT


def test_subjective_requirement_remains_informational() -> None:
    requirement = _requirement(RequirementKind.INFORMATIONAL, {"subject": "OTHER_CONTEXT", "text": "premium"})
    result = _run([requirement])
    assert result.informational_requirement_ids == (requirement.id,)
    assert all(item.kind is not RequirementKind.INFORMATIONAL for item in result.results)
    assert {item.status for item in result.results} <= set(EvaluationStatus)


def test_existing_material_certification_and_capability_checks_are_reused() -> None:
    material = _requirement(RequirementKind.MATERIAL, {"value": "recycled polyester"})
    certification = _requirement(RequirementKind.CERTIFICATION, {"value": "grs"})
    capability = _requirement(RequirementKind.CAPABILITY, {
        "capability_key": "CUSTOM_BRANDING", "value": True,
    })
    evidence_ids = [uuid4() for _ in range(3)]
    supplier = SupplierEvaluationFacts(
        frozenset({("MATERIAL", "recycled polyester"), ("CERTIFICATION", "grs"),
                   ("CUSTOM_BRANDING", "true")}),
        None,
        (
            EvaluationEvidence(evidence_ids[0], "material:recycled polyester", "SUPPORTS"),
            EvaluationEvidence(evidence_ids[1], "certification:grs:current", "SUPPORTS"),
            EvaluationEvidence(evidence_ids[2], "capability:custom branding", "SUPPORTS"),
        ),
    )
    result = _run([material, certification, capability], supplier=supplier)
    assert [item.status for item in result.results[:3]] == [EvaluationStatus.MEETS] * 3
    assert [item.evidence_ids for item in result.results[:3]] == [(item,) for item in evidence_ids]


def test_adapter_uses_confirmed_quantity_and_does_not_invent_delivery_date() -> None:
    supplier = Supplier(id=uuid4(), name="Comparison Synthetic", country="Test", description="Fixture",
                        general_moq=1000, general_lead_time_days=35,
                        indicative_price_amount="4.00", indicative_price_currency="USD",
                        evidence=[], capabilities=[])
    quote = Quote(id=uuid4(), project_id=uuid4(), supplier_id=supplier.id,
                  entry_type="MANUAL", status=QuoteStatus.CONFIRMED.value, values=[])
    field = QuoteValue(id=uuid4(), field_key="quoted_quantity", current_value=2000,
                       current_origin=QuoteValueOrigin.USER_CORRECTED.value,
                       ai_extracted_value=5000, evidence=[])
    evidence_id = uuid4()
    field.evidence.append(QuoteFieldEvidence(id=evidence_id, document_block_id=uuid4(), evidence_value=5000))
    quote.values.append(field)
    currency = QuoteValue(id=uuid4(), field_key="currency", current_value="USD",
                          current_origin=QuoteValueOrigin.USER_ENTERED.value,
                          ai_extracted_value=None, evidence=[])
    quote.values.append(currency)
    quantity = resolve_quoted_quantity(quote)
    assert quantity.status is SourceResolutionStatus.SELECTED
    assert quantity.selected is not None
    assert quantity.selected.value == 2000
    assert quantity.selected.provenance_evidence_ids == (evidence_id,)
    assert quantity.selected.supporting_evidence_ids == ()
    assert resolve_delivery_commitment(quote).status is SourceResolutionStatus.UNAVAILABLE
    assert confirmed_quote_currency(quote) == "USD"
    currency.evidence.extend((
        QuoteFieldEvidence(id=uuid4(), document_block_id=uuid4(), evidence_value="USD"),
        QuoteFieldEvidence(id=uuid4(), document_block_id=uuid4(), evidence_value="EUR"),
    ))
    conflicting_currency = confirmed_quote_currency(quote)
    assert conflicting_currency is None
    price_target = _requirement(
        RequirementKind.UNIT_PRICE, {"amount": "5.00", "currency": "EUR"},
    )
    currency_conflict_result = _run(
        [price_target], price=_resolved("unit_price", PriceValue("4.00", "USD"), conflict=True),
        quote_currency=conflicting_currency, currencies=(None, "USD"),
    )
    assert currency_conflict_result.results[0].status is EvaluationStatus.CONFLICT
    assert ComparisonWarningCode.TARGET_CURRENCY_MISMATCH not in _codes(currency_conflict_result)
    delivery_requirement = _requirement(
        RequirementKind.DELIVERY, {"kind": "DATE", "date": "2026-11-15"},
    )
    assert _run([delivery_requirement], delivery=resolve_delivery_commitment(quote)).results[0].status is EvaluationStatus.UNKNOWN
    quote.status = QuoteStatus.NEEDS_REVIEW.value
    assert resolve_quoted_quantity(quote).status is SourceResolutionStatus.UNAVAILABLE
    assert resolve_delivery_commitment(quote).status is SourceResolutionStatus.UNAVAILABLE
    assert confirmed_quote_currency(quote) is None
    assert resolve_commercial_facts(supplier, quote)["unit_price"].selected is not None
