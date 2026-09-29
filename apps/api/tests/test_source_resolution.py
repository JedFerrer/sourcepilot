"""M4-U1 source precedence and provenance behavior."""

from uuid import uuid4

import pytest

from sourcepilot.comparison.facts import resolve_commercial_facts
from sourcepilot.comparison.source_resolution import (
    FactContext,
    PriceValue,
    SourceFact,
    SourceResolutionStatus,
    resolve_sources,
)
from sourcepilot.persistence.models import (
    Quote,
    QuoteFieldEvidence,
    QuoteValue,
    Supplier,
    SupplierEvidence,
)
from sourcepilot.quotes.domain import QuoteStatus, QuoteValueOrigin


def _supplier(*, moq: int | None = 1000) -> Supplier:
    return Supplier(
        id=uuid4(), name="Synthetic Supplier", country="Test", description="Fixture",
        general_moq=moq, general_lead_time_days=35,
        indicative_price_amount="4.00", indicative_price_currency="USD",
        evidence=[], capabilities=[],
    )


def _quote(supplier: Supplier, status: QuoteStatus = QuoteStatus.CONFIRMED) -> Quote:
    return Quote(
        id=uuid4(), project_id=uuid4(), supplier_id=supplier.id,
        entry_type="MANUAL", status=status.value, values=[],
    )


def _value(
    quote: Quote, key: str, value: object | None,
    origin: QuoteValueOrigin = QuoteValueOrigin.USER_ENTERED,
) -> QuoteValue:
    field = QuoteValue(
        id=uuid4(), field_key=key, current_value=value, current_origin=origin.value,
        ai_extracted_value="30" if origin is QuoteValueOrigin.USER_CORRECTED else None,
        evidence=[],
    )
    quote.values.append(field)
    return field


@pytest.mark.parametrize("origin", list(QuoteValueOrigin))
def test_confirmation_controls_authority_for_every_origin(origin: QuoteValueOrigin) -> None:
    supplier = _supplier()
    quote = _quote(supplier)
    field = _value(quote, "production_lead_time", "25 days", origin)
    resolved = resolve_commercial_facts(supplier, quote)["production_lead_time"]
    assert resolved.status is SourceResolutionStatus.SELECTED
    assert resolved.selected is not None
    assert resolved.selected.value == "25 days"
    assert resolved.selected.source_reference == f"quote-value:{field.id}"
    assert resolved.general_facts[0].value == 35


@pytest.mark.parametrize(
    "status", [QuoteStatus.NEEDS_REVIEW, QuoteStatus.PROCESSING, QuoteStatus.FAILED]
)
def test_unconfirmed_quote_cannot_override_catalog(status: QuoteStatus) -> None:
    supplier = _supplier()
    quote = _quote(supplier, status)
    _value(quote, "moq", 200)
    resolved = resolve_commercial_facts(supplier, quote)["moq"]
    assert resolved.selected is not None
    assert resolved.selected.value == 1000
    assert resolved.project_facts == ()


def test_null_confirmed_value_and_missing_quote_fall_back_to_general() -> None:
    supplier = _supplier()
    quote = _quote(supplier)
    _value(quote, "moq", None)
    for current_quote in (quote, None):
        resolved = resolve_commercial_facts(supplier, current_quote)["moq"]
        assert resolved.status is SourceResolutionStatus.SELECTED
        assert resolved.selected is not None
        assert resolved.selected.value == 1000
        assert resolved.selected.context is FactContext.GENERAL_SUPPLIER


def test_null_confirmed_quote_with_unresolved_pdf_alternatives_blocks_fallback() -> None:
    supplier = _supplier()
    quote = _quote(supplier)
    field = _value(quote, "production_lead_time", None, QuoteValueOrigin.AI_EXTRACTED)
    first_id, second_id = uuid4(), uuid4()
    field.evidence.extend((
        QuoteFieldEvidence(
            id=first_id, document_block_id=uuid4(), evidence_value="20 days",
        ),
        QuoteFieldEvidence(
            id=second_id, document_block_id=uuid4(), evidence_value="30–35 days",
        ),
    ))

    resolved = resolve_commercial_facts(supplier, quote)["production_lead_time"]
    assert resolved.status is SourceResolutionStatus.CONFLICT
    assert resolved.selected is None
    assert resolved.general_facts[0].value == 35
    assert len(resolved.project_facts) == 1
    project = resolved.project_facts[0]
    assert project.value is None
    assert project.source_reference == f"quote-value:{field.id}"
    assert project.has_same_context_conflict
    assert project.supporting_evidence_ids == ()
    assert set(project.provenance_evidence_ids) == {first_id, second_id}


