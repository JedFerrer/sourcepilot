"""Public transient supplier discovery contract."""

from uuid import UUID

from pydantic import BaseModel, Field


class CandidateCapabilityResponse(BaseModel):
    kind: str
    value: str


class SupplierCandidateResponse(BaseModel):
    id: UUID
    name: str
    country: str
    description: str
    capabilities: list[CandidateCapabilityResponse]
    general_moq: int | None
    general_lead_time_days: int | None
    indicative_price_amount: str | None
    indicative_price_currency: str | None


class DiscoverSuppliersResponse(BaseModel):
    brief_revision: int
    suppliers: list[SupplierCandidateResponse]


class SupplierEvidenceResponse(BaseModel):
    id: UUID
    claim_key: str
    source_type: str
    source_label: str
    source_reference: str | None
    evidence_text: str
    evidence_state: str


class RequirementEvaluationResponse(BaseModel):
    requirement_id: UUID
    kind: str
    importance: str | None
    expected_value: dict[str, object]
    status: str
    evidence_ids: list[UUID]


class DerivedContextResponse(BaseModel):
    kind: str
    status: str
    evidence_ids: list[UUID]


class InformationalRequirementResponse(BaseModel):
    requirement_id: UUID
    kind: str
    importance: str | None
    expected_value: dict[str, object]


class ReviewedSupplierResponse(SupplierCandidateResponse):
    shortlisted: bool
    dismissed: bool
    notes: str | None
    evaluated_against_brief_revision: int
    stale: bool
    evaluations: list[RequirementEvaluationResponse]
    derived_context: list[DerivedContextResponse]
    informational_requirements: list[InformationalRequirementResponse]
    evidence: list[SupplierEvidenceResponse]


class SupplierListResponse(BaseModel):
    brief_revision: int
    brief_approved: bool
    suppliers: list[ReviewedSupplierResponse]


class UpdateSupplierReviewRequest(BaseModel):
    shortlisted: bool | None = None
    dismissed: bool | None = None
    notes: str | None = Field(default=None, max_length=10000)
