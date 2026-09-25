from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
    event,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sourcepilot.briefs.domain import (
    BriefStatus,
    RequirementImportance,
    RequirementKind,
    validate_brief_quantity,
    validate_delivery_target,
    validate_requirement_expected_value,
    validate_target_unit_price,
)
from sourcepilot.persistence.base import Base


class DemoSession(Base):
    __tablename__ = "demo_sessions"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    opaque_token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    projects: Mapped[list[Project]] = relationship(
        back_populates="demo_session", passive_deletes=True
    )
    ai_runs: Mapped[list[AIRun]] = relationship(back_populates="demo_session", passive_deletes=True)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    demo_session_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("demo_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_request: Mapped[str] = mapped_column(Text, nullable=False)
    stage: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'BRIEF'"), default="BRIEF"
    )
    brief_revision: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"), default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    demo_session: Mapped[DemoSession] = relationship(back_populates="projects")
    brief: Mapped[Brief | None] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )
    requirements: Mapped[list[Requirement]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    ai_runs: Mapped[list[AIRun]] = relationship(back_populates="project", passive_deletes=True)
    project_suppliers: Mapped[list[ProjectSupplier]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )


class Brief(Base):
    __tablename__ = "briefs"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_briefs_quantity_positive"),
        CheckConstraint("target_unit_price > 0", name="ck_briefs_target_unit_price_positive"),
        CheckConstraint(
            "status IN ('IN_PROGRESS', 'READY_FOR_REVIEW', 'APPROVED')",
            name="ck_briefs_status",
        ),
    )

    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    destination: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_target: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    target_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'IN_PROGRESS'"),
        default=BriefStatus.IN_PROGRESS.value,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[Project] = relationship(back_populates="brief")


class Requirement(Base):
    __tablename__ = "requirements"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('MATERIAL', 'CERTIFICATION', 'MOQ', 'QUANTITY', 'UNIT_PRICE', "
            "'PRODUCTION_LEAD_TIME', 'DELIVERY', 'CAPABILITY', 'INFORMATIONAL')",
            name="ck_requirements_kind",
        ),
        CheckConstraint(
            "importance IN ('REQUIRED', 'PREFERRED', 'INFORMATIONAL')",
            name="ck_requirements_importance",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    importance: Mapped[str | None] = mapped_column(String(32), nullable=True)
    expected_value: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped[Project] = relationship(back_populates="requirements")


class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        CheckConstraint("general_moq > 0", name="ck_suppliers_general_moq_positive"),
        CheckConstraint("general_lead_time_days > 0", name="ck_suppliers_lead_time_positive"),
        CheckConstraint("indicative_price_amount > 0", name="ck_suppliers_price_positive"),
        CheckConstraint(
            "(indicative_price_amount IS NULL) = (indicative_price_currency IS NULL)",
            name="ck_suppliers_price_currency_pair",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    general_moq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    general_lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    indicative_price_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    indicative_price_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    capabilities: Mapped[list[SupplierCapability]] = relationship(
        back_populates="supplier", cascade="all, delete-orphan", passive_deletes=True
    )
    evidence: Mapped[list[SupplierEvidence]] = relationship(
        back_populates="supplier", cascade="all, delete-orphan", passive_deletes=True
    )
    project_suppliers: Mapped[list[ProjectSupplier]] = relationship(
        back_populates="supplier", passive_deletes=True
    )


class SupplierCapability(Base):
    __tablename__ = "supplier_capabilities"
    __table_args__ = (
        CheckConstraint(
            "capability_kind IN ('PRODUCT_CATEGORY', 'MATERIAL', 'CERTIFICATION', "
            "'CUSTOM_BRANDING', 'BRANDING_METHOD', 'PRODUCT_FEATURE', "
            "'MANUFACTURING_CAPABILITY')",
            name="ck_supplier_capabilities_kind",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    supplier_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    capability_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)

    supplier: Mapped[Supplier] = relationship(back_populates="capabilities")


class SupplierEvidence(Base):
    __tablename__ = "supplier_evidence"
    __table_args__ = (
        CheckConstraint(
            "evidence_state IN ('SUPPORTS', 'CONTRADICTS', 'PARTIAL', 'UNKNOWN')",
            name="ck_supplier_evidence_state",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    supplier_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    claim_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_label: Mapped[str] = mapped_column(String(255), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_state: Mapped[str] = mapped_column(String(20), nullable=False)

    supplier: Mapped[Supplier] = relationship(back_populates="evidence")


class ProjectSupplier(Base):
    __tablename__ = "project_suppliers"
    __table_args__ = (
        CheckConstraint("evaluated_against_brief_revision >= 0", name="ck_project_suppliers_revision"),
    )

    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    supplier_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), primary_key=True
    )
    shortlisted: Mapped[bool] = mapped_column(nullable=False, default=False)
    dismissed: Mapped[bool] = mapped_column(nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_against_brief_revision: Mapped[int] = mapped_column(Integer, nullable=False)

    project: Mapped[Project] = relationship(back_populates="project_suppliers")
    supplier: Mapped[Supplier] = relationship(back_populates="project_suppliers")
    evaluations: Mapped[list[RequirementEvaluationRecord]] = relationship(
        back_populates="project_supplier", cascade="all, delete-orphan", passive_deletes=True
    )


class RequirementEvaluationRecord(Base):
    __tablename__ = "requirement_evaluations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "supplier_id"],
            ["project_suppliers.project_id", "project_suppliers.supplier_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["requirement_id"], ["requirements.id"], ondelete="CASCADE"),
        CheckConstraint(
            "status IN ('MEETS', 'DOES_NOT_MEET', 'UNKNOWN', 'CONFLICT')",
            name="ck_requirement_evaluations_status",
        ),
    )

    project_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    supplier_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    requirement_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    resolved_source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resolved_fact_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    project_supplier: Mapped[ProjectSupplier] = relationship(back_populates="evaluations")


def _validate_brief_before_persist(_: object, __: object, brief: Brief) -> None:
    if brief.quantity is not None:
        brief.quantity = validate_brief_quantity(brief.quantity)
    if brief.delivery_target is not None:
        brief.delivery_target = validate_delivery_target(brief.delivery_target)
    if brief.target_unit_price is not None:
        brief.target_unit_price = validate_target_unit_price(brief.target_unit_price)
    if brief.status is None:
        brief.status = BriefStatus.IN_PROGRESS.value
    else:
        brief.status = BriefStatus(brief.status).value


def _validate_requirement_before_persist(_: object, __: object, requirement: Requirement) -> None:
    requirement.kind = RequirementKind(requirement.kind).value
    if requirement.importance is not None:
        requirement.importance = RequirementImportance(requirement.importance).value
    requirement.expected_value = validate_requirement_expected_value(
        requirement.kind, requirement.expected_value
    )


event.listen(Brief, "before_insert", _validate_brief_before_persist)
event.listen(Brief, "before_update", _validate_brief_before_persist)
event.listen(Requirement, "before_insert", _validate_requirement_before_persist)
event.listen(Requirement, "before_update", _validate_requirement_before_persist)


class AIRun(Base):
    """Application-owned trace record for one logical AI operation."""

    __tablename__ = "ai_runs"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    demo_session_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("demo_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_turn_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tool_call_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    validation_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    demo_session: Mapped[DemoSession] = relationship(back_populates="ai_runs")
    project: Mapped[Project | None] = relationship(back_populates="ai_runs")
