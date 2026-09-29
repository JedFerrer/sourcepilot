"""Comparison generation, staleness, persistence, and API isolation."""

from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

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
    DocumentBlock,
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
