"""Public Brief editing contracts."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

from sourcepilot.ai.clarification import ClarificationQuestion
from sourcepilot.briefs.domain import (
    MAX_BRIEF_TEXT_LENGTH,
    RequirementImportance,
    RequirementKind,
    validate_brief_quantity,
    validate_delivery_target,
    validate_requirement_expected_value,
    validate_target_unit_price,
)


class EditRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    kind: RequirementKind
    importance: RequirementImportance | None
    expected_value: dict[str, object]
    notes: str | None = None

    @model_validator(mode="after")
    def validate_value(self) -> EditRequirement:
        self.expected_value = validate_requirement_expected_value(self.kind, self.expected_value)
        return self


class EditBriefRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_name: str | None
    category: str | None
    quantity: StrictInt | None
    destination: str | None
    delivery_target: dict[str, object] | None
    target_unit_price: str | None
    requirements: list[EditRequirement]
    expected_brief_revision: StrictInt | None = Field(default=None, ge=0)

    @field_validator("product_name", "category", "destination")
    @classmethod
    def validate_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("use null for an unknown value")
        if len(value) > MAX_BRIEF_TEXT_LENGTH:
            raise ValueError(f"must be at most {MAX_BRIEF_TEXT_LENGTH} characters")
        return value

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value: int | None) -> int | None:
        return None if value is None else validate_brief_quantity(value)

    @field_validator("delivery_target")
    @classmethod
    def validate_delivery(cls, value: dict[str, object] | None) -> dict[str, object] | None:
        return None if value is None else validate_delivery_target(value)

    @field_validator("target_unit_price")
    @classmethod
    def validate_price(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            amount = validate_target_unit_price(Decimal(value))
        except (InvalidOperation, ValueError) as error:
            raise ValueError("target unit price must be a positive decimal with at most 4 places") from error
        return str(amount)


class RequirementResponse(BaseModel):
    id: UUID
    kind: RequirementKind
    importance: RequirementImportance | None
    expected_value: dict[str, object]
    notes: str | None


class MissingFieldResponse(BaseModel):
    field_key: str
    reason: str


class BriefResponse(BaseModel):
    product_name: str | None
    category: str | None
    quantity: int | None
    destination: str | None
    delivery_target: dict[str, object] | None
    target_unit_price: str | None
    requirements: list[RequirementResponse]
    status: str
    missing_fields: list[MissingFieldResponse]
    brief_revision: int
    can_analyze: bool


class AnalyzeBriefResponse(BriefResponse):
    ambiguities: list[str] = Field(default_factory=list)


class ClarificationResponse(BaseModel):
    brief_revision: int
    questions: list[ClarificationQuestion]