def test_uncorrected_confirmed_lead_time_with_unresolved_alternatives_conflicts() -> None:
    supplier = _supplier()
    quote = _quote(supplier)
    field = _value(quote, "production_lead_time", "20 days", QuoteValueOrigin.AI_EXTRACTED)
    first_id, second_id = uuid4(), uuid4()
    field.evidence.extend((
        QuoteFieldEvidence(id=first_id, document_block_id=uuid4(), evidence_value="20 days"),
        QuoteFieldEvidence(id=second_id, document_block_id=uuid4(), evidence_value="30–35 days"),
    ))

    resolved = resolve_commercial_facts(supplier, quote)["production_lead_time"]
    assert resolved.status is SourceResolutionStatus.CONFLICT
    assert resolved.selected is None
    assert resolved.general_facts[0].value == 35
    project = resolved.project_facts[0]
    assert project.value == "20 days"
    assert project.has_same_context_conflict
    assert project.supporting_evidence_ids == ()
    assert set(project.provenance_evidence_ids) == {first_id, second_id}


def test_surrounding_whitespace_does_not_conflict_in_pdf_lead_time_alternatives() -> None:
    supplier = _supplier()
    quote = _quote(supplier)
    field = _value(quote, "production_lead_time", "25 days", QuoteValueOrigin.AI_EXTRACTED)
    first_id, second_id = uuid4(), uuid4()
    field.evidence.extend((
        QuoteFieldEvidence(id=first_id, document_block_id=uuid4(), evidence_value="25 days"),
        QuoteFieldEvidence(id=second_id, document_block_id=uuid4(), evidence_value="25 days "),
    ))

    resolved = resolve_commercial_facts(supplier, quote)["production_lead_time"]
    assert resolved.status is SourceResolutionStatus.SELECTED
    assert resolved.selected is not None
    assert resolved.selected.value == "25 days"
    assert set(resolved.selected.supporting_evidence_ids) == {first_id, second_id}


def test_corrected_lead_time_resolves_retained_conflicting_alternatives() -> None:
    supplier = _supplier()
    quote = _quote(supplier)
    field = _value(quote, "production_lead_time", "25 days", QuoteValueOrigin.USER_CORRECTED)
    first_id, second_id = uuid4(), uuid4()
    field.evidence.extend((
        QuoteFieldEvidence(id=first_id, document_block_id=uuid4(), evidence_value="20 days"),
        QuoteFieldEvidence(id=second_id, document_block_id=uuid4(), evidence_value="30–35 days"),
    ))

    resolved = resolve_commercial_facts(supplier, quote)["production_lead_time"]
    assert resolved.status is SourceResolutionStatus.SELECTED
    assert resolved.selected is not None
    assert resolved.selected.value == "25 days"
    assert resolved.selected.has_same_context_conflict is False
    assert resolved.selected.supporting_evidence_ids == ()
    assert set(resolved.selected.provenance_evidence_ids) == {first_id, second_id}


def test_no_source_is_unavailable_without_requirement_evaluation() -> None:
    supplier = _supplier(moq=None)
    resolved = resolve_commercial_facts(supplier, None)["moq"]
    assert resolved.status is SourceResolutionStatus.UNAVAILABLE
    assert resolved.selected is None
    assert resolved.project_facts == resolved.general_facts == ()


def test_catalog_evidence_keeps_support_separate_from_other_provenance() -> None:
    supplier = _supplier()
    support_id, partial_id = uuid4(), uuid4()
    supplier.evidence.extend((
        SupplierEvidence(
            id=support_id, claim_key="moq:general", evidence_state="SUPPORTS",
            source_type="CATALOG", source_label="Catalog", evidence_text="MOQ 1000",
        ),
        SupplierEvidence(
            id=partial_id, claim_key="moq:general", evidence_state="PARTIAL",
            source_type="CATALOG", source_label="Draft", evidence_text="May vary",
        ),
    ))
    selected = resolve_commercial_facts(supplier, None)["moq"].selected
    assert selected is not None
    assert selected.supporting_evidence_ids == (support_id,)
    assert selected.provenance_evidence_ids == (partial_id,)


