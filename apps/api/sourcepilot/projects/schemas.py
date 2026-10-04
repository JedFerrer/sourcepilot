from datetime import datetime
from typing import Literal
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


WorkflowStage = Literal["BRIEF", "SUPPLIERS", "QUOTES", "COMPARISON", "DECISION"]
WorkflowAction = Literal[
    "ANALYZE_BRIEF", "COMPLETE_BRIEF", "APPROVE_BRIEF", "DISCOVER_SUPPLIERS",
    "REFRESH_SUPPLIERS", "REVIEW_SHORTLIST", "APPROVE_SHORTLIST", "COMPLETE_QUOTES",
    "GENERATE_COMPARISON", "REGENERATE_COMPARISON", "RECORD_PREFERENCE", "MANAGE_PREFERENCE",
]
WorkflowReason = Literal[
    "BRIEF_ANALYSIS_AVAILABLE", "BRIEF_INCOMPLETE", "BRIEF_APPROVAL_REQUIRED",
    "SUPPLIERS_NOT_DISCOVERED", "SUPPLIER_EVALUATIONS_STALE", "SHORTLIST_EMPTY",
    "SHORTLIST_OVER_LIMIT", "SHORTLIST_APPROVAL_REQUIRED", "INSUFFICIENT_CONFIRMED_QUOTES",
    "COMPARISON_NOT_GENERATED", "COMPARISON_STALE", "PREFERENCE_NOT_RECORDED",
    "PREFERENCE_RECORDED",
]


class WorkflowNextAction(BaseModel):
    code: WorkflowAction
    reason_code: WorkflowReason
    target_stage: WorkflowStage


class WorkflowSummary(BaseModel):
    current_stage: WorkflowStage
    next_action: WorkflowNextAction
    shortlist_count: int
    confirmed_quote_count: int
    comparison_ready: bool
    comparison_present: bool
    comparison_stale: bool
    suppliers_stale: bool
    stage_prerequisites: dict[WorkflowStage, WorkflowReason | None]


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    original_request: str
    stage: str
    workflow: WorkflowSummary
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
