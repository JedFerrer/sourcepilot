"""Generate and read deterministic, revision-aware project comparisons."""

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from sourcepilot.briefs.domain import BriefStatus, RequirementKind
from sourcepilot.comparison.evaluation import evaluate_comparison
from sourcepilot.comparison.facts import (
    confirmed_quote_currency,
    resolve_commercial_facts,
    resolve_delivery_commitment,
    resolve_quoted_quantity,
    unresolved_quote_conflict,
)
from sourcepilot.comparison.source_resolution import SourceResolution, SourceResolutionStatus
from sourcepilot.persistence.models import (
    Brief,
    Comparison,
    Project,
    ProjectSupplier,
    Quote,
    QuoteFieldEvidence,
    QuoteValue,
    Supplier,
)
from sourcepilot.quotes.domain import QUOTE_FIELD_KEYS, QuoteStatus, QuoteValueOrigin
from sourcepilot.suppliers.evaluation import (
    EvaluationEvidence,
    EvaluationRequirement,
    SupplierEvaluationFacts,
)


class ComparisonNotReadyError(ValueError):
    """Current project inputs cannot produce a multi-supplier comparison."""


def _json_value(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_value(item) for item in value]
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


def active_quote_revisions(database_session: Session, project_id: UUID) -> dict[str, object]:
    """Key current quotes by supplier, identity, revision, and comparison facts."""
    quotes = database_session.scalars(
        select(Quote)
        .join(ProjectSupplier, (ProjectSupplier.project_id == Quote.project_id)
              & (ProjectSupplier.supplier_id == Quote.supplier_id))
        .where(Quote.project_id == project_id, Quote.status == QuoteStatus.CONFIRMED.value,
               ProjectSupplier.shortlisted.is_(True), ProjectSupplier.dismissed.is_(False))
        .order_by(Quote.supplier_id)
        .options(selectinload(Quote.values).selectinload(QuoteValue.evidence))
    ).all()
    return {str(quote.supplier_id): {
        "quote_id": str(quote.id), "revision": quote.revision,
        "facts_fingerprint": _quote_fingerprint(quote),
    } for quote in quotes}