def test_contradictory_general_moq_evidence_blocks_catalog_selection() -> None:
    supplier = _supplier()
    support_id, contradiction_id = uuid4(), uuid4()
    supplier.evidence.extend((
        SupplierEvidence(
            id=support_id, claim_key="moq:general", evidence_state="SUPPORTS",
            source_type="CATALOG", source_label="Catalog", evidence_text="MOQ 1000",
        ),
        SupplierEvidence(
            id=contradiction_id, claim_key="moq:general", evidence_state="CONTRADICTS",
            source_type="CATALOG", source_label="Other terms", evidence_text="MOQ 500",
        ),
    ))
    resolved = resolve_commercial_facts(supplier, None)["moq"]
    assert resolved.status is SourceResolutionStatus.CONFLICT
    assert resolved.selected is None
    assert resolved.general_facts[0].value == 1000
    assert resolved.general_facts[0].supporting_evidence_ids == (support_id,)
    assert resolved.general_facts[0].provenance_evidence_ids == (contradiction_id,)


def test_contradiction_only_general_moq_evidence_blocks_catalog_selection() -> None:
    supplier = _supplier()
    contradiction_id = uuid4()
    supplier.evidence.append(SupplierEvidence(
        id=contradiction_id, claim_key="moq:general", evidence_state="CONTRADICTS",
        source_type="CATALOG", source_label="Other terms", evidence_text="MOQ 500",
    ))
    resolved = resolve_commercial_facts(supplier, None)["moq"]
    assert resolved.status is SourceResolutionStatus.CONFLICT
    assert resolved.selected is None
    assert resolved.general_facts[0].value == 1000
    assert resolved.general_facts[0].supporting_evidence_ids == ()
    assert resolved.general_facts[0].provenance_evidence_ids == (contradiction_id,)


def test_quote_price_and_currency_are_one_source_even_when_currency_missing() -> None:
    supplier = _supplier()
    quote = _quote(supplier)
    price = _value(quote, "unit_price", "4.50")
    resolved = resolve_commercial_facts(supplier, quote)["unit_price"]
    assert resolved.selected is not None
    assert resolved.selected.value == PriceValue("4.50", None)
    assert resolved.selected.source_reference == f"quote-value:{price.id}"
    assert tuple(item.field_key for item in resolved.selected.component_attributions) == ("unit_price",)
    assert resolved.general_facts[0].value == PriceValue("4.00", "USD")
    assert tuple(item.field_key for item in resolved.general_facts[0].component_attributions) == (
        "unit_price", "currency"
    )
    _value(quote, "currency", "EUR")
    euro = resolve_commercial_facts(supplier, quote)["unit_price"].selected
    assert euro is not None
    assert euro.value == PriceValue("4.50", "EUR")
    assert euro.related_source_references == (f"quote-value:{quote.values[-1].id}",)
    assert tuple(item.source_reference for item in euro.component_attributions) == (
        f"quote-value:{price.id}", f"quote-value:{quote.values[-1].id}"
    )
    price.current_value = None
    fallback = resolve_commercial_facts(supplier, quote)["unit_price"].selected
    assert fallback is not None
    assert fallback.value == PriceValue("4.00", "USD")


def test_conflicting_currency_alternatives_block_confirmed_price_selection() -> None:
    supplier = _supplier()
    quote = _quote(supplier)
    price = _value(quote, "unit_price", "4.50", QuoteValueOrigin.AI_EXTRACTED)
    currency = _value(quote, "currency", None, QuoteValueOrigin.AI_EXTRACTED)
    usd_id, eur_id = uuid4(), uuid4()
    currency.evidence.extend((
        QuoteFieldEvidence(id=usd_id, document_block_id=uuid4(), evidence_value="USD"),
        QuoteFieldEvidence(id=eur_id, document_block_id=uuid4(), evidence_value="EUR"),
    ))

    resolved = resolve_commercial_facts(supplier, quote)["unit_price"]
    assert resolved.status is SourceResolutionStatus.CONFLICT
    assert resolved.selected is None
    assert resolved.general_facts[0].value == PriceValue("4.00", "USD")
    assert len(resolved.project_facts) == 1
    project = resolved.project_facts[0]
    assert project.value == PriceValue("4.50", None)
    assert project.has_same_context_conflict
    assert project.source_reference == f"quote-value:{price.id}"
    assert project.related_source_references == (f"quote-value:{currency.id}",)
    assert project.supporting_evidence_ids == ()
    amount, currency_part = project.component_attributions
    assert amount.field_key == "unit_price"
    assert currency_part.field_key == "currency"
    assert currency_part.source_reference == f"quote-value:{currency.id}"
    assert currency_part.supporting_evidence_ids == ()
    assert set(currency_part.provenance_evidence_ids) == {usd_id, eur_id}
    assert {item.evidence_value for item in currency.evidence} == {"USD", "EUR"}


