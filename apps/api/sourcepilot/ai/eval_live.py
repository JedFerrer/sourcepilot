"""Eval-only PostgreSQL fixtures and adapters to existing production runtimes.

No model loop, tool implementation, schema creation, migration or reset lives here.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from ipaddress import IPv6Address, ip_address
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, inspect, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session

from sourcepilot.ai.analyst_tools import ComparisonSnapshotResult
from sourcepilot.ai.brief_interpreter import interpret_project_request
from sourcepilot.ai.clarification import generate_clarifications
from sourcepilot.ai.client import StructuredModelClient, ai_settings_from_environment
from sourcepilot.ai.comparison_advice import analyze_comparison_advice
from sourcepilot.ai.comparison_advice_eval import scenario_snapshot
from sourcepilot.ai.quote_extractor import extract_quote_document
from sourcepilot.ai.supplier_explanation import explain_supplier
from sourcepilot.ai.tradeoff_analysis import analyze_tradeoffs
from sourcepilot.ai.tradeoff_analysis_eval import fixture_snapshot
from sourcepilot.briefs.readiness import ReadinessRequirement, evaluate_brief_readiness
from sourcepilot.briefs.schemas import BriefResponse, RequirementResponse
from sourcepilot.comparison.service import active_quote_revisions
from sourcepilot.documents.parse_pdf import ParsedBlock
from sourcepilot.persistence.base import Base
from sourcepilot.persistence.models import (
    AIRun,
    Brief,
    Comparison,
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
    SupplierEvidence,
)

API_ROOT = Path(__file__).resolve().parents[2]
EVAL_DATABASE_URL_ENV = "EVAL_DATABASE_URL"


class EvalPreflightError(RuntimeError):
    pass


def database_target(url: URL) -> tuple[str, int, frozenset[str]]:
    """Resolve an eval safety identity independently of credentials and driver."""
    if url.get_backend_name() != "postgresql" or not url.host or not url.database or url.query:
        raise EvalPreflightError("Isolation requires explicit PostgreSQL host/database URLs.")
    addresses: set[str] = set()
    for item in socket.getaddrinfo(url.host, url.port or 5432, type=socket.SOCK_STREAM):
        address = ip_address(str(item[4][0]))
        if isinstance(address, IPv6Address) and address.ipv4_mapped is not None:
            address = address.ipv4_mapped
        addresses.add("loopback" if address.is_loopback else str(address))
    if not addresses:
        raise EvalPreflightError("Database host resolution did not establish eval isolation.")
    return url.database, url.port or 5432, frozenset(addresses)


def validate_database_isolation(url: URL) -> None:
    """Fail closed for configured protected targets; never use them as fallbacks."""
    candidate = database_target(url)
    for key in ("DATABASE_URL", "TEST_DATABASE_URL"):
        value = os.environ.get(key)
        if value is None:
            continue
        protected = database_target(make_url(value))
        if candidate[:2] == protected[:2] and candidate[2] & protected[2]:
            raise EvalPreflightError(f"EVAL_DATABASE_URL must target a separate database from {key}.")


def preflight_database() -> Engine:
    """Read-only validation; deliberately no fallback to application/test URLs."""
    try:
        ai_settings_from_environment()
    except RuntimeError as error:
        raise EvalPreflightError(str(error)) from error
    value = os.environ.get(EVAL_DATABASE_URL_ENV)
    if not value:
        raise EvalPreflightError("EVAL_DATABASE_URL is required for live evals.")
    engine: Engine | None = None
    try:
        url = make_url(value)
        if url.get_backend_name() != "postgresql" or not url.host or not url.database:
            raise EvalPreflightError("A PostgreSQL host and database are required.")
        # Do not permit environment/URL routing overrides to repurpose another DB.
        if url.query or any(key.startswith("PG") for key in os.environ):
            raise EvalPreflightError("PostgreSQL routing overrides are not supported by evals.")
        validate_database_isolation(url)
        engine = create_engine(url, connect_args={"connect_timeout": 5}, pool_pre_ping=True)
        config = Config()
        config.set_main_option("script_location", str(API_ROOT / "alembic"))
        heads = set(ScriptDirectory.from_config(config).get_heads())
        with engine.connect() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            database = connection.scalar(text("SELECT current_database()"))
            if database != url.database:
                raise EvalPreflightError("Connected database does not match eval configuration.")
            revisions = set(connection.scalars(text("SELECT version_num FROM alembic_version")))
            if not heads or revisions != heads:
                raise EvalPreflightError(
                    "Eval database must already be migrated to repository heads."
                )
            inspector = inspect(connection)
            for table in Base.metadata.sorted_tables:
                columns = {column["name"] for column in inspector.get_columns(table.name)}
                if not set(table.columns.keys()) <= columns:
                    raise EvalPreflightError(f"Eval schema is missing columns in {table.name}.")
        return engine
    except Exception as error:
        if engine is not None:
            engine.dispose()
        if isinstance(error, EvalPreflightError):
            raise
        raise EvalPreflightError(
            f"Eval database preflight failed ({type(error).__name__})."
        ) from error


def remap(value: Any, identities: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {identities.get(key, key): remap(item, identities) for key, item in value.items()}
    if isinstance(value, list):
        return [remap(item, identities) for item in value]
    return identities.get(value, value) if isinstance(value, str) else value


def fresh_project(session: Session, case: dict[str, Any]) -> tuple[DemoSession, Project]:
    now = datetime.now(UTC)
    owner = DemoSession(
        opaque_token=uuid4().hex, last_seen_at=now, expires_at=now + timedelta(hours=24)
    )
    project = Project(
        demo_session=owner,
        name=f"Synthetic M6 eval: {case['id']}",
        original_request=case.get("request", "Synthetic eval only"),
        brief_revision=1,
        stage="QUOTES",
    )
    session.add(project)
    session.flush()
    return owner, project


def supplier_fixture(session: Session, project: Project, case: dict[str, Any]) -> dict[str, str]:
    session.add(Brief(project_id=project.id, status="APPROVED", approved_at=datetime.now(UTC)))
    identities = {"11111111-1111-1111-1111-111111111111": str(uuid4())}
    for finding in case["findings"]:
        identities[finding["requirement_id"]] = str(uuid4())
    for value in case["fetched_evidence_ids"]:
        identities[value] = str(uuid4())
    supplier_id = UUID(identities["11111111-1111-1111-1111-111111111111"])
    session.add(
        Supplier(
            id=supplier_id,
            name=f"Synthetic M6 supplier {supplier_id}",
            country="Demo",
            description="Synthetic eval fixture",
        )
    )
    session.flush()
    session.add(
        ProjectSupplier(
            project_id=project.id,
            supplier_id=supplier_id,
            evaluated_against_brief_revision=1,
            shortlisted=True,
        )
    )
    session.flush()
    for finding in remap(case["findings"], identities):
        session.add(
            Requirement(
                id=UUID(finding["requirement_id"]),
                project_id=project.id,
                kind=finding["kind"],
                importance=finding["importance"],
                expected_value=finding["expected_value"],
            )
        )
    session.flush()
    for finding in remap(case["findings"], identities):
        session.add(
            RequirementEvaluationRecord(
                project_id=project.id,
                supplier_id=supplier_id,
                requirement_id=UUID(finding["requirement_id"]),
                status=finding["status"],
                evidence_ids=finding["evidence_ids"],
            )
        )
    for value in case["fetched_evidence_ids"]:
        # Exact fixture claims supporting these synthetic findings, not real supplier data.
        related = [finding for finding in case["findings"] if value in finding["evidence_ids"]]
        session.add(
            SupplierEvidence(
                id=UUID(identities[value]),
                supplier_id=supplier_id,
                claim_key=related[0]["kind"] if related else "GENERAL",
                source_type="SYNTHETIC",
                source_label="Synthetic eval evidence",
                evidence_text=json.dumps(related, sort_keys=True),
                evidence_state={"MEETS": "SUPPORTS", "DOES_NOT_MEET": "CONTRADICTS"}.get(
                    related[0]["status"], "PARTIAL"
                )
                if related
                else "UNKNOWN",
            )
        )
    session.commit()
    return identities


def canonical_quote_field(
    supplier: dict[str, Any], field: dict[str, Any],
) -> dict[str, Any]:
    """Convert legacy eval provenance without treating source evidence as extraction."""
    result = deepcopy(field)
    evidence = result.get("evidence", [])

    def alias(primary: str, legacy: str) -> tuple[bool, Any]:
        if (primary in result and legacy in result
                and json.dumps(result[primary], sort_keys=True)
                != json.dumps(result[legacy], sort_keys=True)):
            raise ValueError(f"Conflicting provenance aliases: {primary}/{legacy}")
        return primary in result or legacy in result, result.get(primary, result.get(legacy))

    has_origin, origin = alias("origin", "current_origin")
    has_extraction, extracted = alias("ai_extracted_value", "extracted_value")
    if not has_origin:
        if evidence or has_extraction:
            raise ValueError("Ambiguous quote origin")
        origin = "USER_ENTERED"
    if origin not in {"AI_EXTRACTED", "USER_CORRECTED", "USER_ENTERED"}:
        raise ValueError("Invalid quote origin")
    if origin == "USER_ENTERED" and (evidence or extracted is not None):
        raise ValueError("Manual value cannot acquire extraction or PDF evidence")
    if origin == "AI_EXTRACTED":
        if not has_extraction:
            extracted = result["current_value"]
        elif extracted is not None and extracted != result["current_value"]:
            raise ValueError("Unchanged extraction differs from current value")
    if origin == "USER_CORRECTED" and not has_extraction and evidence:
        # The retained fixture explicitly documents this correction. Cardinality
        # alone is never proof that a source value was the model's extraction.
        from sourcepilot.ai.tradeoff_analysis_eval import PDF_PRICE, QA, A

        if not (
            supplier["supplier_id"] == A and supplier["quote_id"] == QA
            and result["field_key"] == "unit_price" and result["current_value"] == "4.50"
            and evidence == [{"id": PDF_PRICE, "evidence_value": "4.22"}]
        ):
            raise ValueError("Ambiguous legacy correction extraction")
        extracted = "4.22"
    result.pop("current_origin", None)
    result.pop("extracted_value", None)
    result.update(origin=origin, ai_extracted_value=extracted, evidence=evidence)
    return result


def comparison_fixture(
    session: Session, project: Project, case: dict[str, Any]
) -> tuple[ComparisonSnapshotResult, dict[str, str]]:
    snapshot = scenario_snapshot(case) if "snapshot_id" in case else fixture_snapshot()
    payload = cast(dict[str, Any], deepcopy(snapshot.comparison_payload))
    assert payload is not None
    # Validate identities before remapping; duplicate evidence must not silently
    # acquire a different owner when assigned fresh database IDs.
    seen: set[str] = {str(snapshot.snapshot_id)}
    for requirement in payload["brief"]["requirements"]:
        if requirement["id"] in seen:
            raise ValueError("Duplicate fixture identity or evidence ownership")
        seen.add(requirement["id"])
    for supplier in payload["suppliers"]:
        fields = supplier["quote_fields"]
        keys = [field["field_key"] for field in fields]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate quote field")
        owned = [supplier["supplier_id"], supplier["quote_id"]]
        owned.extend(source["id"] for field in fields for source in field["evidence"])
        for identity in owned:
            if identity in seen:
                raise ValueError("Duplicate fixture identity or evidence ownership")
            seen.add(identity)
        supplier["quote_fields"] = [canonical_quote_field(supplier, field) for field in fields]
    identities = {str(snapshot.snapshot_id): str(uuid4())}
    for requirement in payload["brief"]["requirements"]:
        identities[requirement["id"]] = str(uuid4())
    for supplier in payload["suppliers"]:
        identities[supplier["supplier_id"]] = str(uuid4())
        identities[supplier["quote_id"]] = str(uuid4())
        for field in supplier["quote_fields"]:
            for evidence in field["evidence"]:
                identities[evidence["id"]] = str(uuid4())
    payload = remap(payload, identities)
    project.brief_revision = snapshot.brief_revision or 1
    session.add(
        Brief(
            project_id=project.id,
            product_name="bags",
            category="bags",
            quantity=2000,
            status="APPROVED",
        )
    )
    for requirement in payload["brief"]["requirements"]:
        expected = {"value": "GRS"} if requirement["kind"] == "CERTIFICATION" else {"max_days": 30}
        requirement["expected_value"] = expected
        session.add(
            Requirement(
                id=UUID(requirement["id"]),
                project_id=project.id,
                kind=requirement["kind"],
                importance=requirement["importance"],
                expected_value=expected,
            )
        )
    for supplier in payload["suppliers"]:
        supplier_id = UUID(supplier["supplier_id"])
        session.add(
            Supplier(
                id=supplier_id,
                name=f"{supplier['supplier_name']} (synthetic {supplier_id})",
                country="Demo",
                description="Synthetic eval supplier",
                general_lead_time_days=supplier["supplier_facts"].get("general_lead_time_days"),
            )
        )
    session.flush()
    for supplier in payload["suppliers"]:
        supplier_id = UUID(supplier["supplier_id"])
        session.add(
            ProjectSupplier(
                project_id=project.id,
                supplier_id=supplier_id,
                shortlisted=True,
                evaluated_against_brief_revision=project.brief_revision,
            )
        )
        quote = Quote(
            id=UUID(supplier["quote_id"]),
            project_id=project.id,
            supplier_id=supplier_id,
            entry_type="PDF",
            status="CONFIRMED",
            revision=1,
        )
        session.add(quote)
        session.flush()
        document = QuoteDocument(
            quote=quote,
            storage_key=f"m6-{uuid4()}.pdf",
            original_filename="synthetic-provenance.pdf",
            sha256="0" * 64,
            page_count=1,
            processing_status="CONFIRMED",
            is_active=True,
        )
        session.add(document)
        session.flush()
        block_number = 0
        for field in supplier["quote_fields"]:
            value = field["current_value"]
            evidence = field["evidence"]
            quote_value = QuoteValue(
                quote_id=quote.id,
                field_key=field["field_key"],
                current_value=value,
                current_origin=field["origin"],
                ai_extracted_value=field["ai_extracted_value"],
            )
            session.add(quote_value)
            session.flush()
            for source in evidence:
                block_number += 1
                block = DocumentBlock(
                    id=uuid4(),
                    quote_document_id=document.id,
                    page_number=1,
                    block_number=block_number,
                    text=f"Synthetic original {field['field_key']}: {source['evidence_value']}",
                )
                session.add(block)
                session.flush()
                session.add(
                    QuoteFieldEvidence(
                        id=UUID(source["id"]),
                        quote_value_id=quote_value.id,
                        document_block_id=block.id,
                        evidence_value=source["evidence_value"],
                    )
                )
    session.flush()
    for supplier in payload["suppliers"]:
        for finding in supplier["evaluation"]["results"]:
            session.add(
                RequirementEvaluationRecord(
                    project_id=project.id,
                    supplier_id=UUID(supplier["supplier_id"]),
                    requirement_id=UUID(finding["requirement_id"]),
                    status=finding["status"],
                    evidence_ids=[],
                )
            )
    session.flush()
    revisions = active_quote_revisions(session, project.id)
    comparison = Comparison(
        id=UUID(identities[str(snapshot.snapshot_id)]),
        project_id=project.id,
        brief_revision=project.brief_revision,
        quote_revision_snapshot=revisions,
        comparison_payload=payload,
        stale=case.get("guard") == "stale",
    )
    session.add(comparison)
    session.commit()
    return snapshot, identities


def run_case(
    session: Session,
    category: str,
    case: dict[str, Any],
    client_factory: Callable[[], StructuredModelClient],
    blocks: list[ParsedBlock] | None = None,
) -> tuple[Any, AIRun | None]:
    """Prepare isolated inputs, call existing entry point, preserve actual AIRun outcome."""
    owner, project = fresh_project(session, case)
    identities: dict[str, str] = {}
    if category == "supplier_explanation":
        identities = supplier_fixture(session, project, case)
    elif category in {"comparison", "suggestion"}:
        _, identities = comparison_fixture(session, project, case)
    else:
        session.commit()
    try:
        if category == "brief":
            result, run = interpret_project_request(
                session, demo_session=owner, project_id=project.id, client=client_factory()
            )
            return result.model_dump(mode="json") if result else None, run
        if category == "clarification":
            brief = case["brief"]
            requirements = [
                RequirementResponse(
                    id=uuid4(),
                    kind=value["kind"],
                    importance=None,
                    expected_value=value["expected_value"],
                    notes=None,
                )
                for value in brief["requirements"]
            ]
            readiness = evaluate_brief_readiness(
                **{
                    key: brief[key]
                    for key in (
                        "product_name",
                        "category",
                        "quantity",
                        "destination",
                        "delivery_target",
                    )
                },
                requirements=tuple(
                    ReadinessRequirement(kind=item.kind, expected_value=item.expected_value)
                    for item in requirements
                ),
            )
            if not readiness.missing_fields:
                return {"questions": []}, None
            response = BriefResponse(
                **{
                    key: brief[key]
                    for key in (
                        "product_name",
                        "category",
                        "quantity",
                        "destination",
                        "delivery_target",
                    )
                },
                target_unit_price=brief.get("target_unit_price"),
                requirements=requirements,
                status="IN_PROGRESS",
                approved_at=None,
                missing_fields=[],
                uncertainties=[],
                brief_revision=1,
                can_analyze=False,
            )
            result, run = generate_clarifications(
                session,
                demo_session=owner,
                project_id=project.id,
                brief=response,
                missing_fields=readiness.missing_fields,
                client=client_factory(),
            )
            return result.model_dump(mode="json") if result else None, run
        if category == "quote_extraction":
            assert blocks
            supplier = Supplier(
                id=uuid4(),
                name=f"Synthetic extraction {uuid4()}",
                country="Demo",
                description="Synthetic eval",
            )
            session.add(supplier)
            session.flush()
            quote = Quote(
                project_id=project.id,
                supplier_id=supplier.id,
                entry_type="PDF",
                status="PROCESSING",
                revision=0,
            )
            session.add(quote)
            session.flush()
            document = QuoteDocument(
                quote=quote,
                storage_key=f"m6-{uuid4()}.pdf",
                original_filename=case["pdf"],
                sha256=hashlib.sha256(
                    (API_ROOT / "tests/fixtures/quote_pdfs" / case["pdf"]).read_bytes()
                ).hexdigest(),
                page_count=max(block.page_number for block in blocks),
                processing_status="PROCESSING",
            )
            session.add(document)
            session.flush()
            session.add_all(
                DocumentBlock(
                    id=uuid4(),
                    quote_document_id=document.id,
                    page_number=b.page_number,
                    block_number=b.block_number,
                    text=b.text,
                )
                for b in blocks
            )
            session.commit()
            result, run = extract_quote_document(
                session, demo_session=owner, document_id=document.id, client=client_factory()
            )
            return result.model_dump(mode="json") if result else None, run
        if category == "supplier_explanation":
            response = explain_supplier(
                session,
                demo_session_id=owner.id,
                project_id=project.id,
                supplier_id=UUID(identities["11111111-1111-1111-1111-111111111111"]),
                client_factory=client_factory,
            )
            output = response.explanation.model_dump(mode="json")
        elif category == "suggestion":
            response = analyze_comparison_advice(
                session,
                demo_session_id=owner.id,
                project_id=project.id,
                snapshot_id=UUID(identities[case["snapshot_id"]]),
                client_factory=client_factory,
            )
            output = response.model_dump(mode="json", exclude={"run_id", "snapshot_id"})
        else:
            response = analyze_tradeoffs(
                session,
                demo_session_id=owner.id,
                project_id=project.id,
                client_factory=client_factory,
            )
            output = response.analysis.model_dump(mode="json")
        actual = remap(output, {value: key for key, value in identities.items()})
        return (
            {"rendered_explanation": actual} if category == "supplier_explanation" else actual
        ), session.get(AIRun, response.run_id)
    except Exception:
        # Known model-caused runtime termination is classified by the persisted run,
        # never inferred from a generic exception message. Unexpected exceptions propagate.
        run = session.scalar(
            select(AIRun).where(AIRun.project_id == project.id).order_by(AIRun.started_at.desc())
        )
        if run is not None and run.status in {
            "VALIDATION_FAILED",
            "FAILED_LIMIT_REACHED",
            "PROVIDER_FAILED",
        }:
            return None, run
        if (
            run is not None
            and run.status == "FAILED"
            and run.error_type in {"NOT_ALLOWED", "NOT_FOUND"}
        ):
            return None, run  # Production tools correctly rejected model-selected scope.
        raise