def _quote_fingerprint(quote: Quote) -> str:
    facts = [{
        "field_key": value.field_key,
        "current_value": value.current_value,
        "current_origin": value.current_origin,
        "ai_extracted_value": value.ai_extracted_value,
        "uncertainty": value.uncertainty,
        "evidence": [{"id": str(item.id), "value": item.evidence_value}
                     for item in sorted(value.evidence, key=lambda item: str(item.id))],
    } for value in sorted(quote.values, key=lambda item: item.field_key)]
    encoded = json.dumps(_json_value(facts), sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def mark_comparisons_stale(database_session: Session, project_id: UUID) -> None:
    """Invalidate stored comparisons within the input change's transaction."""
    database_session.execute(
        update(Comparison).where(Comparison.project_id == project_id, Comparison.stale.is_(False))
        .values(stale=True)
    )


def _supplier_facts(supplier: Supplier) -> SupplierEvaluationFacts:
    return SupplierEvaluationFacts(
        capabilities=frozenset((item.capability_kind, item.value) for item in supplier.capabilities),
        general_moq=supplier.general_moq,
        evidence=tuple(EvaluationEvidence(item.id, item.claim_key, item.evidence_state)
                       for item in sorted(supplier.evidence, key=lambda value: str(value.id))),
    )


def _resolution_state(resolution: SourceResolution) -> str:
    if resolution.status is SourceResolutionStatus.CONFLICT:
        return "conflicting"
    if resolution.status is SourceResolutionStatus.UNAVAILABLE or resolution.selected is None:
        return "missing"
    return "known"


def _quote_fields(quote: Quote) -> list[dict[str, object]]:
    fields: list[dict[str, object]] = []
    for value in sorted(quote.values, key=lambda item: item.field_key):
        fields.append({
            "field_key": value.field_key,
            "current_value": value.current_value,
            "origin": value.current_origin,
            "ai_extracted_value": value.ai_extracted_value,
            "uncertainty": value.uncertainty,
            "source_reference": f"quote-value:{value.id}",
            "evidence": [
                {"id": str(item.id), "value": item.evidence_value,
                 "document_block_id": str(item.document_block_id),
                 "quote_document_id": str(item.block.quote_document_id),
                 "page_number": item.block.page_number,
                 "block_number": item.block.block_number,
                 "role": "provenance" if value.current_origin == QuoteValueOrigin.USER_CORRECTED
                 or unresolved_quote_conflict(value) else "supporting"}
                for item in sorted(value.evidence, key=lambda item: str(item.id))
            ],
        })
    return fields


def _completeness(resolutions: dict[str, SourceResolution], quote: Quote) -> list[dict[str, object]]:
    values = {item.field_key: item for item in quote.values}
    fields: list[dict[str, object]] = []
    for key in sorted(QUOTE_FIELD_KEYS | {"delivery_date"}):
        resolution = resolutions.get(key)
        if resolution is not None:
            fields.append({
                "field_key": key, "state": _resolution_state(resolution),
                "source_references": sorted({fact.source_reference for fact in
                    (*resolution.project_facts, *resolution.general_facts)}),
            })
            continue
        value = values.get(key)
        state = ("missing" if value is None else
                 "conflicting" if unresolved_quote_conflict(value) else
                 "missing" if value.current_value is None else "known")
        fields.append({
            "field_key": key, "state": state,
            "source_references": [f"quote-value:{value.id}"] if value is not None else [],
        })
    return fields


def _comparison_payload(database_session: Session, project: Project, brief: Brief) -> dict[str, object]:
    rows = database_session.scalars(
        select(ProjectSupplier)
        .where(ProjectSupplier.project_id == project.id, ProjectSupplier.shortlisted.is_(True),
               ProjectSupplier.dismissed.is_(False))
        .options(selectinload(ProjectSupplier.supplier).selectinload(Supplier.capabilities),
                 selectinload(ProjectSupplier.supplier).selectinload(Supplier.evidence))
    ).all()
    rows = sorted(rows, key=lambda item: str(item.supplier_id))
    quotes = database_session.scalars(
        select(Quote).where(Quote.project_id == project.id, Quote.status == QuoteStatus.CONFIRMED.value)
        .options(selectinload(Quote.values).selectinload(QuoteValue.evidence)
                 .selectinload(QuoteFieldEvidence.block))
    ).all()
    by_supplier = {quote.supplier_id: quote for quote in quotes}
    included = [(row, by_supplier[row.supplier_id]) for row in rows
                if row.supplier_id in by_supplier]
    if len(included) < 2:
        raise ComparisonNotReadyError("At least two shortlisted suppliers need confirmed quotes.")
    if brief.quantity is None:
        raise ComparisonNotReadyError("The approved Brief needs a requested quantity.")
    requirements = sorted(project.requirements, key=lambda item: str(item.id))
    evaluator_requirements = [
        EvaluationRequirement(item.id, RequirementKind(item.kind), item.expected_value)
        for item in requirements
    ]
    currencies = [confirmed_quote_currency(quote) for _, quote in included]
    suppliers: list[dict[str, object]] = []
    for row, quote in included:
        supplier = row.supplier
        commercial = resolve_commercial_facts(supplier, quote)
        quantity = resolve_quoted_quantity(quote)
        delivery = resolve_delivery_commitment(quote)
        resolutions = {**commercial, "quoted_quantity": quantity, "delivery_date": delivery}
        evaluation = evaluate_comparison(
            evaluator_requirements, requested_quantity=brief.quantity,
            supplier=_supplier_facts(supplier), commercial_facts=commercial,
            quoted_quantity=quantity, delivery_commitment=delivery,
            quote_currency=confirmed_quote_currency(quote), quote_currencies=currencies,
        )
        suppliers.append({
            "supplier_id": str(supplier.id), "supplier_name": supplier.name,
            "quote_id": str(quote.id), "quote_revision": quote.revision,
            "supplier_facts": {
                "country": supplier.country, "description": supplier.description,
                "general_moq": supplier.general_moq,
                "general_lead_time_days": supplier.general_lead_time_days,
                "indicative_price_amount": supplier.indicative_price_amount,
                "indicative_price_currency": supplier.indicative_price_currency,
                "capabilities": sorted((item.capability_kind, item.value)
                                       for item in supplier.capabilities),
                "evidence": [
                    {"id": str(item.id), "claim_key": item.claim_key,
                     "source_type": item.source_type, "source_reference": item.source_reference,
                     "source_label": item.source_label, "evidence_text": item.evidence_text,
                     "evidence_state": item.evidence_state}
                    for item in sorted(supplier.evidence, key=lambda item: str(item.id))
                ],
            },
            "quote_fields": _quote_fields(quote),
            "resolved_facts": {key: _json_value(value) for key, value in sorted(resolutions.items())},
            "evaluation": _json_value(evaluation),
            "completeness": _completeness(resolutions, quote),
        })
    return _json_value({
        "brief": {
            "quantity": brief.quantity,
            "target_unit_price": brief.target_unit_price,
            "delivery_target": brief.delivery_target,
            "requirements": [
                {"id": str(item.id), "kind": item.kind, "importance": item.importance,
                 "expected_value": item.expected_value, "notes": item.notes}
                for item in requirements
            ],
        },
        "suppliers": suppliers,
    })  # type: ignore[return-value]


def comparison_response(database_session: Session, comparison: Comparison) -> dict[str, object]:
    project = database_session.get(Project, comparison.project_id)
    if project is None:
        raise ValueError("Comparison project is missing.")
    stale = (comparison.stale or project.stage != "QUOTES"
             or comparison.brief_revision != project.brief_revision
             or comparison.quote_revision_snapshot != active_quote_revisions(database_session, project.id))
    return {
        "id": comparison.id, "project_id": comparison.project_id,
        "brief_revision": comparison.brief_revision,
        "quote_revision_snapshot": comparison.quote_revision_snapshot,
        "comparison_payload": comparison.comparison_payload,
        "generated_at": comparison.generated_at, "stale": stale,
    }


def latest_comparison(database_session: Session, project_id: UUID) -> Comparison | None:
    return database_session.scalars(
        select(Comparison).where(Comparison.project_id == project_id)
        .order_by(Comparison.generated_at.desc(), Comparison.id.desc()).limit(1)
    ).one_or_none()


def generate_comparison(database_session: Session, project_id: UUID) -> Comparison:
    project = database_session.scalars(
        select(Project).where(Project.id == project_id).with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    brief = database_session.get(Brief, project.id)
    if brief is None or brief.status != BriefStatus.APPROVED:
        raise ComparisonNotReadyError("Approve the Brief before generating a comparison.")
    if project.stage != "QUOTES":
        raise ComparisonNotReadyError("Approve the current shortlist before generating a comparison.")
    payload = _comparison_payload(database_session, project, brief)
    revisions = active_quote_revisions(database_session, project.id)
    mark_comparisons_stale(database_session, project.id)
    comparison = Comparison(
        project_id=project.id, brief_revision=project.brief_revision,
        quote_revision_snapshot=revisions, comparison_payload=payload,
        generated_at=datetime.now(UTC), stale=False,
    )
    database_session.add(comparison)
    database_session.flush()
    return comparison