def test_conflicting_amount_alternatives_block_confirmed_price_selection() -> None:
    supplier = _supplier()
    quote = _quote(supplier)
    price = _value(quote, "unit_price", "4.50", QuoteValueOrigin.AI_EXTRACTED)
    price.ai_extracted_value = "4.50"
    _value(quote, "currency", "USD")
    first_id, second_id = uuid4(), uuid4()
    price.evidence.extend((
        QuoteFieldEvidence(id=first_id, document_block_id=uuid4(), evidence_value="4.50"),
        QuoteFieldEvidence(id=second_id, document_block_id=uuid4(), evidence_value="5.00"),
    ))

    resolved = resolve_commercial_facts(supplier, quote)["unit_price"]
    assert resolved.status is SourceResolutionStatus.CONFLICT
    assert resolved.selected is None
    assert resolved.general_facts[0].value == PriceValue("4.00", "USD")
    project = resolved.project_facts[0]
    assert project.has_same_context_conflict
    amount = project.component_attributions[0]
    assert amount.supporting_evidence_ids == ()
    assert set(amount.provenance_evidence_ids) == {first_id, second_id}


def test_equivalent_pdf_price_amounts_do_not_conflict() -> None:
    supplier = _supplier()
    quote = _quote(supplier)
    price = _value(quote, "unit_price", "4.50", QuoteValueOrigin.AI_EXTRACTED)
    _value(quote, "currency", "USD")
    first_id, second_id = uuid4(), uuid4()
    price.evidence.extend((
        QuoteFieldEvidence(id=first_id, document_block_id=uuid4(), evidence_value="4.50"),
        QuoteFieldEvidence(id=second_id, document_block_id=uuid4(), evidence_value="4.500"),
    ))

    resolved = resolve_commercial_facts(supplier, quote)["unit_price"]
    assert resolved.status is SourceResolutionStatus.SELECTED
    assert resolved.selected is not None
    assert resolved.selected.value == PriceValue("4.50", "USD")
    assert resolved.selected.component_attributions[0].supporting_evidence_ids == (
        *sorted((first_id, second_id), key=str),
    )
    assert [item.evidence_value for item in price.evidence] == ["4.50", "4.500"]


def test_corrected_price_and_currency_resolve_conflicting_pdf_alternatives() -> None:
    supplier = _supplier()
    quote = _quote(supplier)
    price = _value(quote, "unit_price", "4.75", QuoteValueOrigin.USER_CORRECTED)
    currency = _value(quote, "currency", "GBP", QuoteValueOrigin.USER_CORRECTED)
    price.ai_extracted_value = None
    currency.ai_extracted_value = None
    price_ids = (uuid4(), uuid4())
    currency_ids = (uuid4(), uuid4())
    price.evidence.extend((
        QuoteFieldEvidence(id=price_ids[0], document_block_id=uuid4(), evidence_value="4.50"),
        QuoteFieldEvidence(id=price_ids[1], document_block_id=uuid4(), evidence_value="5.00"),
    ))
    currency.evidence.extend((
        QuoteFieldEvidence(id=currency_ids[0], document_block_id=uuid4(), evidence_value="USD"),
        QuoteFieldEvidence(id=currency_ids[1], document_block_id=uuid4(), evidence_value="EUR"),
    ))

    resolved = resolve_commercial_facts(supplier, quote)["unit_price"]
    assert resolved.status is SourceResolutionStatus.SELECTED
    assert resolved.selected is not None
    assert resolved.selected.value == PriceValue("4.75", "GBP")
    assert resolved.selected.source_reference == f"quote-value:{price.id}"
    assert resolved.selected.related_source_references == (f"quote-value:{currency.id}",)
    assert resolved.selected.has_same_context_conflict is False
    amount, currency_part = resolved.selected.component_attributions
    assert amount.source_reference == f"quote-value:{price.id}"
    assert amount.supporting_evidence_ids == ()
    assert set(amount.provenance_evidence_ids) == set(price_ids)
    assert currency_part.source_reference == f"quote-value:{currency.id}"
    assert currency_part.supporting_evidence_ids == ()
    assert set(currency_part.provenance_evidence_ids) == set(currency_ids)
    assert [item.evidence_value for item in price.evidence] == ["4.50", "5.00"]
    assert [item.evidence_value for item in currency.evidence] == ["USD", "EUR"]


