"""Explicit, deterministic requirement evaluation for confirmed comparison facts."""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from uuid import UUID

from sourcepilot.briefs.domain import RequirementKind
from sourcepilot.comparison.source_resolution import (
    FactContext,
    PriceValue,
    SourceFact,
    SourceResolution,
    SourceResolutionStatus,
)
from sourcepilot.suppliers.evaluation import (
    EvaluationRequirement,
    EvaluationStatus,
    SupplierEvaluationFacts,
    evaluate_supplier,
)


class ComparisonWarningCode(StrEnum):
    QUANTITY_MISMATCH = "QUANTITY_MISMATCH"
    MIXED_QUOTE_CURRENCIES = "MIXED_QUOTE_CURRENCIES"
    TARGET_CURRENCY_MISSING = "TARGET_CURRENCY_MISSING"
    PRICE_CURRENCY_MISSING = "PRICE_CURRENCY_MISSING"
    TARGET_CURRENCY_MISMATCH = "TARGET_CURRENCY_MISMATCH"
    SELECTED_PRICE_CURRENCY_MISMATCH = "SELECTED_PRICE_CURRENCY_MISMATCH"


@dataclass(frozen=True)
class ComparisonWarning:
    code: ComparisonWarningCode
    requirement_id: UUID | None = None


@dataclass(frozen=True)
class ComparisonRequirementResult:
    requirement_id: UUID | None
    kind: RequirementKind
    status: EvaluationStatus
    selected_fact: SourceFact | None = None
    evidence_ids: tuple[UUID, ...] = ()
    conflicting_facts: tuple[SourceFact, ...] = ()


@dataclass(frozen=True)
class ComparisonEvaluation:
    results: tuple[ComparisonRequirementResult, ...]
    informational_requirement_ids: tuple[UUID, ...]
    warnings: tuple[ComparisonWarning, ...]


_DAY_SUFFIX = r"\s*(?:after sample approval)?\s*$"
_DAY_COUNT = re.compile(r"^\s*(\d+)\s*days?" + _DAY_SUFFIX, re.IGNORECASE)
_DAY_RANGE = re.compile(r"^\s*(\d+)\s*[-–—]\s*(\d+)\s*days?" + _DAY_SUFFIX, re.IGNORECASE)
_SUPPLIER_KINDS = {
    RequirementKind.MATERIAL,
    RequirementKind.CERTIFICATION,
    RequirementKind.CAPABILITY,
}


def evaluate_comparison(
    requirements: Sequence[EvaluationRequirement],
    *,
    requested_quantity: int,
    supplier: SupplierEvaluationFacts,
    commercial_facts: Mapping[str, SourceResolution],
    quoted_quantity: SourceResolution,
    delivery_commitment: SourceResolution,
    quote_currency: str | None,
    quote_currencies: Sequence[str | None],
) -> ComparisonEvaluation:
    """Evaluate one supplier against approved requirements and quote-set compatibility."""
    if requested_quantity <= 0:
        raise ValueError("requested_quantity must be positive")
    results: list[ComparisonRequirementResult] = []
    informational: list[UUID] = []
    warnings: list[ComparisonWarning] = []
    known_currencies = {currency for currency in quote_currencies if currency is not None}
    mixed_currencies = len(known_currencies) > 1
    if mixed_currencies:
        warnings.append(ComparisonWarning(ComparisonWarningCode.MIXED_QUOTE_CURRENCIES))
    quantity_status, _ = _quantity_result(requested_quantity, quoted_quantity)
    if quantity_status is EvaluationStatus.DOES_NOT_MEET:
        warnings.append(ComparisonWarning(ComparisonWarningCode.QUANTITY_MISMATCH))

    supplier_requirements = [item for item in requirements if item.kind in _SUPPLIER_KINDS]
    supplier_result = evaluate_supplier(
        supplier_requirements, requested_quantity=requested_quantity, supplier=supplier
    )
    supplier_by_id = {
        result.requirement_id: result
        for result in supplier_result.results if result.requirement_id is not None
    }
    has_moq = False

    for requirement in requirements:
        kind = requirement.kind
        if kind in _SUPPLIER_KINDS:
            prior = supplier_by_id[requirement.id]
            results.append(ComparisonRequirementResult(
                requirement.id, kind, prior.status, evidence_ids=prior.evidence_ids,
            ))
        elif kind is RequirementKind.MOQ:
            has_moq = True
            expected_quantity = requirement.expected_value["quantity"]
            assert isinstance(expected_quantity, int)
            limit = min(requested_quantity, expected_quantity)
            results.append(_numeric_result(requirement.id, kind, commercial_facts["moq"], limit))
        elif kind is RequirementKind.QUANTITY:
            status, fact = _quantity_result(requested_quantity, quoted_quantity)
            results.append(ComparisonRequirementResult(
                requirement.id, kind, status, fact,
                conflicting_facts=_conflicting_facts(quoted_quantity),
            ))
        elif kind is RequirementKind.UNIT_PRICE:
            result, price_warnings = _price_result(
                requirement, commercial_facts["unit_price"], quantity_status,
                mixed_currencies=mixed_currencies,
                missing_quote_currency=quote_currency is None or any(
                    currency is None for currency in quote_currencies
                ),
                quote_currency=quote_currency,
                quote_currencies=quote_currencies,
            )
            results.append(result)
            warnings.extend(price_warnings)
        elif kind is RequirementKind.PRODUCTION_LEAD_TIME:
            results.append(_lead_time_result(requirement, commercial_facts["production_lead_time"]))
        elif kind is RequirementKind.DELIVERY:
            results.append(_delivery_result(requirement, delivery_commitment))
        else:
            informational.append(requirement.id)

    if not has_moq:
        results.append(_numeric_result(None, RequirementKind.MOQ, commercial_facts["moq"], requested_quantity))
    return ComparisonEvaluation(tuple(results), tuple(informational), tuple(warnings))


