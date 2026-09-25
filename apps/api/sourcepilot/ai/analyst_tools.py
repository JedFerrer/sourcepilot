"""Read-only, project-scoped supplier tools for the future Sourcing Analyst."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from sourcepilot.persistence.models import (
    DemoSession,
    Project,
    ProjectSupplier,
    Requirement,
    RequirementEvaluationRecord,
    Supplier,
    SupplierCapability,
    SupplierEvidence,
)

DEFAULT_MAX_TOOL_CALLS = 6


class ToolErrorCode(StrEnum):
    NOT_ALLOWED = "NOT_ALLOWED"
    NOT_FOUND = "NOT_FOUND"
    LIMIT_REACHED = "LIMIT_REACHED"


class ToolError(Exception):
    def __init__(self, code: ToolErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class EvaluationAvailability(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    ABSENT = "ABSENT"


@dataclass(frozen=True)
class AnalystToolContext:
    demo_session_id: UUID
    project_id: UUID
    permitted_supplier_ids: frozenset[UUID]
    max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS

    def __post_init__(self) -> None:
        object.__setattr__(self, "permitted_supplier_ids", frozenset(self.permitted_supplier_ids))
        if self.max_tool_calls <= 0:
            raise ValueError("max_tool_calls must be positive")


@dataclass(frozen=True)
class ToolTraceEvent:
    tool_name: str
    supplier_id: UUID
    claim_keys: tuple[str, ...] | None
    outcome: str
    successful_call_count: int


@dataclass
class AnalystToolRuntime:
    context: AnalystToolContext
    successful_call_count: int = field(default=0, init=False)
    _events: list[ToolTraceEvent] = field(default_factory=list, init=False, repr=False)

    @property
    def trace(self) -> tuple[ToolTraceEvent, ...]:
        return tuple(self._events)

    def record(
        self, tool_name: str, supplier_id: UUID, claim_keys: tuple[str, ...] | None,
        outcome: str,
    ) -> None:
        if outcome == "SUCCESS":
            self.successful_call_count += 1
        self._events.append(ToolTraceEvent(
            tool_name=tool_name,
            supplier_id=supplier_id,
            claim_keys=claim_keys,
            outcome=outcome,
            successful_call_count=self.successful_call_count,
        ))

    def check_budget(self) -> None:
        if self.successful_call_count >= self.context.max_tool_calls:
            raise ToolError(ToolErrorCode.LIMIT_REACHED)


class SupplierCapabilityFact(BaseModel):
    kind: str
    value: str


class SupplierRequirementFinding(BaseModel):
    requirement_id: UUID
    kind: str
    importance: str | None
    expected_value: dict[str, object]
    status: str
    evidence_ids: list[UUID]


class SupplierSnapshot(BaseModel):
    supplier_id: UUID
    name: str
    country: str
    description: str
    capabilities: list[SupplierCapabilityFact]
    general_moq: int | None
    general_lead_time_days: int | None
    indicative_price_amount: str | None
    indicative_price_currency: str | None
    evaluation_availability: EvaluationAvailability
    evaluated_against_brief_revision: int
    current_brief_revision: int
    evaluations: list[SupplierRequirementFinding]


class SupplierEvidenceItem(BaseModel):
    id: UUID
    claim_key: str
    source_type: str
    source_label: str
    source_reference: str | None
    evidence_text: str
    evidence_state: str


class SupplierEvidenceResult(BaseModel):
    supplier_id: UUID
    evidence: list[SupplierEvidenceItem]


def _authorized_supplier(
    session: Session, runtime: AnalystToolRuntime, supplier_id: UUID,
) -> tuple[int, int]:
    context = runtime.context
    brief_revision = session.scalar(
        select(Project.brief_revision)
        .join(DemoSession, DemoSession.id == Project.demo_session_id)
        .where(
            Project.id == context.project_id,
            Project.demo_session_id == context.demo_session_id,
            DemoSession.expires_at > datetime.now(UTC),
        )
        .with_for_update(read=True, of=Project)
    )
    if brief_revision is None or supplier_id not in context.permitted_supplier_ids:
        raise ToolError(ToolErrorCode.NOT_ALLOWED)

    if session.scalar(select(Supplier.id).where(Supplier.id == supplier_id)) is None:
        raise ToolError(ToolErrorCode.NOT_FOUND)

    saved_revision = session.scalar(
        select(ProjectSupplier.evaluated_against_brief_revision)
        .where(
            ProjectSupplier.project_id == context.project_id,
            ProjectSupplier.supplier_id == supplier_id,
        )
    )
    if saved_revision is None:
        raise ToolError(ToolErrorCode.NOT_ALLOWED)
    return brief_revision, saved_revision


def get_supplier_snapshot(
    session: Session, runtime: AnalystToolRuntime, supplier_id: UUID,
) -> SupplierSnapshot:
    """Return current candidate facts without exposing stale evaluations."""
    tool_name = "get_supplier_snapshot"
    try:
        runtime.check_budget()
        with session.no_autoflush:
            brief_revision, saved_revision = _authorized_supplier(session, runtime, supplier_id)
            supplier = session.execute(select(
                Supplier.name, Supplier.country, Supplier.description, Supplier.general_moq,
                Supplier.general_lead_time_days, Supplier.indicative_price_amount,
                Supplier.indicative_price_currency,
            ).where(Supplier.id == supplier_id)).one()
            if saved_revision != brief_revision:
                availability = EvaluationAvailability.STALE
                findings: list[SupplierRequirementFinding] = []
            else:
                evaluations = session.execute(select(
                    RequirementEvaluationRecord.requirement_id,
                    RequirementEvaluationRecord.status,
                    RequirementEvaluationRecord.evidence_ids,
                ).where(
                    RequirementEvaluationRecord.project_id == runtime.context.project_id,
                    RequirementEvaluationRecord.supplier_id == supplier_id,
                ).order_by(RequirementEvaluationRecord.requirement_id)).all()
                availability = (
                    EvaluationAvailability.CURRENT if evaluations else EvaluationAvailability.ABSENT
                )
                requirements = {
                    row.id: row for row in session.execute(select(
                        Requirement.id, Requirement.kind, Requirement.importance,
                        Requirement.expected_value,
                    ).where(Requirement.project_id == runtime.context.project_id))
                } if evaluations else {}
                findings = [
                    SupplierRequirementFinding(
                        requirement_id=record.requirement_id,
                        kind=requirements[record.requirement_id].kind,
                        importance=requirements[record.requirement_id].importance,
                        expected_value=requirements[record.requirement_id].expected_value,
                        status=record.status,
                        evidence_ids=[UUID(value) for value in record.evidence_ids],
                    )
                    for record in evaluations if record.requirement_id in requirements
                ]
            result = SupplierSnapshot(
                supplier_id=supplier_id,
                name=supplier.name,
                country=supplier.country,
                description=supplier.description,
                capabilities=[
                    SupplierCapabilityFact(kind=value.capability_kind, value=value.value)
                    for value in session.execute(select(
                        SupplierCapability.capability_kind, SupplierCapability.value,
                    ).where(SupplierCapability.supplier_id == supplier_id).order_by(
                        SupplierCapability.capability_kind, SupplierCapability.value,
                        SupplierCapability.id,
                    ))
                ],
                general_moq=supplier.general_moq,
                general_lead_time_days=supplier.general_lead_time_days,
                indicative_price_amount=(
                    str(supplier.indicative_price_amount)
                    if supplier.indicative_price_amount is not None else None
                ),
                indicative_price_currency=supplier.indicative_price_currency,
                evaluation_availability=availability,
                evaluated_against_brief_revision=saved_revision,
                current_brief_revision=brief_revision,
                evaluations=findings,
            )
    except ToolError as error:
        runtime.record(tool_name, supplier_id, None, error.code.value)
        raise
    except Exception:
        runtime.record(tool_name, supplier_id, None, "ERROR")
        raise
    runtime.record(tool_name, supplier_id, None, "SUCCESS")
    return result


def get_supplier_evidence(
    session: Session, runtime: AnalystToolRuntime, supplier_id: UUID,
    claim_keys: tuple[str, ...] | None = None,
) -> SupplierEvidenceResult:
    """Return catalog evidence only for a still-permitted project candidate."""
    tool_name = "get_supplier_evidence"
    try:
        runtime.check_budget()
        with session.no_autoflush:
            _authorized_supplier(session, runtime, supplier_id)
            selected = set(claim_keys) if claim_keys is not None else None
            result = SupplierEvidenceResult(
                supplier_id=supplier_id,
                evidence=[
                    SupplierEvidenceItem(
                        id=value.id,
                        claim_key=value.claim_key,
                        source_type=value.source_type,
                        source_label=value.source_label,
                        source_reference=value.source_reference,
                        evidence_text=value.evidence_text,
                        evidence_state=value.evidence_state,
                    )
                    for value in session.execute(select(
                        SupplierEvidence.id, SupplierEvidence.claim_key,
                        SupplierEvidence.source_type, SupplierEvidence.source_label,
                        SupplierEvidence.source_reference, SupplierEvidence.evidence_text,
                        SupplierEvidence.evidence_state,
                    ).where(SupplierEvidence.supplier_id == supplier_id).order_by(
                        SupplierEvidence.claim_key, SupplierEvidence.source_label,
                        SupplierEvidence.id,
                    ))
                    if selected is None or value.claim_key in selected
                ],
            )
    except ToolError as error:
        runtime.record(tool_name, supplier_id, claim_keys, error.code.value)
        raise
    except Exception:
        runtime.record(tool_name, supplier_id, claim_keys, "ERROR")
        raise
    runtime.record(tool_name, supplier_id, claim_keys, "SUCCESS")
    return result
