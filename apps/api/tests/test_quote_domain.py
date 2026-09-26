"""Quote provenance and confirmed-value rules."""

import pytest

from sourcepilot.quotes.domain import (
    QuoteStatus,
    QuoteValueOrigin,
    authoritative_current_values,
    validate_quote_value_provenance,
)


def test_extracted_value_starts_as_current_and_correction_preserves_source() -> None:
    extracted = {"amount": "4.22", "currency": "USD"}
    corrected = {"amount": "4.50", "currency": "USD"}
    assert validate_quote_value_provenance(
        field_key="unit_price", current_value=extracted,
        current_origin=QuoteValueOrigin.AI_EXTRACTED, ai_extracted_value=extracted,
    ) == QuoteValueOrigin.AI_EXTRACTED
    assert validate_quote_value_provenance(
        field_key="unit_price", current_value=corrected,
        current_origin=QuoteValueOrigin.USER_CORRECTED, ai_extracted_value=extracted,
    ) == QuoteValueOrigin.USER_CORRECTED
    assert extracted == {"amount": "4.22", "currency": "USD"}


def test_manual_and_unknown_value_provenance() -> None:
    assert validate_quote_value_provenance(
        field_key="shipping_cost", current_value=None,
        current_origin=QuoteValueOrigin.USER_ENTERED, ai_extracted_value=None,
    ) == QuoteValueOrigin.USER_ENTERED
    assert validate_quote_value_provenance(
        field_key="shipping_cost", current_value=None,
        current_origin=QuoteValueOrigin.AI_EXTRACTED, ai_extracted_value=None,
    ) == QuoteValueOrigin.AI_EXTRACTED
    with pytest.raises(ValueError, match="cannot claim"):
        validate_quote_value_provenance(
            field_key="unit_price", current_value="4.50",
            current_origin=QuoteValueOrigin.USER_ENTERED, ai_extracted_value="4.22",
        )


def test_unchanged_ai_origin_cannot_hide_a_correction() -> None:
    with pytest.raises(ValueError, match="must match"):
        validate_quote_value_provenance(
            field_key="unit_price", current_value="4.50",
            current_origin=QuoteValueOrigin.AI_EXTRACTED, ai_extracted_value="4.22",
        )
    with pytest.raises(ValueError, match="Unsupported"):
        validate_quote_value_provenance(
            field_key="invented_field", current_value="4.50",
            current_origin=QuoteValueOrigin.USER_ENTERED, ai_extracted_value=None,
        )


def test_only_confirmed_current_values_are_authoritative() -> None:
    values = [("unit_price", "4.50"), ("shipping_cost", None)]
    assert authoritative_current_values(QuoteStatus.NEEDS_REVIEW, values) is None
    assert authoritative_current_values(QuoteStatus.PROCESSING, values) is None
    assert authoritative_current_values(QuoteStatus.FAILED, values) is None
    assert authoritative_current_values(QuoteStatus.CONFIRMED, values) == {
        "unit_price": "4.50", "shipping_cost": None,
    }