def _source_status(resolution: SourceResolution) -> EvaluationStatus | None:
    if resolution.status is SourceResolutionStatus.CONFLICT:
        return EvaluationStatus.CONFLICT
    if resolution.status is SourceResolutionStatus.UNAVAILABLE or resolution.selected is None:
        return EvaluationStatus.UNKNOWN
    return None


def _conflicting_facts(resolution: SourceResolution) -> tuple[SourceFact, ...]:
    if resolution.status is not SourceResolutionStatus.CONFLICT:
        return ()
    return resolution.project_facts or resolution.general_facts


def _quantity_result(expected: int, resolution: SourceResolution) -> tuple[EvaluationStatus, SourceFact | None]:
    unavailable = _source_status(resolution)
    if unavailable is not None:
        return unavailable, None
    fact = resolution.selected
    assert fact is not None
    if type(fact.value) is not int or fact.value <= 0:
        return EvaluationStatus.UNKNOWN, fact
    return (EvaluationStatus.MEETS if fact.value == expected else EvaluationStatus.DOES_NOT_MEET), fact


def _numeric_result(
    requirement_id: UUID | None, kind: RequirementKind, resolution: SourceResolution, limit: int,
) -> ComparisonRequirementResult:
    unavailable = _source_status(resolution)
    if unavailable is not None:
        return ComparisonRequirementResult(
            requirement_id, kind, unavailable,
            conflicting_facts=_conflicting_facts(resolution),
        )
    fact = resolution.selected
    assert fact is not None
    if type(fact.value) is not int or fact.value <= 0:
        return ComparisonRequirementResult(requirement_id, kind, EvaluationStatus.UNKNOWN, fact)
    if (kind is RequirementKind.MOQ and fact.context is FactContext.GENERAL_SUPPLIER
            and not fact.supporting_evidence_ids):
        return ComparisonRequirementResult(requirement_id, kind, EvaluationStatus.UNKNOWN, fact)
    status = EvaluationStatus.MEETS if fact.value <= limit else EvaluationStatus.DOES_NOT_MEET
    return ComparisonRequirementResult(requirement_id, kind, status, fact)