def test_correction_keeps_pdf_evidence_as_provenance_not_support() -> None:
    supplier = _supplier()
    quote = _quote(supplier)
    field = _value(quote, "production_lead_time", "25 days", QuoteValueOrigin.USER_CORRECTED)
    field.ai_extracted_value = "30 days"
    evidence_id = uuid4()
    field.evidence.append(QuoteFieldEvidence(
        id=evidence_id, document_block_id=uuid4(), evidence_value="30 days"
    ))
    resolved = resolve_commercial_facts(supplier, quote)["production_lead_time"]
    assert resolved.selected is not None
    assert resolved.selected.value == "25 days"
    assert resolved.selected.supporting_evidence_ids == ()
    assert resolved.selected.provenance_evidence_ids == (evidence_id,)
    assert field.ai_extracted_value == "30 days"
    assert field.evidence[0].evidence_value == "30 days"


def test_corrected_currency_does_not_make_old_pdf_evidence_support_the_price_pair() -> None:
    supplier = _supplier()
    quote = _quote(supplier)
    price = _value(quote, "unit_price", "4.50", QuoteValueOrigin.AI_EXTRACTED)
    currency = _value(quote, "currency", "EUR", QuoteValueOrigin.USER_CORRECTED)
    price_evidence_id, currency_evidence_id = uuid4(), uuid4()
    price.evidence.append(QuoteFieldEvidence(
        id=price_evidence_id, document_block_id=uuid4(), evidence_value="4.50"
    ))
    currency.evidence.append(QuoteFieldEvidence(
        id=currency_evidence_id, document_block_id=uuid4(), evidence_value="USD"
    ))
    resolved = resolve_commercial_facts(supplier, quote)["unit_price"]
    assert resolved.selected is not None
    assert resolved.selected.value == PriceValue("4.50", "EUR")
    assert resolved.selected.supporting_evidence_ids == ()
    assert resolved.selected.provenance_evidence_ids == ()
    amount, currency_part = resolved.selected.component_attributions
    assert amount.field_key == "unit_price"
    assert amount.source_reference == f"quote-value:{price.id}"
    assert amount.supporting_evidence_ids == (price_evidence_id,)
    assert amount.provenance_evidence_ids == ()
    assert currency_part.field_key == "currency"
    assert currency_part.source_reference == f"quote-value:{currency.id}"
    assert currency_part.supporting_evidence_ids == ()
    assert currency_part.provenance_evidence_ids == (currency_evidence_id,)


def test_cleared_currency_retains_its_provenance_beside_supported_price() -> None:
    supplier = _supplier()
    quote = _quote(supplier)
    price = _value(quote, "unit_price", "4.50", QuoteValueOrigin.AI_EXTRACTED)
    currency = _value(quote, "currency", None, QuoteValueOrigin.USER_CORRECTED)
    currency.ai_extracted_value = "USD"
    price_evidence_id, currency_evidence_id = uuid4(), uuid4()
    price.evidence.append(QuoteFieldEvidence(
        id=price_evidence_id, document_block_id=uuid4(), evidence_value="4.50"
    ))
    currency.evidence.append(QuoteFieldEvidence(
        id=currency_evidence_id, document_block_id=uuid4(), evidence_value="USD"
    ))

    resolved = resolve_commercial_facts(supplier, quote)["unit_price"]
    assert resolved.status is SourceResolutionStatus.SELECTED
    assert resolved.selected is not None
    assert resolved.selected.value == PriceValue("4.50", None)
    assert resolved.selected.related_source_references == (f"quote-value:{currency.id}",)
    assert resolved.selected.supporting_evidence_ids == ()
    assert resolved.selected.provenance_evidence_ids == ()
    amount, currency_part = resolved.selected.component_attributions
    assert amount.field_key == "unit_price"
    assert amount.source_reference == f"quote-value:{price.id}"
    assert amount.supporting_evidence_ids == (price_evidence_id,)
    assert amount.provenance_evidence_ids == ()
    assert currency_part.field_key == "currency"
    assert currency_part.source_reference == f"quote-value:{currency.id}"
    assert currency_part.supporting_evidence_ids == ()
    assert currency_part.provenance_evidence_ids == (currency_evidence_id,)


