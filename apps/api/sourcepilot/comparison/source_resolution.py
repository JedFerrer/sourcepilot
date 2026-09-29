"""Resolve factual source precedence without evaluating requirements."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class FactContext(StrEnum):
    PROJECT_QUOTE = "PROJECT_QUOTE"
    GENERAL_SUPPLIER = "GENERAL_SUPPLIER"


class SourceResolutionStatus(StrEnum):
    SELECTED = "SELECTED"
    UNAVAILABLE = "UNAVAILABLE"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class PriceValue:
    amount: str
    currency: str | None


@dataclass(frozen=True)
class FactComponentAttribution:
    field_key: str
    source_reference: str
    supporting_evidence_ids: tuple[UUID, ...] = ()
    provenance_evidence_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True)
class SourceFact:
    field_key: str
    value: object
    context: FactContext
    source_reference: str
    related_source_references: tuple[str, ...] = ()
    supporting_evidence_ids: tuple[UUID, ...] = ()
    provenance_evidence_ids: tuple[UUID, ...] = ()
    component_attributions: tuple[FactComponentAttribution, ...] = ()
    has_same_context_conflict: bool = False


@dataclass(frozen=True)
class SourceResolution:
    status: SourceResolutionStatus
    selected: SourceFact | None
    project_facts: tuple[SourceFact, ...]
    general_facts: tuple[SourceFact, ...]


def resolve_sources(
    field_key: str,
    *,
    project_facts: Sequence[SourceFact] = (),
    general_facts: Sequence[SourceFact] = (),
) -> SourceResolution:
    """Select the highest available context; conflicts apply only within that context."""
    project = tuple(fact for fact in project_facts
                    if fact.value is not None or fact.has_same_context_conflict)
    general = tuple(fact for fact in general_facts
                    if fact.value is not None or fact.has_same_context_conflict)
    for fact in project:
        if fact.field_key != field_key or fact.context is not FactContext.PROJECT_QUOTE:
            raise ValueError("Project fact has the wrong field or context.")
    for fact in general:
        if fact.field_key != field_key or fact.context is not FactContext.GENERAL_SUPPLIER:
            raise ValueError("General fact has the wrong field or context.")

    authoritative = project or general
    if not authoritative:
        return SourceResolution(SourceResolutionStatus.UNAVAILABLE, None, project, general)
    if any(fact.has_same_context_conflict for fact in authoritative):
        return SourceResolution(SourceResolutionStatus.CONFLICT, None, project, general)
    if any(not _same_value(fact.value, authoritative[0].value)
           for fact in authoritative[1:]):
        return SourceResolution(SourceResolutionStatus.CONFLICT, None, project, general)
    return SourceResolution(SourceResolutionStatus.SELECTED, authoritative[0], project, general)


def _same_value(left: object, right: object) -> bool:
    if isinstance(left, PriceValue) and isinstance(right, PriceValue):
        return (Decimal(left.amount) == Decimal(right.amount)
                and left.currency == right.currency)
    if isinstance(left, str) and isinstance(right, str):
        return left.strip() == right.strip()
    return left == right
