"""Read-only, project-scoped tools for the bounded Sourcing Analyst."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from sourcepilot.comparison.facts import unresolved_quote_conflict
from sourcepilot.comparison.service import comparison_response, latest_comparison
from sourcepilot.persistence.models import (
    DemoSession,
    DocumentBlock,
    Project,
    ProjectSupplier,
    Quote,
    QuoteDocument,
    QuoteFieldEvidence,
    QuoteValue,
    Requirement,
    RequirementEvaluationRecord,
    Supplier,
    SupplierCapability,
    SupplierEvidence,
)
from sourcepilot.quotes.domain import QuoteEntryType, QuoteStatus, QuoteValueOrigin
from sourcepilot.suppliers.timing import TimingDisclosure, TimingScopeError, read_supplier_timing

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
    permitted_quote_ids: frozenset[UUID] = frozenset()

    def __post_init__(self) -> None:
        object.__setattr__(self, "permitted_supplier_ids", frozenset(self.permitted_supplier_ids))
        object.__setattr__(self, "permitted_quote_ids", frozenset(self.permitted_quote_ids))
        if self.max_tool_calls <= 0:
            raise ValueError("max_tool_calls must be positive")


@dataclass(frozen=True)
class ToolTraceEvent:
    tool_name: str
    supplier_id: UUID | None
    claim_keys: tuple[str, ...] | None
    outcome: str
    successful_call_count: int
    quote_id: UUID | None = None
    field_key: str | None = None


@dataclass
class AnalystToolRuntime:
    context: AnalystToolContext
    successful_call_count: int = field(default=0, init=False)
    _events: list[ToolTraceEvent] = field(default_factory=list, init=False, repr=False)

    @property
    def trace(self) -> tuple[ToolTraceEvent, ...]:
        return tuple(self._events)

    def record(
        self, tool_name: str, supplier_id: UUID | None, claim_keys: tuple[str, ...] | None,
        outcome: str, *, quote_id: UUID | None = None, field_key: str | None = None,
    ) -> None:
        if outcome == "SUCCESS":
            self.successful_call_count += 1
        self._events.append(ToolTraceEvent(
            tool_name=tool_name,
            supplier_id=supplier_id,
            claim_keys=claim_keys,
            outcome=outcome,
            successful_call_count=self.successful_call_count,
            quote_id=quote_id,
            field_key=field_key,
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
    timing_disclosure: TimingDisclosure | None = None
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


class ComparisonSnapshotResult(BaseModel):
    availability: EvaluationAvailability
    snapshot_id: UUID | None
    brief_revision: int | None
    quote_revision_snapshot: dict[str, object] | None
    generated_at: datetime | None
    stale: bool
    comparison_payload: dict[str, object] | None


class QuoteEvidenceCitation(BaseModel):
    id: UUID
    quote_document_id: UUID
    document_block_id: UUID
    page_number: int
    block_number: int
    untrusted_source_text: str
    evidence_value: object | None
    role: str


class QuoteEvidenceResult(BaseModel):
    quote_id: UUID
    supplier_id: UUID
    quote_revision: int
    field_key: str
    current_value: object | None
    current_origin: str
    ai_extracted_value: object | None
    uncertainty: str | None
    evidence: list[QuoteEvidenceCitation]


def _isolated_read_session(session: Session) -> Session:
    """Read persisted rows without touching the caller's identity map or pending edits."""
    return Session(bind=session.connection(), autoflush=False, join_transaction_mode="rollback_only")


def _authorized_project(session: Session, runtime: AnalystToolRuntime) -> None:
    context = runtime.context
    project_id = session.scalar(select(Project.id).join(
        DemoSession, DemoSession.id == Project.demo_session_id,
    ).where(
        Project.id == context.project_id,
        Project.demo_session_id == context.demo_session_id,
        DemoSession.expires_at > datetime.now(UTC),
    ))
    if project_id is None:
        raise ToolError(ToolErrorCode.NOT_ALLOWED)


def get_comparison_snapshot(
    session: Session, runtime: AnalystToolRuntime,
) -> ComparisonSnapshotResult:
    """Return only a current comparison payload; stale history stays metadata-only."""
    tool_name = "get_comparison_snapshot"
    try:
        runtime.check_budget()
        with session.no_autoflush, _isolated_read_session(session) as read_session:
            _authorized_project(read_session, runtime)
            comparison = latest_comparison(read_session, runtime.context.project_id)
            if comparison is None:
                result = ComparisonSnapshotResult(
                    availability=EvaluationAvailability.ABSENT,
                    snapshot_id=None, brief_revision=None, quote_revision_snapshot=None,
                    generated_at=None, stale=False, comparison_payload=None,
                )
            else:
                response = comparison_response(read_session, comparison)
                stale = bool(response["stale"])
                result = ComparisonSnapshotResult(
                    availability=(EvaluationAvailability.STALE if stale
                                  else EvaluationAvailability.CURRENT),
                    snapshot_id=comparison.id,
                    brief_revision=comparison.brief_revision,
                    quote_revision_snapshot=comparison.quote_revision_snapshot,
                    generated_at=comparison.generated_at,
                    stale=stale,
                    comparison_payload=None if stale else comparison.comparison_payload,
                )
    except ToolError as error:
        runtime.record(tool_name, None, None, error.code.value)
        raise
    except Exception:
        runtime.record(tool_name, None, None, "ERROR")
        raise
    runtime.record(tool_name, None, None, "SUCCESS")
    return result


