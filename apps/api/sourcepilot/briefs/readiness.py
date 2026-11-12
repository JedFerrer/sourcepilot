"""Deterministic readiness rules for an unapproved sourcing brief."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sourcepilot.briefs.domain import (
    BriefStatus,
    CapabilityKey,
    RequirementKind,
    validate_delivery_target,
    validate_requirement_expected_value,
)

ReadinessFieldKey = Literal[
    "product_name",
    "category",
    "quantity",
    "destination",
    "delivery_target",
    "requirement.material",
    "requirement.custom_branding",
]

COSMETIC_BAG_CATEGORIES = frozenset(
    {
        "cosmetic bag",
        "cosmetic bags",
        "cosmetic travel bag",
        "cosmetic travel bags",
        "travel bags",  # Explicit alias for the current demo category only.
    }
)


def is_cosmetic_bag_category(category: str | None) -> bool:
    """Recognize only the established exact labels, without taxonomy inference."""
    return category is not None and category.strip().casefold() in COSMETIC_BAG_CATEGORIES


@dataclass(frozen=True)
class ReadinessRequirement:
    kind: RequirementKind | str
    expected_value: object


@dataclass(frozen=True)
class MissingReadinessField:
    field_key: ReadinessFieldKey
    reason: str


@dataclass(frozen=True)
class BriefReadinessResult:
    status: BriefStatus
    missing_fields: tuple[MissingReadinessField, ...]


def evaluate_brief_readiness(
    *,
    product_name: str | None,
    category: str | None,
    quantity: int | None,
    destination: str | None,
    delivery_target: object,
    requirements: tuple[ReadinessRequirement, ...],
) -> BriefReadinessResult:
    """Compute readiness from facts without persistence, AI, or importance rules."""
    missing: list[MissingReadinessField] = []

    if not _has_text(product_name):
        missing.append(MissingReadinessField("product_name", "Name the product to source."))
    if not _has_text(category):
        missing.append(MissingReadinessField("category", "Confirm the product category."))
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        missing.append(MissingReadinessField("quantity", "Enter a positive requested quantity."))
    if not _has_text(destination):
        missing.append(MissingReadinessField("destination", "Enter the delivery destination."))
    if not _has_delivery_target(delivery_target):
        missing.append(MissingReadinessField("delivery_target", "Enter a valid delivery target."))

    if is_cosmetic_bag_category(category):
        if not any(_has_material(requirement) for requirement in requirements):
            missing.append(
                MissingReadinessField(
                    "requirement.material", "Specify the material for the demo product."
                )
            )
        if not any(_has_custom_branding(requirement) for requirement in requirements):
            missing.append(
                MissingReadinessField(
                    "requirement.custom_branding",
                    "State whether custom branding is required for the demo product.",
                )
            )

    status = BriefStatus.IN_PROGRESS if missing else BriefStatus.READY_FOR_REVIEW
    return BriefReadinessResult(status=status, missing_fields=tuple(missing))


def _has_text(value: str | None) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_delivery_target(value: object) -> bool:
    if value is None:
        return False
    try:
        validate_delivery_target(value)
    except (ValueError, TypeError):
        return False
    return True


def _has_material(requirement: ReadinessRequirement) -> bool:
    if requirement.kind != RequirementKind.MATERIAL:
        return False
    try:
        validate_requirement_expected_value(RequirementKind.MATERIAL, requirement.expected_value)
    except (ValueError, TypeError):
        return False
    return True


def _has_custom_branding(requirement: ReadinessRequirement) -> bool:
    if requirement.kind != RequirementKind.CAPABILITY:
        return False
    try:
        value = validate_requirement_expected_value(
            RequirementKind.CAPABILITY, requirement.expected_value
        )
    except (ValueError, TypeError):
        return False
    return value["capability_key"] == CapabilityKey.CUSTOM_BRANDING