def test_corrected_price_keeps_unchanged_currency_evidence_as_support() -> None:
    supplier = _supplier()
    quote = _quote(supplier)
    price = _value(quote, "unit_price", "4.50", QuoteValueOrigin.USER_CORRECTED)
    currency = _value(quote, "currency", "USD", QuoteValueOrigin.AI_EXTRACTED)
    price_evidence_id, currency_evidence_id = uuid4(), uuid4()
    price.evidence.append(QuoteFieldEvidence(
        id=price_evidence_id, document_block_id=uuid4(), evidence_value="4.22"
    ))
    currency.evidence.append(QuoteFieldEvidence(
        id=currency_evidence_id, document_block_id=uuid4(), evidence_value="USD"
    ))
    resolved = resolve_commercial_facts(supplier, quote)["unit_price"]
    assert resolved.selected is not None
    assert resolved.selected.value == PriceValue("4.50", "USD")
    assert resolved.selected.supporting_evidence_ids == ()
    assert resolved.selected.provenance_evidence_ids == ()
    amount, currency_part = resolved.selected.component_attributions
    assert amount.field_key == "unit_price"
    assert amount.source_reference == f"quote-value:{price.id}"
    assert amount.supporting_evidence_ids == ()
    assert amount.provenance_evidence_ids == (price_evidence_id,)
    assert currency_part.field_key == "currency"
    assert currency_part.source_reference == f"quote-value:{currency.id}"
    assert currency_part.supporting_evidence_ids == (currency_evidence_id,)
    assert currency_part.provenance_evidence_ids == ()


def test_cross_context_difference_is_not_conflict_but_same_context_can_be() -> None:
    general = SourceFact("production_lead_time", "30–40 days", FactContext.GENERAL_SUPPLIER,
                         "supplier:typical")
    project = SourceFact("production_lead_time", "25 days", FactContext.PROJECT_QUOTE,
                         "quote:confirmed")
    resolved = resolve_sources("production_lead_time", project_facts=[project], general_facts=[general])
    assert resolved.status is SourceResolutionStatus.SELECTED
    assert resolved.selected == project
    assert resolved.general_facts == (general,)

    incompatible = SourceFact("production_lead_time", "35 days", FactContext.PROJECT_QUOTE,
                              "quote:second-page")
    conflict = resolve_sources(
        "production_lead_time", project_facts=[project, incompatible], general_facts=[general]
    )
    assert conflict.status is SourceResolutionStatus.CONFLICT
    assert conflict.selected is None
    assert conflict.project_facts == (project, incompatible)


def test_equivalent_scalar_text_does_not_create_same_context_conflict() -> None:
    first = SourceFact("production_lead_time", "25 days", FactContext.PROJECT_QUOTE,
                       "quote:page-one")
    equivalent = SourceFact("production_lead_time", "25 days ", FactContext.PROJECT_QUOTE,
                            "quote:page-two")
    resolved = resolve_sources("production_lead_time", project_facts=[first, equivalent])
    assert resolved.status is SourceResolutionStatus.SELECTED
    assert resolved.selected == first


def test_equivalent_price_scale_does_not_create_same_context_conflict() -> None:
    first = SourceFact("unit_price", PriceValue("4.50", "USD"), FactContext.PROJECT_QUOTE,
                       "quote:page-one")
    equivalent = SourceFact("unit_price", PriceValue("4.5000", "USD"), FactContext.PROJECT_QUOTE,
                            "quote:page-two")
    resolved = resolve_sources("unit_price", project_facts=[first, equivalent])
    assert resolved.status is SourceResolutionStatus.SELECTED
    assert resolved.selected == first


def test_wrong_supplier_or_fact_context_is_rejected() -> None:
    supplier = _supplier()
    another_supplier = _supplier()
    with pytest.raises(ValueError, match="another supplier"):
        resolve_commercial_facts(supplier, _quote(another_supplier))
    wrong_context = SourceFact("moq", 100, FactContext.GENERAL_SUPPLIER, "catalog")
    with pytest.raises(ValueError, match="wrong field or context"):
        resolve_sources("moq", project_facts=[wrong_context])
