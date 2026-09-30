"""Comparison generation, staleness, persistence, and API isolation."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from sourcepilot.ai.analyst_tools import (
    AnalystToolContext,
    AnalystToolRuntime,
    EvaluationAvailability,
    ToolError,
    ToolErrorCode,
    get_comparison_snapshot,
    get_quote_evidence,
    get_supplier_snapshot,
)
from sourcepilot.comparison.service import (
    _quote_fingerprint,
    _resolution_state,
    generate_comparison,
)
from sourcepilot.comparison.source_resolution import (
    FactContext,
    SourceFact,
    resolve_sources,
)
from sourcepilot.main import app
from sourcepilot.persistence.database import get_database_session
from sourcepilot.persistence.models import (
    Comparison,
    DemoSession,
    DocumentBlock,
    Project,
    ProjectSupplier,
    Quote,
    QuoteDocument,
    QuoteFieldEvidence,
    QuoteValue,
)
from sourcepilot.suppliers.seed import seed_suppliers
from tests.database_test_support import (
    create_test_engine,
    persistence_test_database_url_from_environment,
    reset_test_database,
)


@pytest.fixture(scope="module")
def database_url() -> str:
    return persistence_test_database_url_from_environment()


@pytest.fixture(scope="module")
def engine(database_url: str) -> Iterator[Engine]:
    test_engine = create_test_engine(database_url)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def client(engine: Engine, database_url: str) -> Iterator[TestClient]:
    reset_test_database(database_url)
    with Session(engine) as session:
        seed_suppliers(session)
        session.commit()
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_database_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_database_session] = override_database_session
    with TestClient(app, raise_server_exceptions=False) as value:
        assert value.post("/demo-session").status_code == 204
        yield value
    app.dependency_overrides.clear()
    reset_test_database(database_url)


def setup_project(client: TestClient) -> tuple[str, list[str]]:
    created = client.post("/projects", json={
        "name": "Bags", "original_request": "Source cosmetic travel bags.",
    })
    assert created.status_code == 201
    project_id = created.json()["id"]
    brief = client.patch(f"/projects/{project_id}/brief", json={
        "product_name": "Cosmetic bag", "category": "cosmetic travel bag", "quantity": 2000,
        "destination": "Sydney", "delivery_target": {"kind": "DATE", "date": "2027-01-01"},
        "target_unit_price": None,
        "requirements": [
            {"kind": "MATERIAL", "importance": "REQUIRED",
             "expected_value": {"value": "recycled polyester"}},
            {"kind": "CAPABILITY", "importance": "REQUIRED",
             "expected_value": {"capability_key": "CUSTOM_BRANDING", "value": True}},
        ],
    })
    assert brief.status_code == 200, brief.text
    approved = client.post(f"/projects/{project_id}/brief/approve", json={
        "expected_brief_revision": brief.json()["brief_revision"],
    })
    assert approved.status_code == 200, approved.text
    assert client.post(f"/projects/{project_id}/suppliers/discover").status_code == 200
    suppliers = client.get(f"/projects/{project_id}/suppliers").json()["suppliers"]
    ids = [item["id"] for item in suppliers[:3]]
    assert len(ids) == 3
    for supplier_id in ids:
        assert client.patch(f"/projects/{project_id}/suppliers/{supplier_id}",
                            json={"shortlisted": True}).status_code == 200
    assert client.post(f"/projects/{project_id}/shortlist/approve").status_code == 200
    return project_id, ids


def confirm_manual(client: TestClient, project_id: str, supplier_id: str,
                   price: str = "4.25", *, quantity: int = 2000,
                   currency: str = "USD") -> str:
    created = client.post(f"/projects/{project_id}/quotes/manual", json={
        "supplier_id": supplier_id,
        "values": {"quoted_quantity": quantity, "unit_price": price, "currency": currency},
    })
    assert created.status_code == 201, created.text
    quote_id = created.json()["id"]
    assert client.post(f"/quotes/{quote_id}/confirm").status_code == 200
    return quote_id


def _analyst_runtime(
    engine: Engine, project_id: str, supplier_ids: list[str], quote_ids: list[str],
    *, limit: int = 6,
) -> AnalystToolRuntime:
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        return AnalystToolRuntime(AnalystToolContext(
            demo_session_id=project.demo_session_id,
            project_id=project.id,
            permitted_supplier_ids=frozenset(UUID(value) for value in supplier_ids),
            max_tool_calls=limit,
            permitted_quote_ids=frozenset(UUID(value) for value in quote_ids),
        ))


def test_analyst_comparison_current_absent_and_stale(client: TestClient, engine: Engine) -> None:
    project_id, supplier_ids = setup_project(client)
    first_quote = confirm_manual(client, project_id, supplier_ids[0])
    second_quote = confirm_manual(client, project_id, supplier_ids[1])
    runtime = _analyst_runtime(engine, project_id, supplier_ids, [first_quote, second_quote])
    with Session(engine) as session:
        absent = get_comparison_snapshot(session, runtime)
        assert absent.availability == EvaluationAvailability.ABSENT
        assert absent.comparison_payload is None
    generated = client.post(f"/projects/{project_id}/comparison/generate")
    assert generated.status_code == 201, generated.text
    with Session(engine) as session:
        current = get_comparison_snapshot(session, runtime)
        assert current.availability == EvaluationAvailability.CURRENT
        assert current.snapshot_id == UUID(generated.json()["id"])
        assert current.comparison_payload == generated.json()["comparison_payload"]
        assert current.stale is False
        assert not session.dirty and not session.new and not session.deleted

    with Session(engine) as session:
        quote = session.get(Quote, UUID(first_quote))
        assert quote is not None
        quote.revision += 1
        session.commit()
    with Session(engine) as session:
        stale = get_comparison_snapshot(session, runtime)
        assert stale.availability == EvaluationAvailability.STALE
        assert stale.stale is True
        assert stale.snapshot_id == current.snapshot_id
        assert stale.comparison_payload is None
        stored = session.get(Comparison, current.snapshot_id)
        assert stored is not None
        assert stored.stale is False
    regenerated = client.post(f"/projects/{project_id}/comparison/generate")
    assert regenerated.status_code == 201, regenerated.text
    with Session(engine) as session:
        latest = get_comparison_snapshot(session, runtime)
        assert latest.availability == EvaluationAvailability.CURRENT
        assert latest.snapshot_id == UUID(regenerated.json()["id"])
    assert runtime.successful_call_count == 4


def test_analyst_quote_allowlist_and_scope(client: TestClient, engine: Engine) -> None:
    project_id, supplier_ids = setup_project(client)
    allowed = confirm_manual(client, project_id, supplier_ids[0])
    omitted = confirm_manual(client, project_id, supplier_ids[1])
    runtime = _analyst_runtime(engine, project_id, supplier_ids, [allowed])
    with Session(engine) as session:
        for quote_id in (UUID(omitted), uuid4()):
            with pytest.raises(ToolError) as error:
                get_quote_evidence(session, runtime, quote_id, "unit_price")
            assert error.value.code == ToolErrorCode.NOT_ALLOWED
        assert [event.outcome for event in runtime.trace] == ["NOT_ALLOWED"] * 2
        assert runtime.successful_call_count == 0
        allowed_result = get_quote_evidence(session, runtime, UUID(allowed), "unit_price")
        assert allowed_result.current_value == "4.25"
        assert allowed_result.current_origin == "USER_ENTERED"
        assert allowed_result.ai_extracted_value is None
        assert allowed_result.evidence == []
        with pytest.raises(ToolError) as error:
            get_quote_evidence(session, runtime, UUID(allowed), "missing")
        assert error.value.code == ToolErrorCode.NOT_FOUND
        assert not session.dirty and not session.new and not session.deleted
    with Session(engine) as session:
        candidate = session.get(ProjectSupplier, (UUID(project_id), UUID(supplier_ids[0])))
        assert candidate is not None
        candidate.shortlisted = False
        session.commit()
    with Session(engine) as session:
        with pytest.raises(ToolError) as error:
            get_quote_evidence(session, runtime, UUID(allowed), "unit_price")
        assert error.value.code == ToolErrorCode.NOT_ALLOWED


def test_analyst_quote_requires_confirmation(client: TestClient, engine: Engine) -> None:
    project_id, supplier_ids = setup_project(client)
    created = client.post(f"/projects/{project_id}/quotes/manual", json={
        "supplier_id": supplier_ids[0], "values": {"unit_price": "4.25"},
    })
    assert created.status_code == 201, created.text
    quote_id = UUID(created.json()["id"])
    runtime = _analyst_runtime(engine, project_id, supplier_ids, [str(quote_id)])
    with Session(engine) as session:
        with pytest.raises(ToolError) as error:
            get_quote_evidence(session, runtime, quote_id, "unit_price")
        assert error.value.code == ToolErrorCode.NOT_ALLOWED
        assert runtime.successful_call_count == 0


def test_analyst_quote_conflicting_pdf_values_are_provenance(
    client: TestClient, engine: Engine,
) -> None:
    project_id, supplier_ids = setup_project(client)
    quote_id = confirm_manual(client, project_id, supplier_ids[0])
    with Session(engine) as session:
        quote = session.get(Quote, UUID(quote_id))
        assert quote is not None
        quote.entry_type = "PDF"
        document = QuoteDocument(
            quote_id=quote.id, storage_key=f"test/{uuid4()}",
            original_filename="conflict.pdf", sha256="2" * 64, page_count=1,
            processing_status="CONFIRMED", is_active=True,
        )
        session.add(document)
        session.flush()
        value = next(item for item in quote.values if item.field_key == "unit_price")
        value.current_value = None
        value.current_origin = "AI_EXTRACTED"
        value.ai_extracted_value = None
        for block_number, evidence_value in enumerate(("4.25", "4.75"), start=1):
            block = DocumentBlock(
                id=uuid4(), quote_document_id=document.id,
                page_number=1, block_number=block_number,
                text=f"Price {evidence_value}",
            )
            session.add(block)
            session.flush()
            value.evidence.append(QuoteFieldEvidence(
                document_block_id=block.id, evidence_value=evidence_value,
            ))
        session.commit()
    runtime = _analyst_runtime(engine, project_id, supplier_ids, [quote_id])
    with Session(engine) as session:
        result = get_quote_evidence(session, runtime, UUID(quote_id), "unit_price")
        assert result.current_value is None
        assert [item.evidence_value for item in result.evidence] == ["4.25", "4.75"]
        assert all(item.role == "provenance" for item in result.evidence)


def test_analyst_tools_revalidate_session_and_preserve_pending_edits(
    client: TestClient, engine: Engine,
) -> None:
    project_id, supplier_ids = setup_project(client)
    quote_id = confirm_manual(client, project_id, supplier_ids[0])
    runtime = _analyst_runtime(engine, project_id, supplier_ids, [quote_id])
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        quote = session.get(Quote, UUID(quote_id))
        candidate = session.get(ProjectSupplier, (UUID(project_id), UUID(supplier_ids[0])))
        assert project is not None and quote is not None and candidate is not None
        project.stage = "PENDING"
        quote.status = "NEEDS_REVIEW"
        candidate.shortlisted = False
        result = get_quote_evidence(session, runtime, quote.id, "unit_price")
        assert result.current_value == "4.25"
        assert get_comparison_snapshot(session, runtime).availability == EvaluationAvailability.ABSENT
        assert {project, quote, candidate} <= set(session.dirty)
        assert project.stage == "PENDING" and quote.status == "NEEDS_REVIEW"
        assert candidate.shortlisted is False
        with Session(engine) as other:
            demo = other.get(DemoSession, runtime.context.demo_session_id)
            assert demo is not None
            demo.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            other.commit()
        for call in (
            lambda: get_comparison_snapshot(session, runtime),
            lambda: get_quote_evidence(session, runtime, quote.id, "unit_price"),
        ):
            with pytest.raises(ToolError) as error:
                call()
            assert error.value.code == ToolErrorCode.NOT_ALLOWED
        assert project.stage == "PENDING" and quote.status == "NEEDS_REVIEW"
        assert candidate.shortlisted is False


def test_analyst_tools_share_budget(client: TestClient, engine: Engine) -> None:
    project_id, supplier_ids = setup_project(client)
    quote_id = confirm_manual(client, project_id, supplier_ids[0])
    runtime = _analyst_runtime(engine, project_id, supplier_ids, [quote_id], limit=2)
    with Session(engine) as session:
        get_supplier_snapshot(session, runtime, UUID(supplier_ids[0]))
        get_quote_evidence(session, runtime, UUID(quote_id), "unit_price")
        with pytest.raises(ToolError) as error:
            get_comparison_snapshot(session, runtime)
        assert error.value.code == ToolErrorCode.LIMIT_REACHED
        assert not session.dirty and not session.new and not session.deleted
    assert runtime.successful_call_count == 2
    assert [event.outcome for event in runtime.trace] == [
        "SUCCESS", "SUCCESS", "LIMIT_REACHED",
    ]
    assert runtime.trace[1].quote_id == UUID(quote_id)
    assert runtime.trace[1].field_key == "unit_price"


def test_analyst_tools_reject_other_project_and_session(
    client: TestClient, engine: Engine,
) -> None:
    project_id, supplier_ids = setup_project(client)
    quote_id = confirm_manual(client, project_id, supplier_ids[0])
    other_project_id, other_suppliers = setup_project(client)
    other_quote_id = confirm_manual(client, other_project_id, other_suppliers[0])
    runtime = _analyst_runtime(
        engine, project_id, supplier_ids,
        [quote_id, other_quote_id],
    )
    with Session(engine) as session:
        with pytest.raises(ToolError) as error:
            get_quote_evidence(session, runtime, UUID(other_quote_id), "unit_price")
        assert error.value.code == ToolErrorCode.NOT_ALLOWED
    with TestClient(app, raise_server_exceptions=False) as other_client:
        assert other_client.post("/demo-session").status_code == 204
        foreign_project_id, foreign_suppliers = setup_project(other_client)
        foreign_quote_id = confirm_manual(other_client, foreign_project_id,
                                          foreign_suppliers[0])
    foreign_runtime = _analyst_runtime(
        engine, foreign_project_id, foreign_suppliers, [foreign_quote_id],
    )
    misplaced = AnalystToolRuntime(AnalystToolContext(
        demo_session_id=foreign_runtime.context.demo_session_id,
        project_id=UUID(project_id),
        permitted_supplier_ids=runtime.context.permitted_supplier_ids,
        permitted_quote_ids=runtime.context.permitted_quote_ids,
    ))
    with Session(engine) as session:
        for call in (
            lambda: get_comparison_snapshot(session, misplaced),
            lambda: get_quote_evidence(session, misplaced, UUID(quote_id), "unit_price"),
        ):
            with pytest.raises(ToolError) as error:
                call()
            assert error.value.code == ToolErrorCode.NOT_ALLOWED


def test_completeness_classifies_selected_missing_and_conflict() -> None:
    selected = resolve_sources("moq", general_facts=(
        SourceFact("moq", 500, FactContext.GENERAL_SUPPLIER, "supplier:moq"),
    ))
    missing = resolve_sources("delivery_date")
    conflict = resolve_sources("moq", project_facts=(
        SourceFact("moq", 500, FactContext.PROJECT_QUOTE, "quote:moq",
                   has_same_context_conflict=True),
    ))
    assert [_resolution_state(item) for item in (selected, missing, conflict)] == [
        "known", "missing", "conflicting",
    ]


def test_origin_change_changes_input_fingerprint_without_revision_change() -> None:
    quote = Quote(project_id=uuid4(), supplier_id=uuid4(), entry_type="PDF",
                  status="CONFIRMED", revision=0)
    value = QuoteValue(field_key="unit_price", current_value="4.50",
                       ai_extracted_value="4.50", current_origin="AI_EXTRACTED")
    quote.values.append(value)
    original = _quote_fingerprint(quote)
    value.current_origin = "USER_CORRECTED"
    assert quote.revision == 0
    assert _quote_fingerprint(quote) != original


def test_snapshot_assembles_warnings_and_structured_completeness(client: TestClient) -> None:
    project_id, supplier_ids = setup_project(client)
    confirm_manual(client, project_id, supplier_ids[0])
    confirm_manual(client, project_id, supplier_ids[1], quantity=2500, currency="EUR")
    generated = client.post(f"/projects/{project_id}/comparison/generate")
    assert generated.status_code == 201, generated.text
    suppliers = generated.json()["comparison_payload"]["suppliers"]
    assert len(suppliers) == 2
    mismatched = next(item for item in suppliers if item["supplier_id"] == supplier_ids[1])
    warning_codes = {item["code"] for item in mismatched["evaluation"]["warnings"]}
    assert {"MIXED_QUOTE_CURRENCIES", "QUANTITY_MISMATCH"} <= warning_codes
    completeness = {item["field_key"]: item for item in mismatched["completeness"]}
    assert completeness["currency"]["state"] == "known"
    assert completeness["delivery_date"]["state"] == "missing"
    assert completeness["shipping_cost"]["state"] == "missing"
    assert completeness["unit_price"]["state"] == "known"
    assert all(isinstance(item["source_references"], list) for item in completeness.values())


def test_changed_shortlist_requires_renewed_approval(client: TestClient, engine: Engine) -> None:
    project_id, supplier_ids = setup_project(client)
    comparison_route = f"/projects/{project_id}/comparison"
    route = f"{comparison_route}/generate"
    confirm_manual(client, project_id, supplier_ids[0])
    confirm_manual(client, project_id, supplier_ids[1])
    first = client.post(route)
    assert first.status_code == 201, first.text
    assert first.json()["stale"] is False

    changed = client.patch(f"/projects/{project_id}/suppliers/{supplier_ids[2]}",
                           json={"shortlisted": False})
    assert changed.status_code == 200, changed.text
    assert changed.json()["shortlist_approved"] is False
    stale = client.get(comparison_route)
    assert stale.status_code == 200, stale.text
    assert stale.json()["id"] == first.json()["id"]
    assert stale.json()["quote_revision_snapshot"] == first.json()["quote_revision_snapshot"]
    assert stale.json()["stale"] is True
    with Session(engine) as session:
        snapshot = session.get(Comparison, UUID(first.json()["id"]))
        assert snapshot is not None
        assert snapshot.stale is False
    rejected = client.post(route)
    assert rejected.status_code == 409
    assert "shortlist" in rejected.text.lower()

    approved = client.post(f"/projects/{project_id}/shortlist/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["shortlist_approved"] is True
    current = client.get(comparison_route)
    assert current.status_code == 200, current.text
    assert current.json() == first.json()
    regenerated = client.post(route)
    assert regenerated.status_code == 201, regenerated.text
    assert regenerated.json()["id"] != first.json()["id"]


def test_pdf_evidence_links_to_document_blocks_without_copying_text(
    client: TestClient, engine: Engine,
) -> None:
    project_id, supplier_ids = setup_project(client)
    pdf_quote_id = confirm_manual(client, project_id, supplier_ids[0])
    confirm_manual(client, project_id, supplier_ids[1])
    block_id = uuid4()
    evidence_id = uuid4()
    with Session(engine) as session:
        quote = session.get(Quote, UUID(pdf_quote_id))
        assert quote is not None
        quote.entry_type = "PDF"
        document = QuoteDocument(
            quote_id=quote.id, storage_key=f"test/{uuid4()}", original_filename="quote.pdf",
            sha256="0" * 64, page_count=2, processing_status="CONFIRMED", is_active=True,
        )
        session.add(document)
        session.flush()
        session.add(DocumentBlock(
            id=block_id, quote_document_id=document.id, page_number=2, block_number=3,
            text="Original PDF text must stay in DocumentBlock.",
        ))
        price = next(value for value in quote.values if value.field_key == "unit_price")
        session.delete(price)
        session.flush()
        price = QuoteValue(
            quote_id=quote.id, field_key="unit_price", current_value="4.25",
            current_origin="AI_EXTRACTED", ai_extracted_value="4.25",
        )
        session.add(price)
        session.flush()
        price.current_value = "4.50"
        price.current_origin = "USER_CORRECTED"
        price.evidence.append(QuoteFieldEvidence(
            id=evidence_id, document_block_id=block_id, evidence_value="4.25",
        ))
        document_id = document.id
        session.commit()

    generated = client.post(f"/projects/{project_id}/comparison/generate")
    assert generated.status_code == 201, generated.text
    payload = generated.json()["comparison_payload"]
    pdf_supplier = next(item for item in payload["suppliers"]
                        if item["supplier_id"] == supplier_ids[0])
    price_field = next(item for item in pdf_supplier["quote_fields"]
                       if item["field_key"] == "unit_price")
    assert price_field["current_value"] == "4.50"
    assert price_field["origin"] == "USER_CORRECTED"
    assert price_field["ai_extracted_value"] == "4.25"
    assert price_field["evidence"] == [{
        "id": str(evidence_id), "value": "4.25", "role": "provenance",
        "document_block_id": str(block_id), "quote_document_id": str(document_id),
        "page_number": 2, "block_number": 3,
    }]
    assert str(evidence_id) in str(pdf_supplier["resolved_facts"]["unit_price"])
    assert "Original PDF text" not in str(payload)
    runtime = _analyst_runtime(engine, project_id, supplier_ids, [pdf_quote_id])
    with Session(engine) as session:
        evidence = get_quote_evidence(session, runtime, UUID(pdf_quote_id), "unit_price")
        assert evidence.current_value == "4.50"
        assert evidence.current_origin == "USER_CORRECTED"
        assert evidence.ai_extracted_value == "4.25"
        assert len(evidence.evidence) == 1
        citation = evidence.evidence[0]
        assert citation.id == evidence_id
        assert citation.quote_document_id == document_id
        assert citation.document_block_id == block_id
        assert citation.page_number == 2 and citation.block_number == 3
        assert citation.untrusted_source_text == "Original PDF text must stay in DocumentBlock."
        assert citation.evidence_value == "4.25"
        assert citation.role == "provenance"
    with Session(engine) as session:
        quote = session.get(Quote, UUID(pdf_quote_id))
        assert quote is not None
        value = next(item for item in quote.values if item.field_key == "unit_price")
        inactive = QuoteDocument(
            quote_id=quote.id, storage_key=f"test/{uuid4()}",
            original_filename="old.pdf", sha256="1" * 64, page_count=1,
            processing_status="CONFIRMED", is_active=False,
        )
        session.add(inactive)
        session.flush()
        other_block = DocumentBlock(
            id=uuid4(), quote_document_id=inactive.id,
            page_number=1, block_number=1, text="Old document value.",
        )
        session.add(other_block)
        session.flush()
        value.evidence.append(QuoteFieldEvidence(
            document_block_id=other_block.id, evidence_value="9.99",
        ))
        session.commit()
    with Session(engine) as session:
        scoped = get_quote_evidence(session, runtime, UUID(pdf_quote_id), "unit_price")
        assert [item.id for item in scoped.evidence] == [evidence_id]
    manual_supplier = next(item for item in payload["suppliers"]
                           if item["supplier_id"] == supplier_ids[1])
    assert all(not field["evidence"] for field in manual_supplier["quote_fields"])


def test_generate_stale_and_regenerate(client: TestClient, engine: Engine) -> None:
    project_id, supplier_ids = setup_project(client)
    route = f"/projects/{project_id}/comparison"
    assert client.get(route).status_code == 404
    assert client.post(f"{route}/generate").status_code == 409
    assert client.get(route).status_code == 404
    first_quote = confirm_manual(client, project_id, supplier_ids[0])
    assert client.post(f"{route}/generate").status_code == 409
    second_quote = confirm_manual(client, project_id, supplier_ids[1], "4.50")
    created = client.post(f"{route}/generate")
    assert created.status_code == 201, created.text
    first = created.json()
    assert not first["stale"]
    assert set(first["quote_revision_snapshot"]) == set(supplier_ids[:2])
    assert first["quote_revision_snapshot"][supplier_ids[0]]["quote_id"] == first_quote
    assert first["quote_revision_snapshot"][supplier_ids[1]]["quote_id"] == second_quote
    assert all(item["revision"] == 0 and len(item["facts_fingerprint"]) == 64
               for item in first["quote_revision_snapshot"].values())
    assert len(first["comparison_payload"]["suppliers"]) == 2
    assert all(item["state"] in {"known", "missing", "conflicting"}
               for supplier in first["comparison_payload"]["suppliers"]
               for item in supplier["completeness"])
    assert all("score" not in supplier and "percentage" not in supplier
               for supplier in first["comparison_payload"]["suppliers"])
    assert client.get(route).json() == first
    assert client.patch(f"/projects/{project_id}/suppliers/{supplier_ids[2]}",
                        json={"shortlisted": False}).status_code == 200
    assert client.get(route).json()["stale"]
    assert client.post(f"{route}/generate").status_code == 409
    assert client.post(f"/projects/{project_id}/shortlist/approve").status_code == 200
    assert not client.get(route).json()["stale"]
    unchanged_quote = client.patch(f"/quotes/{first_quote}", json={
        "values": {"unit_price": "4.2500"}, "notes": "Reviewed",
    })
    assert unchanged_quote.status_code == 200, unchanged_quote.text
    assert unchanged_quote.json()["revision"] == 0
    assert not client.get(route).json()["stale"]

    unchanged = client.post(f"{route}/generate")
    assert unchanged.status_code == 201, unchanged.text
    assert unchanged.json()["comparison_payload"] == first["comparison_payload"]
    assert unchanged.json()["id"] != first["id"]

    changed = client.patch(f"/quotes/{first_quote}", json={"values": {"unit_price": "5.00"}})
    assert changed.status_code == 200, changed.text
    assert changed.json()["revision"] == 1
    assert client.get(route).json()["stale"]
    refreshed = client.post(f"{route}/generate")
    assert refreshed.status_code == 201, refreshed.text
    latest = refreshed.json()
    assert not latest["stale"]
    assert latest["quote_revision_snapshot"][supplier_ids[0]]["revision"] == 1
    quote = next(item for item in latest["comparison_payload"]["suppliers"]
                 if item["supplier_id"] == supplier_ids[0])
    assert next(item for item in quote["quote_fields"]
                if item["field_key"] == "unit_price")["current_value"] == "5.00"
    with Session(engine) as session:
        history = session.scalars(select(Comparison).where(
            Comparison.project_id == UUID(project_id)
        )).all()
        assert len(history) == 3
        assert sum(not item.stale for item in history) == 1


def test_quote_set_brief_and_defensive_read_staleness(client: TestClient, engine: Engine) -> None:
    project_id, supplier_ids = setup_project(client)
    route = f"/projects/{project_id}/comparison"
    first = confirm_manual(client, project_id, supplier_ids[0])
    confirm_manual(client, project_id, supplier_ids[1])
    original = client.post(f"{route}/generate").json()
    third = confirm_manual(client, project_id, supplier_ids[2])
    assert client.get(route).json()["stale"]
    added = client.post(f"{route}/generate").json()
    assert not added["stale"] and len(added["quote_revision_snapshot"]) == 3
    assert added["quote_revision_snapshot"][supplier_ids[2]]["quote_id"] == third

    with Session(engine) as session:
        latest = session.get(Comparison, UUID(added["id"]))
        assert latest is not None
        quote = session.get(Quote, UUID(first))
        assert quote is not None
        quote.revision += 1
        session.commit()
        assert latest.stale is False
    assert client.get(route).json()["stale"]
    assert client.post(f"{route}/generate").json()["stale"] is False

    brief = client.get(f"/projects/{project_id}/brief").json()
    edited = client.patch(f"/projects/{project_id}/brief", json={
        "expected_brief_revision": brief["brief_revision"],
        "product_name": brief["product_name"], "category": brief["category"],
        "quantity": 2500, "destination": brief["destination"],
        "delivery_target": brief["delivery_target"],
        "target_unit_price": brief["target_unit_price"],
        "requirements": brief["requirements"],
    })
    assert edited.status_code == 200, edited.text
    assert client.get(route).json()["stale"]
    assert client.post(f"{route}/generate").status_code == 409
    assert client.post(f"/projects/{project_id}/shortlist/approve").status_code == 409
    assert client.post(f"/projects/{project_id}/suppliers/discover").status_code == 200
    assert client.post(f"/projects/{project_id}/shortlist/approve").status_code == 200
    refreshed = client.post(f"{route}/generate")
    assert refreshed.status_code == 201, refreshed.text
    assert not refreshed.json()["stale"]
    assert refreshed.json()["brief_revision"] == edited.json()["brief_revision"]
    assert original["id"] != added["id"]


def test_session_isolation(client: TestClient, engine: Engine) -> None:
    project_id, supplier_ids = setup_project(client)
    confirm_manual(client, project_id, supplier_ids[0])
    confirm_manual(client, project_id, supplier_ids[1])
    assert client.post(f"/projects/{project_id}/comparison/generate").status_code == 201
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_database_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_database_session] = override_database_session
    with TestClient(app, raise_server_exceptions=False) as other:
        assert other.post("/demo-session").status_code == 204
        assert other.get(f"/projects/{project_id}/comparison").status_code == 404
        assert other.post(f"/projects/{project_id}/comparison/generate").status_code == 404


def test_quote_removal_and_replacement_change_active_identity(client: TestClient,
                                                               engine: Engine) -> None:
    project_id, supplier_ids = setup_project(client)
    route = f"/projects/{project_id}/comparison"
    first = confirm_manual(client, project_id, supplier_ids[0])
    confirm_manual(client, project_id, supplier_ids[1])
    confirm_manual(client, project_id, supplier_ids[2])
    initial = client.post(f"{route}/generate").json()

    removed = client.patch(f"/projects/{project_id}/suppliers/{supplier_ids[2]}",
                           json={"shortlisted": False})
    assert removed.status_code == 200, removed.text
    assert client.get(route).json()["stale"]
    assert client.post(f"{route}/generate").status_code == 409
    assert client.post(f"/projects/{project_id}/shortlist/approve").status_code == 200
    without_third = client.post(f"{route}/generate")
    assert without_third.status_code == 201, without_third.text
    assert supplier_ids[2] not in without_third.json()["quote_revision_snapshot"]

    with Session(engine) as session:
        old = session.get(Quote, UUID(first))
        assert old is not None
        session.delete(old)
        session.flush()
        replacement = Quote(
            project_id=UUID(project_id), supplier_id=UUID(supplier_ids[0]),
            entry_type="MANUAL", status="CONFIRMED", revision=0,
        )
        replacement.values.append(QuoteValue(
            field_key="quoted_quantity", current_value=2000, current_origin="USER_ENTERED",
        ))
        session.add(replacement)
        session.commit()
        replacement_id = str(replacement.id)
    assert client.get(route).json()["stale"]
    regenerated = client.post(f"{route}/generate")
    assert regenerated.status_code == 201, regenerated.text
    replacement_input = regenerated.json()["quote_revision_snapshot"][supplier_ids[0]]
    assert replacement_input["quote_id"] == replacement_id
    assert replacement_input["revision"] == 0
    assert initial["quote_revision_snapshot"][supplier_ids[0]]["quote_id"] != replacement_id


def test_generation_rollback_leaves_no_partial_snapshot(client: TestClient, engine: Engine) -> None:
    project_id, supplier_ids = setup_project(client)
    confirm_manual(client, project_id, supplier_ids[0])
    confirm_manual(client, project_id, supplier_ids[1])
    with Session(engine) as session:
        generated = generate_comparison(session, UUID(project_id))
        assert generated.id is not None
        session.rollback()
    assert client.get(f"/projects/{project_id}/comparison").status_code == 404
