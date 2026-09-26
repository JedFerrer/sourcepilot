"""Deterministic quote provenance and authority rules."""

from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation
from enum import StrEnum


class QuoteEntryType(StrEnum):
    MANUAL = "MANUAL"
    PDF = "PDF"


class QuoteStatus(StrEnum):
    PROCESSING = "PROCESSING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class QuoteValueOrigin(StrEnum):
    AI_EXTRACTED = "AI_EXTRACTED"
    USER_CORRECTED = "USER_CORRECTED"
    USER_ENTERED = "USER_ENTERED"


QUOTE_FIELD_KEYS = frozenset(
    {
        "quoted_quantity", "unit_price", "currency", "moq", "sample_cost",
        "tooling_cost", "packaging_cost", "shipping_cost", "sample_lead_time",
        "production_lead_time", "shipping_time", "total_lead_time",
        "payment_terms", "incoterm", "quote_validity", "warranty",
        "certifications", "compliance_notes", "exclusions", "special_conditions",
        "supplier_notes",
    }
)

QUOTE_INTEGER_FIELDS = frozenset({"quoted_quantity", "moq"})
QUOTE_MONEY_FIELDS = frozenset({
    "unit_price", "sample_cost", "tooling_cost", "packaging_cost", "shipping_cost",
})


def validate_manual_values(values: Mapping[str, object | None]) -> dict[str, object | None]:
    """Normalize boundary values for a manually entered quote."""
    normalized: dict[str, object | None] = {}
    for key, value in values.items():
        if key not in QUOTE_FIELD_KEYS:
            raise ValueError(f"Unsupported quote field: {key!r}")
        if value is None:
            normalized[key] = None
        elif key in QUOTE_INTEGER_FIELDS:
            if type(value) is not int or value <= 0:
                raise ValueError(f"{key} must be a positive whole number")
            normalized[key] = value
        elif key in QUOTE_MONEY_FIELDS:
            if not isinstance(value, str):
                raise ValueError(f"{key} must be a decimal string")
            try:
                amount = Decimal(value)
            except InvalidOperation as error:
                raise ValueError(f"{key} must be a decimal string") from error
            if not amount.is_finite() or amount < 0 or (key == "unit_price" and amount == 0):
                raise ValueError(f"{key} must be a valid nonnegative amount")
            exponent = amount.as_tuple().exponent
            if isinstance(exponent, int) and exponent < -4:
                raise ValueError(f"{key} must have at most four decimal places")
            normalized[key] = str(amount)
        elif key == "currency":
            if not isinstance(value, str) or len(value.strip()) != 3 or not value.strip().isalpha():
                raise ValueError("currency must be a three-letter code")
            normalized[key] = value.strip().upper()
        else:
            if not isinstance(value, str) or not value.strip() or len(value.strip()) > 10000:
                raise ValueError(f"{key} must be nonempty text of at most 10000 characters")
            normalized[key] = value.strip()
    return normalized


def validate_quote_value_provenance(
    *, field_key: str, current_value: object | None,
    current_origin: QuoteValueOrigin | str, ai_extracted_value: object | None,
) -> QuoteValueOrigin:
    """Validate the origin without collapsing extracted and current values."""
    if field_key not in QUOTE_FIELD_KEYS:
        raise ValueError(f"Unsupported quote field: {field_key!r}")
    origin = QuoteValueOrigin(current_origin)
    if origin == QuoteValueOrigin.USER_ENTERED and ai_extracted_value is not None:
        raise ValueError("User-entered values cannot claim an AI-extracted value.")
    if origin == QuoteValueOrigin.AI_EXTRACTED and current_value != ai_extracted_value:
        raise ValueError("An unchanged AI-extracted current value must match the extraction.")
    return origin


def authoritative_current_values(
    status: QuoteStatus | str, values: Iterable[tuple[str, object | None]]
) -> dict[str, object | None] | None:
    """Return confirmed current facts, or no authoritative facts for a draft."""
    if QuoteStatus(status) != QuoteStatus.CONFIRMED:
        return None
    return dict(values)
