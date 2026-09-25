"""Deterministic, catalog-only supplier candidate selection."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sourcepilot.briefs.domain import RequirementKind

MAX_CANDIDATES = 5
_COSMETIC_BAG_ALIASES = frozenset(
    {"cosmetic bag", "cosmetic bags", "cosmetic travel bag", "cosmetic travel bags", "travel bags"}
)


@dataclass(frozen=True)
class RetrievalRequirement:
    kind: str
    expected_value: dict[str, object]


@dataclass(frozen=True)
class CandidateFacts:
    id: UUID
    name: str
    capabilities: frozenset[tuple[str, str]]
    general_moq: int | None


def normalize_category(category: str) -> str:
    """Map only the demo's established aliases; do not guess other category synonyms."""
    normalized = " ".join(category.split()).casefold()
    return "cosmetic travel bag" if normalized in _COSMETIC_BAG_ALIASES else normalized


def order_candidates(
    candidates: list[CandidateFacts],
    *,
    requirements: list[RetrievalRequirement],
    quantity: int,
) -> list[UUID]:
    """Order category matches without converting retrieval preferences into a fit verdict."""
    wanted_materials: set[str] = set()
    wanted_capabilities: set[tuple[str, str]] = set()
    wanted_certifications: set[str] = set()
    for requirement in requirements:
        value = requirement.expected_value
        if requirement.kind == RequirementKind.MATERIAL:
            material = value.get("value")
            if isinstance(material, str):
                wanted_materials.add(material.casefold())
        elif requirement.kind == RequirementKind.CAPABILITY:
            key = value.get("capability_key")
            selected = value.get("value")
            if isinstance(key, str) and isinstance(selected, (str, bool)):
                wanted_capabilities.add((key, str(selected).casefold()))
        elif requirement.kind == RequirementKind.CERTIFICATION:
            certification = value.get("value")
            if isinstance(certification, str):
                wanted_certifications.add(certification.casefold())

    def sort_key(candidate: CandidateFacts) -> tuple[int, int, int, int, str, str]:
        material_matches = sum(
            (RequirementKind.MATERIAL.value, value) in candidate.capabilities
            for value in wanted_materials
        )
        capability_matches = sum(
            (key, value) in candidate.capabilities for key, value in wanted_capabilities
        )
        certification_matches = sum(
            (RequirementKind.CERTIFICATION.value, value) in candidate.capabilities
            for value in wanted_certifications
        )
        moq_compatible = candidate.general_moq is not None and candidate.general_moq <= quantity
        return (
            -material_matches,
            -capability_matches,
            -certification_matches,
            -int(moq_compatible),
            candidate.name.casefold(),
            str(candidate.id),
        )

    return [candidate.id for candidate in sorted(candidates, key=sort_key)[:MAX_CANDIDATES]]


def candidate_facts(
    supplier_id: UUID,
    name: str,
    general_moq: int | None,
    capabilities: list[tuple[str, str]],
) -> CandidateFacts:
    """Normalize catalog vocabulary before pure ranking."""
    return CandidateFacts(
        id=supplier_id,
        name=name,
        general_moq=general_moq,
        capabilities=frozenset((kind, value.casefold()) for kind, value in capabilities),
    )
