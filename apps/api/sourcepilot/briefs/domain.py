from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum


class BriefStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"


class RequirementImportance(StrEnum):
    REQUIRED = "REQUIRED"
    PREFERRED = "PREFERRED"
    INFORMATIONAL = "INFORMATIONAL"


class RequirementKind(StrEnum):
    MATERIAL = "MATERIAL"
    CERTIFICATION = "CERTIFICATION"
    MOQ = "MOQ"
    QUANTITY = "QUANTITY"
    UNIT_PRICE = "UNIT_PRICE"
    PRODUCTION_LEAD_TIME = "PRODUCTION_LEAD_TIME"
    DELIVERY = "DELIVERY"
    CAPABILITY = "CAPABILITY"
    INFORMATIONAL = "INFORMATIONAL"


class CapabilityKey(StrEnum):
    PRODUCT_CATEGORY = "PRODUCT_CATEGORY"
    CUSTOM_BRANDING = "CUSTOM_BRANDING"
    BRANDING_METHOD = "BRANDING_METHOD"
    PRODUCT_FEATURE = "PRODUCT_FEATURE"
    MANUFACTURING_CAPABILITY = "MANUFACTURING_CAPABILITY"


class InformationalSubject(StrEnum):
    DIMENSIONS = "DIMENSIONS"
    SIZE_OR_CAPACITY = "SIZE_OR_CAPACITY"
    COLOR = "COLOR"
    PACKAGING = "PACKAGING"
    LABELING = "LABELING"
    PRODUCT_DESCRIPTION = "PRODUCT_DESCRIPTION"
    BRANDING_NOTES = "BRANDING_NOTES"
    OTHER_CONTEXT = "OTHER_CONTEXT"


_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
_BOOLEAN_CAPABILITY_KEYS = {CapabilityKey.CUSTOM_BRANDING}


def validate_delivery_target(value: object) -> dict[str, object]:
    """Validate and normalize one of the two persisted delivery target shapes."""
    payload = _require_mapping(value, "delivery target")
    kind = payload.get("kind")

    if kind == "DATE":
        _require_exact_keys(payload, {"kind", "date"}, "delivery date")
        return {"kind": "DATE", "date": _require_iso_date(payload["date"], "date")}

    if kind == "PERIOD":
        _require_exact_keys(
            payload,
            {"kind", "label", "start_date", "end_date"},
            "delivery period",
        )
        return {
            "kind": "PERIOD",
            "label": _require_text(payload["label"], "label"),
            "start_date": _require_optional_iso_date(payload["start_date"], "start_date"),
            "end_date": _require_optional_iso_date(payload["end_date"], "end_date"),
        }

    raise ValueError("delivery target kind must be DATE or PERIOD")


def validate_requirement_expected_value(
    kind: RequirementKind | str, value: object
) -> dict[str, object]:
    """Validate the fixed JSON shape associated with one explicit requirement kind."""
    resolved_kind = RequirementKind(kind)

    if resolved_kind in {RequirementKind.MATERIAL, RequirementKind.CERTIFICATION}:
        payload = _require_mapping(value, "requirement value")
        _require_exact_keys(payload, {"value"}, resolved_kind.value)
        return {"value": _normalize_comparison_text(payload["value"], "value")}

    if resolved_kind in {RequirementKind.MOQ, RequirementKind.QUANTITY}:
        payload = _require_mapping(value, "requirement value")
        _require_exact_keys(payload, {"quantity"}, resolved_kind.value)
        return {"quantity": _require_positive_integer(payload["quantity"], "quantity")}

    if resolved_kind is RequirementKind.UNIT_PRICE:
        payload = _require_mapping(value, "requirement value")
        expected_keys = {"amount", "currency"}
        if set(payload) not in ({"amount"}, expected_keys):
            raise ValueError("UNIT_PRICE must contain amount and optional currency only")
        result: dict[str, object] = {
            "amount": _require_positive_decimal_string(payload["amount"], "amount")
        }
        if "currency" in payload:
            result["currency"] = _require_iso_currency(payload["currency"])
        return result

    if resolved_kind is RequirementKind.PRODUCTION_LEAD_TIME:
        payload = _require_mapping(value, "requirement value")
        _require_exact_keys(payload, {"max_days"}, "PRODUCTION_LEAD_TIME")
        return {"max_days": _require_positive_integer(payload["max_days"], "max_days")}

    if resolved_kind is RequirementKind.DELIVERY:
        return validate_delivery_target(value)

    if resolved_kind is RequirementKind.CAPABILITY:
        payload = _require_mapping(value, "requirement value")
        _require_exact_keys(payload, {"capability_key", "value"}, "CAPABILITY")
        capability_key = CapabilityKey(payload["capability_key"])
        capability_value = payload["value"]
        if capability_key in _BOOLEAN_CAPABILITY_KEYS:
            if not isinstance(capability_value, bool):
                raise ValueError(f"{capability_key.value} value must be a boolean")
            normalized_value: bool | str = capability_value
        else:
            normalized_value = _normalize_comparison_text(capability_value, "value")
        return {"capability_key": capability_key.value, "value": normalized_value}

    payload = _require_mapping(value, "requirement value")
    _require_exact_keys(payload, {"subject", "text"}, "INFORMATIONAL")
    subject = InformationalSubject(payload["subject"])
    return {"subject": subject.value, "text": _require_text(payload["text"], "text")}


def validate_target_unit_price(value: object) -> Decimal:
    """Require a Decimal that fits Numeric(12,4) without rounding."""
    if not isinstance(value, Decimal):
        raise ValueError(  # noqa: TRY004 - boundary validation reports one stable value error.
            "target unit price must be a Decimal, not a floating-point value"
        )
    if not value.is_finite() or value <= 0:
        raise ValueError("target unit price must be a positive finite Decimal")
    exponent = value.as_tuple().exponent
    if not isinstance(exponent, int) or exponent < -4:
        raise ValueError("target unit price must have no more than 4 fractional digits")
    if value >= Decimal(100000000):
        raise ValueError("target unit price exceeds Numeric(12,4) precision")
    return value


def _require_mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")  # noqa: TRY004 - stable boundary error.
    return value


def _require_exact_keys(payload: dict[str, object], expected: set[str], label: str) -> None:
    if set(payload) != expected:
        raise ValueError(f"{label} must contain exactly: {', '.join(sorted(expected))}")


def _require_text(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text")  # noqa: TRY004 - stable boundary error.
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{label} must not be blank")
    return normalized


def _normalize_comparison_text(value: object, label: str) -> str:
    return _require_text(value, label).casefold()


def _require_positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _require_positive_decimal_string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(  # noqa: TRY004 - stable boundary error.
            f"{label} must be a decimal string"
        )
    try:
        decimal_value = Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"{label} must be a decimal string") from error
    if not decimal_value.is_finite() or decimal_value <= 0:
        raise ValueError(f"{label} must be a positive finite decimal string")
    return value


def _require_iso_currency(value: object) -> str:
    if not isinstance(value, str) or not _ISO_CURRENCY_PATTERN.fullmatch(value):
        raise ValueError("currency must be an uppercase ISO 4217 code")
    return value


def _require_optional_iso_date(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _require_iso_date(value, label)


def _require_iso_date(value: object, label: str) -> str:
    if not isinstance(value, str) or not _ISO_DATE_PATTERN.fullmatch(value):
        raise ValueError(f"{label} must use YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{label} must be a valid calendar date") from error
    return value