def get_quote_evidence(
    session: Session, runtime: AnalystToolRuntime, quote_id: UUID, field_key: str,
) -> QuoteEvidenceResult:
    """Return one confirmed field and citations from its active PDF only."""
    tool_name = "get_quote_evidence"
    try:
        runtime.check_budget()
        if quote_id not in runtime.context.permitted_quote_ids:
            raise ToolError(ToolErrorCode.NOT_ALLOWED)
        with session.no_autoflush, _isolated_read_session(session) as read_session:
            _authorized_project(read_session, runtime)
            quote = read_session.scalars(select(Quote).join(
                ProjectSupplier,
                (ProjectSupplier.project_id == Quote.project_id)
                & (ProjectSupplier.supplier_id == Quote.supplier_id),
            ).where(
                Quote.id == quote_id,
                Quote.project_id == runtime.context.project_id,
                Quote.status == QuoteStatus.CONFIRMED.value,
                ProjectSupplier.shortlisted.is_(True),
                ProjectSupplier.dismissed.is_(False),
                Quote.supplier_id.in_(runtime.context.permitted_supplier_ids),
            )).one_or_none()
            if quote is None:
                raise ToolError(ToolErrorCode.NOT_ALLOWED)
            value = read_session.scalars(select(QuoteValue).where(
                QuoteValue.quote_id == quote_id, QuoteValue.field_key == field_key,
            )).one_or_none()
            if value is None:
                raise ToolError(ToolErrorCode.NOT_FOUND)
            citations: list[QuoteEvidenceCitation] = []
            if quote.entry_type == QuoteEntryType.PDF.value:
                rows = read_session.execute(select(
                    QuoteFieldEvidence.id, QuoteDocument.id, DocumentBlock.id,
                    DocumentBlock.page_number, DocumentBlock.block_number,
                    DocumentBlock.text, QuoteFieldEvidence.evidence_value,
                ).join(
                    DocumentBlock, DocumentBlock.id == QuoteFieldEvidence.document_block_id,
                ).join(
                    QuoteDocument, QuoteDocument.id == DocumentBlock.quote_document_id,
                ).where(
                    QuoteFieldEvidence.quote_value_id == value.id,
                    QuoteDocument.quote_id == quote_id,
                    QuoteDocument.is_active.is_(True),
                ).order_by(
                    DocumentBlock.page_number, DocumentBlock.block_number,
                    QuoteFieldEvidence.id,
                )).all()
                provenance = (value.current_origin == QuoteValueOrigin.USER_CORRECTED.value
                              or unresolved_quote_conflict(value))
                citations = [QuoteEvidenceCitation(
                    id=row[0], quote_document_id=row[1], document_block_id=row[2],
                    page_number=row[3], block_number=row[4], untrusted_source_text=row[5],
                    evidence_value=row[6],
                    role="provenance" if provenance else "supporting",
                ) for row in rows]
            result = QuoteEvidenceResult(
                quote_id=quote.id, supplier_id=quote.supplier_id,
                quote_revision=quote.revision, field_key=value.field_key,
                current_value=value.current_value, current_origin=value.current_origin,
                ai_extracted_value=value.ai_extracted_value,
                uncertainty=value.uncertainty, evidence=citations,
            )
    except ToolError as error:
        runtime.record(tool_name, None, None, error.code.value,
                       quote_id=quote_id, field_key=field_key)
        raise
    except Exception:
        runtime.record(tool_name, None, None, "ERROR", quote_id=quote_id, field_key=field_key)
        raise
    runtime.record(tool_name, None, None, "SUCCESS", quote_id=quote_id, field_key=field_key)
    return result


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
                timing_disclosure=read_supplier_timing(
                    session, demo_session_id=runtime.context.demo_session_id,
                    project_id=runtime.context.project_id, supplier_id=supplier_id,
                ),
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
    except TimingScopeError as error:
        runtime.record(tool_name, supplier_id, None, ToolErrorCode.NOT_ALLOWED.value)
        raise ToolError(ToolErrorCode.NOT_ALLOWED) from error
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
