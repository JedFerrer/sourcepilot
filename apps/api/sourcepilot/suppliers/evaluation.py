"""Pure, evidence-aware supplier-stage requirement evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sourcepilot.briefs.domain import CapabilityKey, RequirementKind


class EvaluationStatus(StrEnum):
    MEETS = "MEETS"
    DOES_NOT_MEET = "DOES_NOT_MEET"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class EvaluationRequirement:
    id: UUID
    kind: RequirementKind
    expected_value: dict[str, object]


@dataclass(frozen=True)
class EvaluationEvidence:
    id: UUID
    claim_key: str
    evidence_state: str


@dataclass(frozen=True)
class SupplierEvaluationFacts:
    capabilities: frozenset[tuple[str, str]]
    general_moq: int | None
    evidence: tuple[EvaluationEvidence, ...]


@dataclass(frozen=True)
class RequirementEvaluation:
    requirement_id: UUID | None
    kind: RequirementKind
    status: EvaluationStatus
    evidence_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class SupplierEvaluation:
    results: tuple[RequirementEvaluation, ...]
    informational_requirement_ids: tuple[UUID, ...]


def evaluate_supplier(
    requirements: list[EvaluationRequirement],
    *,
    requested_quantity: int,
    supplier: SupplierEvaluationFacts,
) -> SupplierEvaluation:
    """Evaluate supported requirements; keep other Brief requirements informational."""
    results: list[RequirementEvaluation] = []
    informational: list[UUID] = []
    has_moq_requirement = False

    for requirement in requirements:
        if requirement.kind in {RequirementKind.MATERIAL, RequirementKind.CERTIFICATION}:
            value = str(requirement.expected_value["value"])
            claim_key = _claim_key(requirement.kind, value)
            result = _positive_claim_result(
                supplier,
                claim_key,
                (requirement.kind.value, _normalize(value)),
            )
        elif requirement.kind is RequirementKind.CAPABILITY:
            result = _capability_result(requirement.expected_value, supplier)
        elif requirement.kind is RequirementKind.MOQ:
            has_moq_requirement = True
            acceptable_moq = requirement.expected_value["quantity"]
            assert isinstance(acceptable_moq, int)  # Validated Brief requirement shape.
            limit = min(requested_quantity, acceptable_moq)
            result = _moq_result(limit, supplier)
        else:
            informational.append(requirement.id)
            continue
        results.append(RequirementEvaluation(requirement.id, requirement.kind, *result))

    if not has_moq_requirement:
        results.append(
            RequirementEvaluation(None, RequirementKind.MOQ, *_moq_result(requested_quantity, supplier))
        )
    return SupplierEvaluation(tuple(results), tuple(informational))


def _claim_key(kind: RequirementKind, value: str) -> str:
    normalized = " ".join(value.split()).casefold()
    if kind is RequirementKind.MATERIAL:
        return f"material:{normalized}"
    return f"certification:{normalized}:current"


def _capability_result(
    expected_value: dict[str, object], supplier: SupplierEvaluationFacts
) -> tuple[EvaluationStatus, tuple[UUID, ...]]:
    key = CapabilityKey(str(expected_value["capability_key"]))
    value = expected_value["value"]
    if key is CapabilityKey.PRODUCT_CATEGORY:
        claim_key = f"category:{_normalize(str(value))}"
    elif key is CapabilityKey.CUSTOM_BRANDING:
        claim_key = "capability:custom branding"
    else:
        claim_key = f"capability:{key.value.replace('_', ' ').casefold()}:{_normalize(str(value))}"

    if key is CapabilityKey.CUSTOM_BRANDING and value is False:
        status, evidence_ids = _positive_claim_result(
            supplier, claim_key, (key.value, "true")
        )
        if status is EvaluationStatus.MEETS:
            return EvaluationStatus.DOES_NOT_MEET, evidence_ids
        if status is EvaluationStatus.DOES_NOT_MEET:
            if _has_capability(supplier, key.value, "false"):
                return EvaluationStatus.MEETS, evidence_ids
            return EvaluationStatus.UNKNOWN, evidence_ids
        return status, evidence_ids
    return _positive_claim_result(supplier, claim_key, (key.value, _normalize(str(value))))


def _positive_claim_result(
    supplier: SupplierEvaluationFacts,
    claim_key: str,
    catalog_claim: tuple[str, str],
) -> tuple[EvaluationStatus, tuple[UUID, ...]]:
    status, evidence_ids = _evidence_result(supplier.evidence, claim_key)
    if status is EvaluationStatus.MEETS and not _has_capability(supplier, *catalog_claim):
        return EvaluationStatus.UNKNOWN, evidence_ids
    return status, evidence_ids


def _has_capability(supplier: SupplierEvaluationFacts, kind: str, value: str) -> bool:
    return any(
        actual_kind == kind and _normalize(actual_value) == value
        for actual_kind, actual_value in supplier.capabilities
    )


def _moq_result(
    limit: int, supplier: SupplierEvaluationFacts
) -> tuple[EvaluationStatus, tuple[UUID, ...]]:
    status, evidence_ids = _evidence_result(supplier.evidence, "moq:general")
    if status is EvaluationStatus.CONFLICT:
        return status, evidence_ids
    if status is not EvaluationStatus.MEETS or supplier.general_moq is None:
        return EvaluationStatus.UNKNOWN, evidence_ids
    if supplier.general_moq <= limit:
        return EvaluationStatus.MEETS, evidence_ids
    return EvaluationStatus.DOES_NOT_MEET, evidence_ids


def _evidence_result(
    evidence: tuple[EvaluationEvidence, ...], claim_key: str
) -> tuple[EvaluationStatus, tuple[UUID, ...]]:
    matching = tuple(item for item in evidence if _normalize(item.claim_key) == claim_key)
    evidence_ids = tuple(sorted((item.id for item in matching), key=str))
    supports = any(item.evidence_state == "SUPPORTS" for item in matching)
    contradicts = any(item.evidence_state == "CONTRADICTS" for item in matching)
    if supports and contradicts:
        return EvaluationStatus.CONFLICT, evidence_ids
    if supports:
        return EvaluationStatus.MEETS, evidence_ids
    if contradicts:
        return EvaluationStatus.DOES_NOT_MEET, evidence_ids
    return EvaluationStatus.UNKNOWN, evidence_ids


def _normalize(value: str) -> str:
    return " ".join(value.split()).casefold()
