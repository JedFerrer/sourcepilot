"""Structured advice contracts and deterministic reference validation; no model calls."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from sourcepilot.comparison.validation import ComparisonRejection, RejectionCode


class QuoteFieldReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quote_id: UUID
    field_key: str = Field(min_length=1)


class AnalysisPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    supplier_ids: list[UUID]
    requirement_ids: list[UUID]
    quote_fields: list[QuoteFieldReference]
    evidence_ids: list[UUID]


class SuggestedSupplierResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_id: UUID | None
    supporting_reasons: list[AnalysisPoint]
    tradeoffs: list[AnalysisPoint]
    uncertainties: list[AnalysisPoint]
    evidence_ids: list[UUID]


def validate_suggestion(
    suggestion: SuggestedSupplierResult, payload: dict[str, Any],
) -> None:
    """Validate scope and structured disclosure; narrative quality belongs to evals."""
    suppliers = {UUID(item["supplier_id"]): item for item in payload["suppliers"]}
    requirements = {UUID(item["id"]): item for item in payload["brief"]["requirements"]}
    quote_owners = {UUID(item["quote_id"]): supplier_id
                    for supplier_id, item in suppliers.items()}
    fields = {(UUID(item["quote_id"]), field["field_key"])
              for item in suppliers.values()
              for field in (*item["quote_fields"], *item["completeness"])}
    evidence_owners = {
        UUID(evidence["id"]): supplier_id
        for supplier_id, item in suppliers.items()
        for evidence in [*item["supplier_facts"]["evidence"],
                         *(e for field in item["quote_fields"] for e in field["evidence"])]
    }
    states = {(supplier_id, UUID(result["requirement_id"])): result["status"]
              for supplier_id, item in suppliers.items()
              for result in item["evaluation"]["results"]
              if result["requirement_id"] is not None}
    if suggestion.supplier_id is not None:
        if suggestion.supplier_id not in suppliers:
            raise ComparisonRejection(RejectionCode.SUPPLIER_REFERENCE, "Suggested supplier is outside the comparison.")
        if not suggestion.supporting_reasons:
            raise ComparisonRejection(RejectionCode.SUGGESTION_REASONS, "A suggestion requires supporting reasons.")
    elif not suggestion.uncertainties:
        raise ComparisonRejection(RejectionCode.NULL_EXPLANATION, "No suggestion requires an explanation.")
    points = suggestion.supporting_reasons + suggestion.tradeoffs + suggestion.uncertainties
    cited: set[UUID] = set()
    for point in points:
        if not point.text.strip() or not point.supplier_ids or not set(point.supplier_ids) <= suppliers.keys():
            raise ComparisonRejection(RejectionCode.SUPPLIER_REFERENCE, "Suggestion point references an unpermitted supplier or empty text.")
        if not set(point.requirement_ids) <= requirements.keys():
            raise ComparisonRejection(RejectionCode.REQUIREMENT_REFERENCE, "Suggestion references an unknown requirement.")
        if any((supplier_id, requirement_id) not in states
               for supplier_id in point.supplier_ids for requirement_id in point.requirement_ids):
            raise ComparisonRejection(RejectionCode.REQUIREMENT_REFERENCE, "Requirement is outside a referenced supplier.")
        if not {(ref.quote_id, ref.field_key) for ref in point.quote_fields} <= fields:
            raise ComparisonRejection(RejectionCode.QUOTE_REFERENCE, "Suggestion references an unknown quote field.")
        if any(quote_owners[ref.quote_id] not in point.supplier_ids for ref in point.quote_fields):
            raise ComparisonRejection(RejectionCode.QUOTE_OWNER_MISMATCH, "Quote field belongs to a different supplier.")
        if any(evidence_owners.get(evidence_id) not in point.supplier_ids
               for evidence_id in point.evidence_ids):
            raise ComparisonRejection(RejectionCode.EVIDENCE_OWNER_MISMATCH, "Suggestion references unknown or misowned evidence.")
        cited.update(point.evidence_ids)
    if not set(suggestion.evidence_ids) <= evidence_owners.keys():
        raise ComparisonRejection(RejectionCode.UNKNOWN_EVIDENCE, "Suggestion references unknown evidence.")
    if not cited <= set(suggestion.evidence_ids):
        raise ComparisonRejection(RejectionCode.SUGGESTION_EVIDENCE, "Suggestion evidence list omits point citations.")
    selected = suggestion.supplier_id
    if selected is None:
        return
    # Supporting reasons cannot structurally claim a known required failure or
    # unresolved required finding as an advantage of the selected supplier.
    required = {requirement_id: state for (supplier_id, requirement_id), state in states.items()
                if supplier_id == selected and requirements[requirement_id]["importance"] == "REQUIRED"}
    for point in suggestion.supporting_reasons:
        if selected not in point.supplier_ids:
            raise ComparisonRejection(RejectionCode.SUGGESTION_REASONS, "Supporting reason must reference the suggested supplier.")
        if any(required.get(requirement_id) in {"DOES_NOT_MEET", "UNKNOWN", "CONFLICT"}
               for requirement_id in point.requirement_ids):
            raise ComparisonRejection(RejectionCode.SUGGESTION_CONTRADICTION, "Supporting reason contradicts a required finding.")
    for section, expected in ((suggestion.tradeoffs, {"DOES_NOT_MEET"}),
                              (suggestion.uncertainties, {"UNKNOWN", "CONFLICT"})):
        covered = {requirement_id for point in section if selected in point.supplier_ids
                   for requirement_id in point.requirement_ids}
        if not {key for key, state in required.items() if state in expected} <= covered:
            raise ComparisonRejection(RejectionCode.SUGGESTION_COVERAGE, "Suggestion omits a required failure or uncertainty.")
