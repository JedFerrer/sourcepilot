"""Manual quote API contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sourcepilot.quotes.domain import validate_manual_values


class ManualQuoteCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_id: UUID
    values: dict[str, object | None] = Field(default_factory=dict)
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("values")
    @classmethod
    def validate_values(cls, values: dict[str, object | None]) -> dict[str, object | None]:
        return validate_manual_values(values)


class ManualQuoteEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    values: dict[str, object | None] = Field(default_factory=dict)
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("values")
    @classmethod
    def validate_values(cls, values: dict[str, object | None]) -> dict[str, object | None]:
        return validate_manual_values(values)


class QuoteFieldResponse(BaseModel):
    current_value: object | None
    current_origin: str
    ai_extracted_value: object | None


class QuoteProcessingResponse(BaseModel):
    status: str
    attempts: int
    started_at: datetime | None
    completed_at: datetime | None
    failure: str | None


class QuoteResponse(BaseModel):
    id: UUID
    project_id: UUID
    supplier_id: UUID
    entry_type: str
    status: str
    revision: int
    confirmed_at: datetime | None
    notes: str | None
    values: dict[str, QuoteFieldResponse]
    processing: QuoteProcessingResponse | None = None
