"""Public transient supplier discovery contract."""

from uuid import UUID

from pydantic import BaseModel


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