def _price_result(
    requirement: EvaluationRequirement,
    resolution: SourceResolution,
    quantity_status: EvaluationStatus,
    *, mixed_currencies: bool,
    missing_quote_currency: bool,
    quote_currency: str | None,
    quote_currencies: Sequence[str | None],
) -> tuple[ComparisonRequirementResult, tuple[ComparisonWarning, ...]]:
    target_currency = requirement.expected_value.get("currency")
    price = resolution.selected.value if resolution.selected is not None else None
    warnings: list[ComparisonWarning] = []
    if not isinstance(target_currency, str):
        warnings.append(ComparisonWarning(ComparisonWarningCode.TARGET_CURRENCY_MISSING, requirement.id))
    if (isinstance(price, PriceValue) and price.currency is None) or missing_quote_currency:
        warnings.append(ComparisonWarning(ComparisonWarningCode.PRICE_CURRENCY_MISSING, requirement.id))
    if (isinstance(target_currency, str) and quote_currency is not None
            and quote_currency != target_currency):
        warnings.append(ComparisonWarning(ComparisonWarningCode.TARGET_CURRENCY_MISMATCH, requirement.id))
    if (isinstance(target_currency, str) and isinstance(price, PriceValue)
            and price.currency is not None and price.currency != target_currency):
        warnings.append(ComparisonWarning(
            ComparisonWarningCode.SELECTED_PRICE_CURRENCY_MISMATCH, requirement.id,
        ))
    warning_metadata = tuple(warnings)
    unavailable = _source_status(resolution)
    if unavailable is not None:
        return ComparisonRequirementResult(
            requirement.id, requirement.kind, unavailable,
            conflicting_facts=_conflicting_facts(resolution),
        ), warning_metadata
    fact = resolution.selected
    assert fact is not None
    price = fact.value
    if not isinstance(price, PriceValue):
        return ComparisonRequirementResult(requirement.id, requirement.kind, EvaluationStatus.UNKNOWN, fact), warning_metadata
    if (warnings or mixed_currencies or quantity_status is not EvaluationStatus.MEETS
            or any(currency != price.currency for currency in quote_currencies)):
        return ComparisonRequirementResult(requirement.id, requirement.kind, EvaluationStatus.UNKNOWN, fact), warning_metadata
    try:
        amount = Decimal(price.amount)
        target = Decimal(str(requirement.expected_value["amount"]))
    except InvalidOperation:
        return ComparisonRequirementResult(requirement.id, requirement.kind, EvaluationStatus.UNKNOWN, fact), warning_metadata
    if not amount.is_finite() or not target.is_finite():
        return ComparisonRequirementResult(requirement.id, requirement.kind, EvaluationStatus.UNKNOWN, fact), warning_metadata
    status = EvaluationStatus.MEETS if amount <= target else EvaluationStatus.DOES_NOT_MEET
    return ComparisonRequirementResult(requirement.id, requirement.kind, status, fact), warning_metadata


def _lead_time_result(
    requirement: EvaluationRequirement, resolution: SourceResolution,
) -> ComparisonRequirementResult:
    unavailable = _source_status(resolution)
    if unavailable is not None:
        return ComparisonRequirementResult(
            requirement.id, requirement.kind, unavailable,
            conflicting_facts=_conflicting_facts(resolution),
        )
    fact = resolution.selected
    assert fact is not None
    bounds = _day_bounds(fact.value)
    if bounds is None:
        return ComparisonRequirementResult(requirement.id, requirement.kind, EvaluationStatus.UNKNOWN, fact)
    maximum = requirement.expected_value["max_days"]
    assert isinstance(maximum, int)
    if bounds[1] <= maximum:
        status = EvaluationStatus.MEETS
    elif bounds[0] > maximum:
        status = EvaluationStatus.DOES_NOT_MEET
    else:
        status = EvaluationStatus.UNKNOWN
    return ComparisonRequirementResult(requirement.id, requirement.kind, status, fact)


def _day_bounds(value: object) -> tuple[int, int] | None:
    if type(value) is int and value > 0:
        return value, value
    if not isinstance(value, str):
        return None
    count = _DAY_COUNT.fullmatch(value)
    if count is not None:
        days = int(count.group(1))
        return (days, days) if days > 0 else None
    day_range = _DAY_RANGE.fullmatch(value)
    if day_range is None:
        return None
    low, high = int(day_range.group(1)), int(day_range.group(2))
    return (low, high) if 0 < low <= high else None


def _delivery_result(
    requirement: EvaluationRequirement, resolution: SourceResolution,
) -> ComparisonRequirementResult:
    unavailable = _source_status(resolution)
    if unavailable is not None:
        return ComparisonRequirementResult(
            requirement.id, requirement.kind, unavailable,
            conflicting_facts=_conflicting_facts(resolution),
        )
    fact = resolution.selected
    assert fact is not None
    try:
        commitment = date.fromisoformat(fact.value) if isinstance(fact.value, str) else fact.value
        if not isinstance(commitment, date):
            return ComparisonRequirementResult(requirement.id, requirement.kind, EvaluationStatus.UNKNOWN, fact)
        target = requirement.expected_value
        if target.get("kind") == "DATE":
            deadline = date.fromisoformat(str(target["date"]))
            status = EvaluationStatus.MEETS if commitment <= deadline else EvaluationStatus.DOES_NOT_MEET
        elif target.get("kind") == "PERIOD" and target.get("end_date") is not None:
            end = date.fromisoformat(str(target["end_date"]))
            start_value = target.get("start_date")
            start = date.fromisoformat(str(start_value)) if start_value is not None else None
            if start is not None and start > end:
                status = EvaluationStatus.UNKNOWN
            elif commitment > end:
                status = EvaluationStatus.DOES_NOT_MEET
            elif start is None or commitment < start:
                status = EvaluationStatus.UNKNOWN
            else:
                status = EvaluationStatus.MEETS
        else:
            status = EvaluationStatus.UNKNOWN
    except ValueError:
        status = EvaluationStatus.UNKNOWN
    return ComparisonRequirementResult(requirement.id, requirement.kind, status, fact)
