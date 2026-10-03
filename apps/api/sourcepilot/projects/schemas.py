from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateProjectRequest(BaseModel):
    name: str = Field(max_length=255)
    original_request: str

    @field_validator("name", "original_request", mode="before")
    @classmethod
    def trim_required_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        trimmed_value = value.strip()
        if not trimmed_value:
            raise ValueError("must not be blank")
        return trimmed_value


class RenameProjectRequest(BaseModel):
    name: str = Field(max_length=255)

    @field_validator("name", mode="before")
    @classmethod
    def trim_required_name(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        trimmed_value = value.strip()
        if not trimmed_value:
            raise ValueError("must not be blank")
        return trimmed_value


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    original_request: str
    stage: str
    preferred_supplier_id: UUID | None
    preferred_supplier_name: str | None
    decision_notes: str | None
    created_at: datetime
    updated_at: datetime


class PreferredSupplierRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_id: UUID | None
    decision_notes: str | None = Field(default=None, max_length=10000)

    @field_validator("decision_notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return (value.strip() or None) if value is not None else None
