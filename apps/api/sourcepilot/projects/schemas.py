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
    created_at: datetime
    updated_at: datetime
