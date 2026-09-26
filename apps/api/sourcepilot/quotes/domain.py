"""Deterministic quote provenance and authority rules."""

from collections.abc import Iterable
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
