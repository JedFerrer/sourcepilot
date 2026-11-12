"""Application-owned timing disclosure; general production is never delivery evidence."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from sourcepilot.comparison.facts import resolve_commercial_facts, resolve_delivery_commitment
from sourcepilot.comparison.source_resolution import SourceResolution, resolve_sources
from sourcepilot.persistence.models import (
    Brief,
    DemoSession,
    Project,
    ProjectSupplier,
    Quote,
    QuoteValue,
    Supplier,
)
from sourcepilot.quotes.domain import QuoteStatus


class TimingScopeError(ValueError):
    pass


class TimingFact(BaseModel):
    value: str | None
    source_reference: str
    supporting_evidence_ids: list[UUID] = Field(default_factory=list)
    provenance_evidence_ids: list[UUID] = Field(default_factory=list)


class OrderTiming(BaseModel):
    status: Literal["UNKNOWN", "CONFIRMED", "CONFLICT"]
    facts: list[TimingFact] = Field(default_factory=list)


class TimingDisclosure(BaseModel):
    owner: Literal["APPLICATION"] = "APPLICATION"
    destination: str | None
    delivery_target: dict[str, object] | None
    production: OrderTiming
    delivery: OrderTiming
    freshness_key: str = ""


def order_timing(resolution: SourceResolution) -> OrderTiming:
    """Only project facts establish order timing, even when a general fallback exists."""
    if not resolution.project_facts:
        return OrderTiming(status="UNKNOWN")
    scoped = resolve_sources(resolution.project_facts[0].field_key,
                             project_facts=resolution.project_facts)
    status: Literal["UNKNOWN", "CONFIRMED", "CONFLICT"] = (
        "CONFLICT" if scoped.status == "CONFLICT" else
        "CONFIRMED" if scoped.selected is not None else "UNKNOWN"
    )
    return OrderTiming(status=status, facts=[TimingFact(
        value=str(fact.value) if fact.value is not None else None,
        source_reference=fact.source_reference,
        supporting_evidence_ids=list(fact.supporting_evidence_ids),
        provenance_evidence_ids=list(fact.provenance_evidence_ids),
    ) for fact in scoped.project_facts])


def timing_disclosure(
    *, destination: str | None, target: dict[str, object] | None,
    production: SourceResolution, delivery: SourceResolution,
) -> TimingDisclosure:
    """Pure projection, including contract-only dated delivery inputs."""
    return TimingDisclosure(destination=destination, delivery_target=target,
                            production=order_timing(production), delivery=order_timing(delivery))


def read_supplier_timing(
    session: Session, *, demo_session_id: UUID, project_id: UUID, supplier_id: UUID,
) -> TimingDisclosure:
    """Read fresh scoped facts without autoflush, writes, or model-tool budget use."""
    with session.no_autoflush:
        row = session.execute(select(ProjectSupplier, Brief, Supplier).join(
            Project, Project.id == ProjectSupplier.project_id,
        ).join(DemoSession, DemoSession.id == Project.demo_session_id).join(
            Brief, Brief.project_id == Project.id,
        ).join(Supplier, Supplier.id == ProjectSupplier.supplier_id).where(
            Project.id == project_id, Project.demo_session_id == demo_session_id,
            DemoSession.expires_at > datetime.now(UTC),
            ProjectSupplier.supplier_id == supplier_id,
        ).options(selectinload(Supplier.evidence)).execution_options(populate_existing=True)).one_or_none()
        if row is None:
            raise TimingScopeError("Supplier timing is outside the current project scope.")
        membership, brief, supplier = row
        quote = session.scalar(select(Quote).where(
            Quote.project_id == project_id, Quote.supplier_id == supplier_id,
        ).options(selectinload(Quote.values).selectinload(QuoteValue.evidence))
            .execution_options(populate_existing=True))
        eligible = bool(membership.shortlisted and not membership.dismissed
                        and quote is not None and quote.status == QuoteStatus.CONFIRMED)
        permitted_quote = quote if eligible else None
        production = resolve_commercial_facts(supplier, permitted_quote)["production_lead_time"]
        result = timing_disclosure(
            destination=brief.destination, target=brief.delivery_target,
            production=production, delivery=resolve_delivery_commitment(permitted_quote),
        )
        # Retain same-context alternatives as provenance, not a chosen interpretation.
        if result.production.status == "CONFLICT" and permitted_quote is not None:
            value = next(v for v in permitted_quote.values if v.field_key == "production_lead_time")
            result.production.facts = [TimingFact(
                value=str(e.evidence_value) if e.evidence_value is not None else None,
                source_reference=f"quote-value:{value.id}", provenance_evidence_ids=[e.id],
            ) for e in sorted(value.evidence, key=lambda item: str(item.id))]
        stamp = {
            "disclosure": result.model_dump(mode="json"),
            "membership": [membership.shortlisted, membership.dismissed],
            "quote": [str(quote.id), quote.revision, quote.status] if quote is not None else None,
        }
        result.freshness_key = hashlib.sha256(
            json.dumps(stamp, sort_keys=True, default=str).encode()
        ).hexdigest()
        return result
