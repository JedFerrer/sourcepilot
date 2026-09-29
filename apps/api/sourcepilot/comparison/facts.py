"""Map persisted supplier and quote values to source-resolution inputs."""

from decimal import Decimal, InvalidOperation

from sourcepilot.comparison.source_resolution import (
    FactComponentAttribution,
    FactContext,
    PriceValue,
    SourceFact,
    SourceResolution,
    resolve_sources,
)
from sourcepilot.persistence.models import Quote, QuoteValue, Supplier
from sourcepilot.quotes.domain import QuoteStatus, QuoteValueOrigin


def resolve_commercial_facts(
    supplier: Supplier, quote: Quote | None,
) -> dict[str, SourceResolution]:
    """Resolve catalog/quote overlap without making requirement judgments."""
    if quote is not None and quote.supplier_id != supplier.id:
        raise ValueError("Quote belongs to another supplier.")
    values = (
        {item.field_key: item for item in quote.values}
        if quote is not None and quote.status == QuoteStatus.CONFIRMED else {}
    )
    return {
        "moq": resolve_sources(
            "moq", project_facts=_quote_fact(values.get("moq"), "moq"),
            general_facts=_general_fact(supplier, "moq", supplier.general_moq),
        ),
        "production_lead_time": resolve_sources(
            "production_lead_time",
            project_facts=_quote_fact(values.get("production_lead_time"), "production_lead_time"),
            general_facts=_general_fact(
                supplier, "production_lead_time", supplier.general_lead_time_days
            ),
        ),
        "unit_price": resolve_sources(
            "unit_price",
            project_facts=_quote_price_fact(values),
            general_facts=_general_fact(
                supplier, "unit_price",
                PriceValue(str(supplier.indicative_price_amount), supplier.indicative_price_currency)
                if supplier.indicative_price_amount is not None else None,
            ),
        ),
    }


def resolve_quoted_quantity(quote: Quote | None) -> SourceResolution:
    """Expose only the current value of a confirmed project's quote."""
    values = (
        {item.field_key: item for item in quote.values}
        if quote is not None and quote.status == QuoteStatus.CONFIRMED else {}
    )
    return resolve_sources(
        "quoted_quantity",
        project_facts=_quote_fact(values.get("quoted_quantity"), "quoted_quantity"),
    )


def resolve_delivery_commitment(quote: Quote | None) -> SourceResolution:
    """Current quote fields have no structured dated delivery commitment."""
    return resolve_sources("delivery_date")


def confirmed_quote_currency(quote: Quote | None) -> str | None:
    """Read a quote's own confirmed currency, independently of catalog price fallback."""
    if quote is None or quote.status != QuoteStatus.CONFIRMED:
        return None
    currency = next((item for item in quote.values if item.field_key == "currency"), None)
    if currency is None or currency.current_value is None or unresolved_quote_conflict(currency):
        return None
    return str(currency.current_value)


def _quote_price_fact(values: dict[str, QuoteValue]) -> tuple[SourceFact, ...]:
    price = values.get("unit_price")
    currency = values.get("currency")
    price_conflict = price is not None and unresolved_quote_conflict(price)
    currency_conflict = currency is not None and unresolved_quote_conflict(currency)
    if (price is None or price.current_value is None) and not (price_conflict or currency_conflict):
        return ()
    if price is not None and price.current_value is None and price_conflict:
        evidence_ids = tuple(sorted((item.id for item in price.evidence), key=str))
        attribution = FactComponentAttribution(
            "unit_price", f"quote-value:{price.id}", provenance_evidence_ids=evidence_ids,
        )
        currency_attributions = (
            _component_attribution(currency, conflict=currency_conflict),
        ) if currency is not None else ()
        return (SourceFact(
            field_key="unit_price", value=None, context=FactContext.PROJECT_QUOTE,
            source_reference=f"quote-value:{price.id}",
            provenance_evidence_ids=evidence_ids,
            component_attributions=(attribution, *currency_attributions),
            has_same_context_conflict=True,
        ),)
    components = tuple(component for component in (price, currency) if component is not None)
    attributions = tuple(
        _component_attribution(
            component,
            conflict=(price_conflict and component is price)
            or (currency_conflict and component is currency),
        )
        for component in components
    )
    primary = price if price is not None else currency
    assert primary is not None
    return (SourceFact(
        field_key="unit_price",
        value=PriceValue(
            str(price.current_value),
            str(currency.current_value) if currency is not None
            and currency.current_value is not None else None,
        ) if price is not None and price.current_value is not None else None,
        context=FactContext.PROJECT_QUOTE,
        source_reference=f"quote-value:{primary.id}",
        related_source_references=(f"quote-value:{currency.id}",)
        if price is not None and currency is not None else (),
        component_attributions=attributions,
        has_same_context_conflict=price_conflict or currency_conflict,
    ),)


def _component_attribution(
    value: QuoteValue, *, conflict: bool = False,
) -> FactComponentAttribution:
    evidence_ids = tuple(sorted((item.id for item in value.evidence), key=str))
    corrected = value.current_origin == QuoteValueOrigin.USER_CORRECTED
    return FactComponentAttribution(
        field_key=value.field_key,
        source_reference=f"quote-value:{value.id}",
        supporting_evidence_ids=() if corrected or conflict else evidence_ids,
        provenance_evidence_ids=evidence_ids if corrected or conflict else (),
    )


def _quote_fact(
    value: QuoteValue | None, field_key: str, selected_value: object | None = None,
) -> tuple[SourceFact, ...]:
    if value is None:
        return ()
    conflict = unresolved_quote_conflict(value)
    if value.current_value is None and not conflict:
        return ()
    evidence_ids = tuple(sorted((item.id for item in value.evidence), key=str))
    corrected = value.current_origin == QuoteValueOrigin.USER_CORRECTED
    return (SourceFact(
        field_key=field_key,
        value=selected_value if selected_value is not None else value.current_value,
        context=FactContext.PROJECT_QUOTE,
        source_reference=f"quote-value:{value.id}",
        supporting_evidence_ids=() if corrected or conflict else evidence_ids,
        provenance_evidence_ids=evidence_ids if corrected or conflict else (),
        has_same_context_conflict=conflict,
    ),)


def unresolved_quote_conflict(value: QuoteValue) -> bool:
    """Recognize distinct saved PDF interpretations without choosing one."""
    if (value.current_origin == QuoteValueOrigin.USER_CORRECTED
            and value.current_value is not None):
        return False
    alternatives = [item.evidence_value for item in value.evidence
                    if item.evidence_value is not None]
    if len(alternatives) < 2:
        return False
    return any(not _same_pdf_alternative(value.field_key, item, alternatives[0])
               for item in alternatives[1:])


def _same_pdf_alternative(field_key: str, left: object, right: object) -> bool:
    if field_key == "unit_price":
        try:
            return Decimal(str(left)) == Decimal(str(right))
        except InvalidOperation:
            pass
    if isinstance(left, str) and isinstance(right, str):
        return left.strip() == right.strip()
    return type(left) is type(right) and left == right


def _general_fact(
    supplier: Supplier, field_key: str, value: object | None,
) -> tuple[SourceFact, ...]:
    if value is None:
        return ()
    claim_key = "moq:general" if field_key == "moq" else None
    evidence_ids = tuple(sorted((item.id for item in supplier.evidence
                                 if item.claim_key == claim_key
                                 and item.evidence_state == "SUPPORTS"), key=str))
    other_evidence_ids = tuple(sorted((item.id for item in supplier.evidence
                                       if item.claim_key == claim_key
                                       and item.evidence_state != "SUPPORTS"), key=str))
    has_same_context_conflict = any(
        item.claim_key == claim_key and item.evidence_state == "CONTRADICTS"
        for item in supplier.evidence
    )
    source_reference = f"supplier:{supplier.id}:{field_key}"
    return (SourceFact(
        field_key=field_key, value=value, context=FactContext.GENERAL_SUPPLIER,
        source_reference=source_reference,
        supporting_evidence_ids=evidence_ids,
        provenance_evidence_ids=other_evidence_ids,
        component_attributions=(
            FactComponentAttribution("unit_price", source_reference),
            FactComponentAttribution("currency", source_reference),
        ) if isinstance(value, PriceValue) and value.currency is not None else (),
        has_same_context_conflict=has_same_context_conflict,
    ),)
