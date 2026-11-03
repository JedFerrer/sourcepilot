"""PDF upload validation, ownership, and storage lifecycle tests."""

from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier, Event, Lock
from typing import Any, Self
from unittest.mock import Mock
from uuid import UUID, uuid4

import pymupdf
import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from sourcepilot.ai.client import AnalystModelInvocation, ModelInvocation, ModelProviderError
from sourcepilot.ai.quote_extraction_eval import load_recorded_outputs
from sourcepilot.ai.quote_extractor import QuoteExtraction
from sourcepilot.documents.body_limit import UploadBodyLimitMiddleware
from sourcepilot.documents.inspect_pdf import PdfInspectionTimeoutError
from sourcepilot.documents.lifecycle import effective_processing_status
from sourcepilot.documents.parse_pdf import ParsedBlock
from sourcepilot.documents.parse_service import parse_and_persist_document
from sourcepilot.documents.processing import _finish_success, process_pdf_quote
from sourcepilot.documents.service import (
    PdfCommitUncertainError,
    PdfUploadError,
    stage_pdf_upload,
    store_pdf_quote,
)
from sourcepilot.documents.settings import (
    MULTIPART_OVERHEAD_BYTES,
    document_settings_from_environment,
)
from sourcepilot.documents.storage import (
    LocalDocumentStorage,
    S3DocumentStorage,
    new_storage_key,
)
from sourcepilot.main import app, get_document_storage
from sourcepilot.persistence.database import get_database_session
from sourcepilot.persistence.models import (
    AIRun,
    DocumentBlock,
    Project,
    Quote,
    QuoteDocument,
    QuoteFieldEvidence,
    QuoteValue,
    SupplierExplanationRunStep,
)
from sourcepilot.quotes.service import QuoteWorkflowError, create_manual_quote
from sourcepilot.suppliers.seed import seed_suppliers
from tests.database_test_support import (
    create_test_engine,
    persistence_test_database_url_from_environment,
    reset_test_database,
)
from tests.test_manual_quotes import setup_shortlist

FIXTURE_PDFS = Path(__file__).parent / "fixtures" / "quote_pdfs"


class RecordedClient:
    model = "recorded-model"

    def __init__(self, case: str) -> None:
        self.case = case

    def invoke(self, **kwargs: object) -> ModelInvocation:
        return ModelInvocation(json.dumps(load_recorded_outputs()[self.case]), 1, 1)

    def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
        raise AssertionError("The quote extractor must not use tools.")


class FailedClient(RecordedClient):
    def invoke(self, **kwargs: object) -> ModelInvocation:
        raise ModelProviderError("private provider detail", retryable=False)


class AllUnknownClient(RecordedClient):
    def invoke(self, **kwargs: object) -> ModelInvocation:
        fields = load_recorded_outputs()["harbor-primary"]["fields"]
        unknown = {key: {
            "state": "UNKNOWN", "extracted_value": None, "source_block_ids": [],
            "uncertainty": None, "conflicting_values": [],
        } for key in fields}
        return ModelInvocation(json.dumps({"fields": unknown}), 1, 1)


@pytest.fixture(scope="module")
def database_url() -> str:
    return persistence_test_database_url_from_environment()


@pytest.fixture(scope="module")
def engine(database_url: str) -> Iterator[Engine]:
    test_engine = create_test_engine(database_url)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def client(engine: Engine, database_url: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    reset_test_database(database_url)
    with Session(engine) as session:
        seed_suppliers(session)
        session.commit()
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_database_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_database_session] = override_database_session
    monkeypatch.setattr("sourcepilot.main.run_pdf_quote_processing", lambda document_id, attempt: None)
    with TestClient(app, raise_server_exceptions=False) as value:
        assert value.post("/demo-session").status_code == 204
        yield value
    app.dependency_overrides.clear()
    reset_test_database(database_url)


def pdf_bytes(pages: int = 1) -> bytes:
    document = pymupdf.open()
    for _ in range(pages):
        document.new_page()
    result = document.tobytes()
    document.close()
    return result


@pytest.fixture
def storage_client(client: TestClient, tmp_path: Path) -> tuple[TestClient, LocalDocumentStorage]:
    storage = LocalDocumentStorage(tmp_path / "stored")
    app.dependency_overrides[get_document_storage] = lambda: storage
    return client, storage


def upload(client: TestClient, project_id: str, supplier_id: str, data: bytes,
           filename: str = "quote.pdf"):
    return client.post(
        f"/projects/{project_id}/quotes/upload",
        data={"supplier_id": supplier_id},
        files={"file": (filename, data, "application/pdf")},
    )


def test_upload_creates_unconfirmed_pdf_metadata_without_exposing_storage_key(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    original = pdf_bytes()
    response = upload(api, project_id, supplier_id, original, "../supplier.pdf")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["quote"]["entry_type"] == "PDF"
    assert body["quote"]["status"] == "PROCESSING"
    assert body["quote"]["revision"] == 0
    assert body["quote"]["confirmed_at"] is None
    assert body["quote"]["values"] == {}
    assert body["document"]["processing_status"] == "PROCESSING"
    assert body["document"]["processing_attempts"] == 1
    assert body["document"]["processing_started_at"] is not None
    assert body["document"]["processing_completed_at"] is None
    assert body["document"]["last_error"] is None
    assert body["document"]["page_count"] == 1
    assert body["document"]["sha256"] == hashlib.sha256(original).hexdigest()
    assert "storage_key" not in response.text
    assert str(storage.root) not in response.text
    assert next(iter(storage.root.rglob("*.pdf"))).read_bytes() == original
    quote_id = body["quote"]["id"]
    assert api.post(f"/quotes/{quote_id}/confirm").status_code == 409
    assert api.get(f"/quotes/{quote_id}").json()["status"] == "PROCESSING"
    with Session(engine) as database_session:
        stored = database_session.scalars(select(QuoteDocument)).one()
        assert stored.quote_id == UUID(quote_id)
        assert stored.original_filename == "supplier.pdf"
        assert stored.sha256 == hashlib.sha256(original).hexdigest()
        assert stored.processing_attempts == 1
        assert stored.processing_started_at is not None
        assert stored.processing_completed_at is None
        assert stored.last_error is None


def test_upload_schedules_only_after_processing_metadata_is_committed(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, _ = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    observed: list[UUID] = []

    def scheduled(document_id: UUID, attempt: int) -> None:
        with Session(engine) as session:
            document = session.get(QuoteDocument, document_id)
            assert document is not None
            assert document.processing_status == "PROCESSING"
            assert document.processing_attempts == 1
            assert attempt == 1
            assert document.processing_started_at is not None
            assert document.processing_completed_at is None
            observed.append(document_id)

    monkeypatch.setattr("sourcepilot.main.run_pdf_quote_processing", scheduled)
    monkeypatch.setattr("sourcepilot.documents.processing.parse_and_persist_document",
                        lambda *args, **kwargs: pytest.fail("Parsing ran inline"))
    response = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "harbor_primary.pdf").read_bytes())
    assert response.status_code == 201
    assert observed == [UUID(response.json()["document"]["id"])]
    assert api.get(f"/quotes/{response.json()['quote']['id']}").json()["processing"] == {
        "status": "PROCESSING", "attempts": 1,
        "started_at": response.json()["document"]["processing_started_at"],
        "completed_at": None, "failure": None,
    }


def test_background_success_persists_unconfirmed_draft_and_completion(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    response = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "harbor_primary.pdf").read_bytes())
    assert response.status_code == 201
    document_id = UUID(response.json()["document"]["id"])
    quote_id = UUID(response.json()["quote"]["id"])
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    process_pdf_quote(document_id, 1, session_factory=factory, storage=storage,
        settings=document_settings_from_environment(),
        client_factory=lambda: RecordedClient("harbor-primary"),
    )
    with Session(engine) as session:
        document = session.get(QuoteDocument, document_id)
        quote = session.get(Quote, quote_id)
        assert document is not None and quote is not None
        assert document.processing_status == quote.status == "NEEDS_REVIEW"
        assert document.processing_completed_at is not None
        assert document.processing_started_at is not None
        assert document.processing_completed_at >= document.processing_started_at
        assert quote.confirmed_at is None
        assert len(quote.values) == len(load_recorded_outputs()["harbor-primary"]["fields"])
        assert next(value for value in quote.values if value.field_key == "unit_price").current_value == "4.60"
    poll = api.get(f"/quotes/{quote_id}")
    assert poll.status_code == 200
    assert poll.json()["processing"]["status"] == "NEEDS_REVIEW"
    assert poll.json()["processing"]["completed_at"] is not None


def test_background_failure_keeps_pdf_and_null_draft(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    response = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "image_only.pdf").read_bytes())
    assert response.status_code == 201
    document_id = UUID(response.json()["document"]["id"])
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    process_pdf_quote(document_id, 1, session_factory=factory, storage=storage,
        settings=document_settings_from_environment(),
        client_factory=lambda: pytest.fail("Model called for image-only PDF"),
    )
    with Session(engine) as session:
        document = session.get(QuoteDocument, document_id)
        assert document is not None
        assert document.processing_status == document.quote.status == "FAILED"
        assert document.processing_completed_at is not None
        assert document.last_error == "PROCESSING_FAILED"
        assert session.scalar(select(QuoteValue).where(QuoteValue.quote_id == document.quote_id)) is None
        assert storage.root.joinpath(document.storage_key).exists()
    assert api.patch(f"/quotes/{response.json()['quote']['id']}", json={
        "values": {"unit_price": "4.50"},
    }).status_code == 409


def test_extractor_failure_retains_blocks_and_exposes_only_safe_failure(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    response = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "harbor_primary.pdf").read_bytes())
    document_id = UUID(response.json()["document"]["id"])
    quote_id = response.json()["quote"]["id"]
    process_pdf_quote(document_id, 1, session_factory=sessionmaker(bind=engine, expire_on_commit=False),
        storage=storage, settings=document_settings_from_environment(),
        client_factory=lambda: FailedClient("harbor-primary"),
    )
    with Session(engine) as session:
        document = session.get(QuoteDocument, document_id)
        assert document is not None
        assert document.processing_status == "FAILED"
        assert document.processing_completed_at is not None
        assert session.scalar(select(DocumentBlock).where(DocumentBlock.quote_document_id == document_id)) is not None
        assert session.scalar(select(QuoteValue).where(QuoteValue.quote_id == document.quote_id)) is None
    poll = api.get(f"/quotes/{quote_id}")
    assert poll.status_code == 200
    assert poll.json()["processing"]["failure"] == "PROCESSING_FAILED"
    assert "private provider detail" not in poll.text
    with TestClient(app, raise_server_exceptions=False) as stranger:
        assert stranger.post("/demo-session").status_code == 204
        assert stranger.get(f"/quotes/{quote_id}").status_code == 404


def test_changed_attempt_is_not_finalized(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    response = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "harbor_primary.pdf").read_bytes())
    document_id = UUID(response.json()["document"]["id"])
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    original = __import__("sourcepilot.documents.processing", fromlist=["parse_and_persist_document"])

    def changed_attempt(*args: object, **kwargs: object) -> None:
        with factory() as session, session.begin():
            document = session.get(QuoteDocument, document_id)
            assert document is not None
            document.processing_attempts = 2
        original.parse_and_persist_document(*args, **kwargs)

    monkeypatch.setattr("sourcepilot.documents.processing.parse_and_persist_document", changed_attempt)
    process_pdf_quote(document_id, 1, session_factory=factory, storage=storage,
        settings=document_settings_from_environment(),
        client_factory=lambda: RecordedClient("harbor-primary"),
    )
    with Session(engine) as session:
        document = session.get(QuoteDocument, document_id)
        assert document is not None
        assert document.processing_status == "PROCESSING"
        assert document.processing_completed_at is None
        assert session.scalar(select(QuoteValue).where(QuoteValue.quote_id == document.quote_id)) is None


@pytest.mark.parametrize(("filename", "case", "field_key"), [
    ("missing_shipping.pdf", "missing-shipping", "shipping_cost"),
    ("conflicting_lead_time.pdf", "conflicting-lead-time", "production_lead_time"),
])
def test_unknown_and_conflicting_fields_do_not_select_a_value(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
    filename: str, case: str, field_key: str,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    response = upload(api, project_id, supplier_id, (FIXTURE_PDFS / filename).read_bytes())
    document_id = UUID(response.json()["document"]["id"])
    process_pdf_quote(document_id, 1, session_factory=sessionmaker(bind=engine, expire_on_commit=False),
        storage=storage, settings=document_settings_from_environment(),
        client_factory=lambda: RecordedClient(case),
    )
    with Session(engine) as session:
        document = session.get(QuoteDocument, document_id)
        assert document is not None
        assert document.processing_status == "NEEDS_REVIEW"
        field = next(value for value in document.quote.values if value.field_key == field_key)
        assert field.current_value is None
        assert field.ai_extracted_value is None
        if case == "conflicting-lead-time":
            assert field.uncertainty is not None


def test_pdf_correction_retains_source_and_has_deterministic_origins(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    uploaded = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "missing_shipping.pdf").read_bytes())
    assert uploaded.status_code == 201
    quote_id = uploaded.json()["quote"]["id"]
    document_id = UUID(uploaded.json()["document"]["id"])
    assert api.patch(f"/quotes/{quote_id}", json={"values": {"unit_price": "4.50"}}).status_code == 409
    process_pdf_quote(document_id, 1, session_factory=sessionmaker(bind=engine, expire_on_commit=False),
        storage=storage, settings=document_settings_from_environment(),
        client_factory=lambda: RecordedClient("missing-shipping"),
    )
    original = api.get(f"/quotes/{quote_id}").json()
    price = original["values"]["unit_price"]
    assert price["ai_extracted_value"] == price["current_value"] == "4.60"
    assert price["current_origin"] == "AI_EXTRACTED"
    assert price["evidence"][0]["block_id"] == "p1-b5"
    assert "4.60" in price["evidence"][0]["block_text"]
    assert price["evidence"][0]["evidence_value"] == "4.60"
    assert original["values"]["shipping_cost"]["ai_extracted_value"] is None
    assert original["values"]["shipping_cost"]["review_state"] == "UNKNOWN"
    original_evidence = price["evidence"]

    corrected = api.patch(f"/quotes/{quote_id}", json={
        "values": {"unit_price": "4.50", "shipping_cost": "12.00"},
        "notes": "Draft correction",
    })
    assert corrected.status_code == 200, corrected.text
    values = corrected.json()["values"]
    assert values["unit_price"]["current_value"] == "4.50"
    assert values["unit_price"]["current_origin"] == "USER_CORRECTED"
    assert values["unit_price"]["ai_extracted_value"] == "4.60"
    assert values["unit_price"]["evidence"] == original_evidence
    assert values["shipping_cost"]["current_value"] == "12.00"
    assert values["shipping_cost"]["current_origin"] == "USER_CORRECTED"
    assert values["shipping_cost"]["evidence"] == []
    assert corrected.json()["revision"] == 0
    assert corrected.json()["status"] == "NEEDS_REVIEW"
    # Confirmation is exercised after draft correction checks below.

    cleared = api.patch(f"/quotes/{quote_id}", json={"values": {"unit_price": None}})
    assert cleared.status_code == 200
    assert cleared.json()["values"]["unit_price"]["current_value"] is None
    assert cleared.json()["values"]["unit_price"]["current_origin"] == "USER_CORRECTED"
    restored = api.patch(f"/quotes/{quote_id}", json={"values": {"unit_price": "4.60"}})
    assert restored.status_code == 200
    assert restored.json()["values"]["unit_price"]["current_origin"] == "AI_EXTRACTED"
    assert restored.json()["values"]["unit_price"]["evidence"] == original_evidence
    assert restored.json()["values"]["shipping_cost"]["current_origin"] == "USER_CORRECTED"
    assert api.patch(f"/quotes/{quote_id}", json={"values": {"moq": 0}}).status_code == 422
    with TestClient(app, raise_server_exceptions=False) as stranger:
        assert stranger.post("/demo-session").status_code == 204
        assert stranger.patch(f"/quotes/{quote_id}", json={"values": {}}).status_code == 404


def test_conflict_alternatives_keep_citations_with_null_current(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    uploaded = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "conflicting_lead_time.pdf").read_bytes())
    document_id = UUID(uploaded.json()["document"]["id"])
    process_pdf_quote(document_id, 1, session_factory=sessionmaker(bind=engine, expire_on_commit=False),
        storage=storage, settings=document_settings_from_environment(),
        client_factory=lambda: RecordedClient("conflicting-lead-time"),
    )
    field = api.get(f"/quotes/{uploaded.json()['quote']['id']}").json()["values"]["production_lead_time"]
    assert field["current_value"] is None
    assert field["ai_extracted_value"] is None
    assert field["current_origin"] == "AI_EXTRACTED"
    assert field["review_state"] == "CONFLICT"
    assert field["uncertainty"]
    alternatives = field["conflicting_values"]
    assert {alternative["value"] for alternative in alternatives} == {
        "25 days after sample approval", "30-35 days after sample approval",
    }
    assert {source["block_id"] for alternative in alternatives
            for source in alternative["evidence"]} == {"p1-b10", "p2-b3"}
    assert all(source["evidence_value"] == alternative["value"]
               for alternative in alternatives for source in alternative["evidence"])
    with Session(engine) as session:
        assert all(association.block.quote_document_id == document_id
                   for association in session.scalars(select(QuoteFieldEvidence)).all())


def test_cross_document_citation_rejected_before_any_draft_is_written(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
) -> None:
    api, storage = storage_client
    project_id, first_supplier, second_supplier = setup_shortlist(
        api, approve_shortlist=False,
    )
    assert api.patch(
        f"/projects/{project_id}/suppliers/{second_supplier}",
        json={"shortlisted": True},
    ).status_code == 200
    assert api.post(f"/projects/{project_id}/shortlist/approve").status_code == 200
    first = upload(api, project_id, first_supplier,
                   (FIXTURE_PDFS / "harbor_primary.pdf").read_bytes())
    second = upload(api, project_id, second_supplier, pdf_bytes())
    assert first.status_code == second.status_code == 201
    first_document = UUID(first.json()["document"]["id"])
    second_document = UUID(second.json()["document"]["id"])
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    parse_and_persist_document(
        factory, first_document, storage=storage,
        settings=document_settings_from_environment(),
    )
    with Session(engine) as session, session.begin():
        session.add(DocumentBlock(
            id=uuid4(), quote_document_id=second_document,
            page_number=99, block_number=99, text="Other quote only",
        ))
    extraction = QuoteExtraction.model_validate(load_recorded_outputs()["harbor-primary"])
    extraction.fields.unit_price.source_block_ids = ["p99-b99"]
    with pytest.raises(ValueError, match="outside the quote document"):
        _finish_success(factory, first_document, 1, extraction)
    with Session(engine) as session:
        document = session.get(QuoteDocument, first_document)
        assert document is not None
        assert document.evidence_capture_version is None
        quote = document.quote
        assert quote.status == "PROCESSING"
        assert session.scalar(select(QuoteValue).where(QuoteValue.quote_id == quote.id)) is None
        assert session.scalar(select(QuoteFieldEvidence)) is None


def test_older_pdf_draft_without_associations_reports_indeterminate_null_fields(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    uploaded = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "conflicting_lead_time.pdf").read_bytes())
    document_id = UUID(uploaded.json()["document"]["id"])
    process_pdf_quote(document_id, 1, session_factory=sessionmaker(bind=engine, expire_on_commit=False),
        storage=storage, settings=document_settings_from_environment(),
        client_factory=lambda: RecordedClient("conflicting-lead-time"),
    )
    with Session(engine) as session, session.begin():
        session.execute(delete(QuoteFieldEvidence))
        document = session.get(QuoteDocument, document_id)
        assert document is not None
        document.evidence_capture_version = None
    quote_id = uploaded.json()["quote"]["id"]
    for response in (api.get(f"/quotes/{quote_id}"), api.get(f"/projects/{project_id}/quotes")):
        assert response.status_code == 200
        values = (response.json()["values"] if isinstance(response.json(), dict)
                  else response.json()[0]["values"])
        known = values["unit_price"]
        assert known["ai_extracted_value"] is not None
        assert known["review_state"] == "KNOWN"
        ambiguous = values["production_lead_time"]
        assert ambiguous["ai_extracted_value"] is None
        assert ambiguous["review_state"] == "UNAVAILABLE"
        assert ambiguous["evidence"] == []
        assert ambiguous["conflicting_values"] == []


def test_legacy_pdf_evidence_on_one_field_does_not_classify_another(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    uploaded = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "missing_shipping.pdf").read_bytes())
    document_id = UUID(uploaded.json()["document"]["id"])
    process_pdf_quote(document_id, 1, session_factory=sessionmaker(bind=engine, expire_on_commit=False),
        storage=storage, settings=document_settings_from_environment(),
        client_factory=lambda: RecordedClient("missing-shipping"),
    )
    with Session(engine) as session, session.begin():
        document = session.get(QuoteDocument, document_id)
        assert document is not None
        document.evidence_capture_version = None
    for response in (api.get(f"/quotes/{uploaded.json()['quote']['id']}"),
                     api.get(f"/projects/{project_id}/quotes")):
        assert response.status_code == 200
        quote = response.json() if isinstance(response.json(), dict) else response.json()[0]
        known = quote["values"]["unit_price"]
        assert known["review_state"] == "KNOWN"
        assert known["evidence"]
        uncited = quote["values"]["shipping_cost"]
        assert uncited["ai_extracted_value"] is None
        assert uncited["evidence"] == []
        assert uncited["review_state"] == "UNAVAILABLE"


def test_new_all_unknown_pdf_without_citations_reports_unknown(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    uploaded = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "harbor_primary.pdf").read_bytes())
    assert uploaded.status_code == 201
    document_id = UUID(uploaded.json()["document"]["id"])
    process_pdf_quote(document_id, 1, session_factory=sessionmaker(bind=engine, expire_on_commit=False),
        storage=storage, settings=document_settings_from_environment(),
        client_factory=lambda: AllUnknownClient("harbor-primary"),
    )
    with Session(engine) as session:
        document = session.get(QuoteDocument, document_id)
        assert document is not None
        assert document.evidence_capture_version == 1
        assert session.scalar(select(QuoteFieldEvidence)) is None
    for response in (api.get(f"/quotes/{uploaded.json()['quote']['id']}"),
                     api.get(f"/projects/{project_id}/quotes")):
        assert response.status_code == 200
        quote = response.json() if isinstance(response.json(), dict) else response.json()[0]
        assert quote["status"] == "NEEDS_REVIEW"
        assert quote["values"]
        assert {field["review_state"] for field in quote["values"].values()} == {"UNKNOWN"}
        assert all(field["evidence"] == [] for field in quote["values"].values())


def test_quote_listing_batches_pdf_evidence_and_skips_manual_evidence_queries(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
) -> None:
    api, storage = storage_client
    project_id, first_supplier, second_supplier = setup_shortlist(api, approve_shortlist=False)
    assert api.patch(
        f"/projects/{project_id}/suppliers/{second_supplier}",
        json={"shortlisted": True},
    ).status_code == 200
    assert api.post(f"/projects/{project_id}/shortlist/approve").status_code == 200
    for supplier_id in (first_supplier, second_supplier):
        uploaded = upload(api, project_id, supplier_id,
                          (FIXTURE_PDFS / "harbor_primary.pdf").read_bytes())
        process_pdf_quote(UUID(uploaded.json()["document"]["id"]), 1, session_factory=sessionmaker(bind=engine, expire_on_commit=False),
            storage=storage, settings=document_settings_from_environment(),
            client_factory=lambda: RecordedClient("harbor-primary"),
        )

    statements: list[str] = []

    def record_query(_: object, __: object, statement: str, *args: object) -> None:
        if statement.lstrip().lower().startswith("select"):
            statements.append(statement.lower())

    event.listen(engine, "before_cursor_execute", record_query)
    try:
        response = api.get(f"/projects/{project_id}/quotes")
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert all(quote["values"]["unit_price"]["evidence"] for quote in response.json())
        assert sum("from quote_field_evidence" in query for query in statements) == 1
        assert sum("from document_blocks" in query for query in statements) == 1
    finally:
        event.remove(engine, "before_cursor_execute", record_query)


def test_draft_persistence_error_rolls_back_before_failed_completion(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    response = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "harbor_primary.pdf").read_bytes())
    document_id = UUID(response.json()["document"]["id"])

    def reject_draft(session: Session, *args: object) -> None:
        if any(isinstance(value, QuoteValue) for value in session.new):
            raise RuntimeError("test draft persistence error")

    event.listen(Session, "before_flush", reject_draft)
    try:
        process_pdf_quote(document_id, 1, session_factory=sessionmaker(bind=engine, expire_on_commit=False),
            storage=storage, settings=document_settings_from_environment(),
            client_factory=lambda: RecordedClient("harbor-primary"),
        )
    finally:
        event.remove(Session, "before_flush", reject_draft)
    with Session(engine) as session:
        document = session.get(QuoteDocument, document_id)
        assert document is not None
        assert document.processing_status == document.quote.status == "FAILED"
        assert document.processing_completed_at is not None
        assert document.last_error == "PROCESSING_FAILED"
        assert document.evidence_capture_version is None
        assert session.scalar(select(QuoteValue).where(QuoteValue.quote_id == document.quote_id)) is None
        assert session.scalar(select(DocumentBlock).where(DocumentBlock.quote_document_id == document_id)) is not None


def test_pdf_validation_rejects_bad_files_and_page_limit(
    storage_client: tuple[TestClient, LocalDocumentStorage],
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    encrypted = pymupdf.open()
    encrypted.new_page()
    encrypted_data = encrypted.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256,  # pyright: ignore[reportAttributeAccessIssue]
        owner_pw="owner", user_pw="reader",
    )
    encrypted.close()
    for data, name in ((pdf_bytes(), "quote.txt"), (b"not a pdf", "quote.pdf"),
                       (b"%PDF-broken", "quote.pdf"), (encrypted_data, "quote.pdf"),
                       (pdf_bytes(16), "quote.pdf")):
        response = upload(api, project_id, supplier_id, data, name)
        assert response.status_code == 422, response.text
    if storage.root.exists():
        assert list(storage.root.rglob("*.pdf")) == []
    assert api.get(f"/projects/{project_id}/quotes").json() == []
    accepted = upload(api, project_id, supplier_id, pdf_bytes(15))
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["document"]["page_count"] == 15


def test_duplicate_and_different_existing_quote_conflicts(
    storage_client: tuple[TestClient, LocalDocumentStorage],
) -> None:
    api, _ = storage_client
    project_id, supplier_id, other = setup_shortlist(api, approve_shortlist=False)
    assert api.patch(f"/projects/{project_id}/suppliers/{other}", json={
        "shortlisted": True,
    }).status_code == 200
    assert api.post(f"/projects/{project_id}/shortlist/approve").status_code == 200
    original = pdf_bytes()
    assert upload(api, project_id, supplier_id, original).status_code == 201
    duplicate = upload(api, project_id, supplier_id, original)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_PDF"
    different = upload(api, project_id, supplier_id, pdf_bytes(2))
    assert different.status_code == 409
    assert different.json()["error"]["code"] == "QUOTE_ALREADY_EXISTS"
    assert api.post(f"/projects/{project_id}/quotes/manual", json={
        "supplier_id": other,
    }).status_code == 201
    manual_conflict = upload(api, project_id, other, pdf_bytes())
    assert manual_conflict.status_code == 409
    assert manual_conflict.json()["error"]["code"] == "QUOTE_ALREADY_EXISTS"


def test_stage_pdf_exact_byte_boundary_and_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = document_settings_from_environment()
    monkeypatch.setattr("sourcepilot.documents.service.inspect_page_count", lambda *args, **kwargs: 1)
    accepted = b"%PDF-" + b"x" * (10_000_000 - 5)
    staged = stage_pdf_upload(UploadFile(file=BytesIO(accepted), filename="a.pdf"), settings)
    directory, path, _, digest, pages = staged
    assert path.stat().st_size == 10_000_000
    assert digest == hashlib.sha256(accepted).hexdigest()
    assert pages == 1
    directory.cleanup()
    assert not path.exists()
    with pytest.raises(PdfUploadError) as error:
        stage_pdf_upload(
            UploadFile(file=BytesIO(accepted + b"x"), filename="a.pdf"), settings,
        )
    assert error.value.status_code == 413


def test_invalid_stage_removes_private_temporary_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    original_temporary = TemporaryDirectory
    monkeypatch.setattr(
        "sourcepilot.documents.service.TemporaryDirectory",
        lambda prefix: original_temporary(prefix=prefix, dir=tmp_path),
    )
    with pytest.raises(PdfUploadError):
        stage_pdf_upload(
            UploadFile(file=BytesIO(b"%PDF-broken"), filename="a.pdf"),
            document_settings_from_environment(),
        )
    assert list(tmp_path.iterdir()) == []


def test_inspection_timeout_reaps_child_cleans_temporary_file_and_allows_retry(
    storage_client: tuple[TestClient, LocalDocumentStorage],
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    api, _ = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    marker = tmp_path / "child-started"
    staged_root = tmp_path / "staged"
    staged_root.mkdir()
    real_popen = subprocess.Popen
    real_temporary = TemporaryDirectory
    children: list[subprocess.Popen[str]] = []
    child_code = (
        "import os, pathlib, sys, time; "
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)"
    )

    def spawn_blocking_child(args: list[str], *positional: Any, **options: Any) -> subprocess.Popen[str]:
        assert args[1:3] == ["-m", "sourcepilot.documents.inspect_pdf"]
        child = real_popen(
            [sys.executable, "-c", child_code, str(marker)], *positional, **options,
        )
        children.append(child)
        return child

    with monkeypatch.context() as patch:
        patch.setattr(subprocess, "Popen", spawn_blocking_child)
        patch.setattr(
            "sourcepilot.documents.service.TemporaryDirectory",
            lambda prefix: real_temporary(prefix=prefix, dir=staged_root),
        )
        with pytest.raises(PdfUploadError, match="timed out") as timeout_error:
            stage_pdf_upload(
                UploadFile(file=BytesIO(pdf_bytes()), filename="a.pdf"),
                replace(document_settings_from_environment(), inspection_timeout_seconds=2),
            )
    assert isinstance(timeout_error.value.__cause__, PdfInspectionTimeoutError)
    assert marker.exists(), "The real child must start before the timeout"
    assert len(children) == 1
    assert children[0].returncode is not None
    assert children[0].wait(timeout=0) == children[0].returncode
    assert list(staged_root.iterdir()) == []
    accepted = upload(api, project_id, supplier_id, pdf_bytes())
    assert accepted.status_code == 201, accepted.text


def test_local_and_s3_storage_use_owned_safe_keys(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-original")
    key = new_storage_key()
    local = LocalDocumentStorage(tmp_path / "local")
    local.put(key, source)
    assert (local.root / key).read_bytes() == source.read_bytes()
    with pytest.raises(ValueError):
        local.delete("../other.pdf")
    local.delete(key)
    assert not (local.root / key).exists()
    mock_client = Mock()
    s3 = S3DocumentStorage("bucket", client=mock_client)
    s3.put(key, source)
    assert mock_client.put_object.call_args.kwargs["Key"] == key
    assert mock_client.put_object.call_args.kwargs["ContentType"] == "application/pdf"
    s3.delete(key)
    mock_client.delete_object.assert_called_once_with(Bucket="bucket", Key=key)


def test_request_limit_rejects_stream_without_content_length_before_parser() -> None:
    calls = 0
    async def inner(*args: object) -> None:
        nonlocal calls
        calls += 1
    middleware = UploadBodyLimitMiddleware(inner)
    settings = document_settings_from_environment()
    assert settings.max_request_bytes == 10_000_000 + MULTIPART_OVERHEAD_BYTES
    messages = iter([
        {"type": "http.request", "body": b"x" * settings.max_request_bytes, "more_body": True},
        {"type": "http.request", "body": b"x", "more_body": False},
    ])
    sent: list[dict[str, object]] = []
    async def receive() -> dict[str, object]:
        return next(messages)
    async def send(message: dict[str, object]) -> None:
        sent.append(message)
    asyncio.run(middleware(
        {"type": "http", "method": "POST", "path": "/projects/x/quotes/upload", "headers": []},
        receive, send,
    ))
    assert calls == 0
    assert sent[0]["status"] == 413


def test_upload_scope_and_existing_manual_quote(
    storage_client: tuple[TestClient, LocalDocumentStorage],
) -> None:
    api, _ = storage_client
    project_id, supplier_id, other = setup_shortlist(api, approve_shortlist=False)
    assert upload(api, project_id, supplier_id, pdf_bytes()).status_code == 409
    assert api.post(f"/projects/{project_id}/shortlist/approve").status_code == 200
    assert upload(api, project_id, other, pdf_bytes()).status_code == 409
    with TestClient(app, raise_server_exceptions=False) as stranger:
        assert stranger.post("/demo-session").status_code == 204
        assert upload(stranger, project_id, supplier_id, pdf_bytes()).status_code == 404
    assert api.post(f"/projects/{project_id}/quotes/manual", json={
        "supplier_id": supplier_id,
    }).status_code == 201
    conflict = upload(api, project_id, supplier_id, pdf_bytes())
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "QUOTE_ALREADY_EXISTS"


def test_storage_partial_write_is_cleaned_after_failure(
    storage_client: tuple[TestClient, LocalDocumentStorage], monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    original_put = storage.put
    def failing_put(key: str, source: Path) -> None:
        original_put(key, source)
        raise OSError("simulated uncertain write")
    monkeypatch.setattr(storage, "put", failing_put)
    response = upload(api, project_id, supplier_id, pdf_bytes())
    assert response.status_code == 503
    assert api.get(f"/projects/{project_id}/quotes").json() == []
    assert list(storage.root.rglob("*.pdf")) == []


def test_partial_write_and_unlink_failure_records_safe_identifiers(
    storage_client: tuple[TestClient, LocalDocumentStorage],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    original_open = Path.open
    original_unlink = Path.unlink
    secret = "sensitive PDF bytes and connection secret"
    content_marker = "PRIVATE PDF CONTENT MARKER"
    document = pymupdf.open()
    document.new_page().insert_text((50, 50), content_marker)
    sensitive_pdf = document.tobytes()
    document.close()
    log = Mock()
    original_put = storage.put
    write_errors: list[Exception] = []
    monkeypatch.setattr("sourcepilot.documents.storage.logger", log)

    def observed_put(key: str, source: Path) -> None:
        try:
            original_put(key, source)
        except Exception as error:
            write_errors.append(error)
            raise

    monkeypatch.setattr(storage, "put", observed_put)

    class FailingOutput:
        def __init__(self, path: Path) -> None:
            self.file = original_open(path, "xb")

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            self.file.close()

        def write(self, data: bytes) -> None:
            self.file.write(data[:16])
            raise OSError("original partial write failure")

    def failing_open(path: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if path.suffix == ".part" and mode == "xb":
            return FailingOutput(path)
        return original_open(path, mode, *args, **kwargs)

    def failing_unlink(path: Path, *args: Any, **kwargs: Any) -> None:
        if path.suffix == ".part":
            raise OSError(secret)
        original_unlink(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", failing_open)
        patch.setattr(Path, "unlink", failing_unlink)
        response = upload(api, project_id, supplier_id, sensitive_pdf)
    assert response.status_code == 503
    assert len(write_errors) == 1
    assert str(write_errors[0]) == "original partial write failure"
    assert response.json()["error"]["code"] == "UPLOAD_UNAVAILABLE"
    assert "original partial write failure" not in response.text
    assert secret not in response.text
    assert content_marker not in response.text
    assert api.get(f"/projects/{project_id}/quotes").json() == []
    partials = list(storage.root.rglob("*.part"))
    assert len(partials) == 1
    message = log.error.call_args.args[0] % log.error.call_args.args[1:]
    assert "PDF partial cleanup failed" in message
    assert "quote-pdfs/" in message
    assert partials[0].name in message
    assert secret not in message
    assert content_marker not in message
    assert "original partial write failure" not in message
    original_unlink(partials[0])


def test_cleanup_failure_is_recorded_without_erasing_original_error(
    storage_client: tuple[TestClient, LocalDocumentStorage], monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    log = Mock()
    monkeypatch.setattr("sourcepilot.documents.service.logger", log)
    def failing_put(key: str, source: Path) -> None:
        raise OSError("write failed")
    def failing_delete(key: str) -> None:
        raise OSError("cleanup failed")
    monkeypatch.setattr(storage, "put", failing_put)
    monkeypatch.setattr(storage, "delete", failing_delete)
    response = upload(api, project_id, supplier_id, pdf_bytes())
    assert response.status_code == 503
    assert api.get(f"/projects/{project_id}/quotes").json() == []
    assert "PDF upload cleanup failed" in log.exception.call_args.args[0]


def test_confirmed_database_rollback_removes_owned_object(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    source = tmp_path / "quote.pdf"
    source.write_bytes(pdf_bytes())
    with Session(engine) as database_session:
        project = database_session.get(Project, UUID(project_id))
        assert project is not None
        def failing_commit() -> None:
            raise IntegrityError("commit", {}, Exception("constraint"))
        monkeypatch.setattr(database_session, "commit", failing_commit)
        with pytest.raises(IntegrityError):
            store_pdf_quote(
                database_session, project, UUID(supplier_id), path=source,
                filename="quote.pdf", sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                page_count=1, storage=storage,
            )
    assert list(storage.root.rglob("*.pdf")) == []
    with Session(engine) as database_session:
        assert database_session.scalars(select(Quote).where(Quote.project_id == UUID(project_id))).all() == []


def test_uncertain_commit_preserves_object_and_reports_it(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    source = tmp_path / "quote.pdf"
    source.write_bytes(pdf_bytes())
    log = Mock()
    monkeypatch.setattr("sourcepilot.documents.service.logger", log)
    with Session(engine) as database_session:
        project = database_session.get(Project, UUID(project_id))
        assert project is not None
        def uncertain_commit() -> None:
            raise ConnectionError("connection dropped")
        monkeypatch.setattr(database_session, "commit", uncertain_commit)
        with pytest.raises(PdfCommitUncertainError):
            store_pdf_quote(
                database_session, project, UUID(supplier_id), path=source,
                filename="quote.pdf", sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                page_count=1, storage=storage,
            )
    assert len(list(storage.root.rglob("*.pdf"))) == 1
    assert "commit outcome uncertain" in log.exception.call_args.args[0]


@pytest.mark.parametrize("same_pdf", [True, False], ids=["identical", "different"])
def test_concurrent_pdf_uploads_serialize_with_independent_postgres_transactions(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, same_pdf: bool,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    winner_bytes = pdf_bytes()
    loser_bytes = winner_bytes if same_pdf else pdf_bytes(2)
    first_stored = Event()
    release_first = Event()
    second_transaction_attempt = Event()
    guard = Lock()
    transaction_connections: list[object] = []
    original_put = storage.put
    real_temporary = TemporaryDirectory
    staged_root = tmp_path / "staged"
    staged_root.mkdir()

    def held_first_put(key: str, source: Path) -> None:
        original_put(key, source)
        first_stored.set()
        assert release_first.wait(timeout=15), "Second request did not reach PostgreSQL"

    def observe_transaction(connection: object, _cursor: object, statement: str,
                            _parameters: object, _context: object, _executemany: bool) -> None:
        # The session activity update can block before the second project FOR UPDATE.
        if "update demo_sessions" in statement.lower():
            with guard:
                transaction_connections.append(connection)
                if len(transaction_connections) == 2:
                    second_transaction_attempt.set()

    monkeypatch.setattr(storage, "put", held_first_put)
    monkeypatch.setattr(
        "sourcepilot.documents.service.TemporaryDirectory",
        lambda prefix: real_temporary(prefix=prefix, dir=staged_root),
    )
    event.listen(engine, "before_cursor_execute", observe_transaction)
    try:
        with TestClient(app, raise_server_exceptions=False) as second_api, ThreadPoolExecutor(
            max_workers=2,
        ) as executor:
            second_api.cookies.update(api.cookies)
            first = executor.submit(upload, api, project_id, supplier_id, winner_bytes)
            assert first_stored.wait(timeout=15), "First request did not hold the transaction"
            second = executor.submit(upload, second_api, project_id, supplier_id, loser_bytes)
            try:
                assert second_transaction_attempt.wait(timeout=15), (
                    f"Second request did not overlap: observed={len(transaction_connections)}, "
                    f"second_done={second.done()}, "
                    f"second_result={second.result() if second.done() else None}"
                )
                assert not first.done()
                assert not second.done()
            finally:
                release_first.set()
            winning_response = first.result(timeout=15)
            losing_response = second.result(timeout=15)
    finally:
        release_first.set()
        event.remove(engine, "before_cursor_execute", observe_transaction)

    assert transaction_connections[0] is not transaction_connections[1]
    assert winning_response.status_code == 201, winning_response.text
    assert losing_response.status_code == 409, losing_response.text
    assert losing_response.json()["error"]["code"] == (
        "DUPLICATE_PDF" if same_pdf else "QUOTE_ALREADY_EXISTS"
    )
    with Session(engine) as database_session:
        quotes = database_session.scalars(select(Quote)).all()
        documents = database_session.scalars(select(QuoteDocument)).all()
        assert len(quotes) == len(documents) == 1
        assert documents[0].quote_id == quotes[0].id
        assert documents[0].sha256 == hashlib.sha256(winner_bytes).hexdigest()
        stored_file = storage.root / documents[0].storage_key
        assert stored_file.read_bytes() == winner_bytes
    assert list(storage.root.rglob("*.pdf")) == [stored_file]
    assert list(storage.root.rglob("*.part")) == []
    assert list(staged_root.iterdir()) == []


def test_concurrent_manual_and_pdf_creation_keeps_one_quote(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine, tmp_path: Path,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    source = tmp_path / "quote.pdf"
    source.write_bytes(pdf_bytes())
    def create_pdf() -> str:
        with Session(engine) as database_session:
            project = database_session.get(Project, UUID(project_id))
            assert project is not None
            try:
                store_pdf_quote(
                    database_session, project, UUID(supplier_id), path=source,
                    filename="quote.pdf", sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    page_count=1, storage=storage,
                )
                return "created"
            except PdfUploadError:
                database_session.rollback()
                return "conflict"
    def create_manual() -> str:
        with Session(engine) as database_session:
            project = database_session.get(Project, UUID(project_id))
            assert project is not None
            try:
                create_manual_quote(database_session, project, UUID(supplier_id), {}, None)
                database_session.commit()
                return "created"
            except QuoteWorkflowError:
                database_session.rollback()
                return "conflict"
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = [executor.submit(create_pdf), executor.submit(create_manual)]
        assert sorted(future.result() for future in outcomes) == ["conflict", "created"]
    with Session(engine) as database_session:
        quotes = database_session.scalars(select(Quote).where(Quote.project_id == UUID(project_id))).all()
        assert len(quotes) == 1
        documents = database_session.scalars(select(QuoteDocument)).all()
        assert len(documents) == (1 if quotes[0].entry_type == "PDF" else 0)


def test_pdf_confirmation_and_confirmed_revision_preserve_evidence(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    uploaded = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "harbor_primary.pdf").read_bytes())
    quote_id = uploaded.json()["quote"]["id"]
    document_id = UUID(uploaded.json()["document"]["id"])
    process_pdf_quote(document_id, 1, session_factory=sessionmaker(bind=engine, expire_on_commit=False),
        storage=storage, settings=document_settings_from_environment(),
        client_factory=lambda: RecordedClient("harbor-primary"),
    )
    original = api.get(f"/quotes/{quote_id}").json()
    evidence = original["values"]["unit_price"]["evidence"]
    confirmed = api.post(f"/quotes/{quote_id}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "CONFIRMED"
    assert confirmed.json()["revision"] == 0
    assert confirmed.json()["values"]["unit_price"]["evidence"] == evidence
    with Session(engine) as session:
        document = session.get(QuoteDocument, document_id)
        assert document is not None and document.processing_status == "CONFIRMED"
    assert api.post(f"/quotes/{quote_id}/confirm").status_code == 409
    assert api.post(f"/quotes/{quote_id}/retry").status_code == 409
    assert upload(api, project_id, supplier_id, (FIXTURE_PDFS / "moss_primary.pdf").read_bytes()).status_code == 409

    same = api.patch(f"/quotes/{quote_id}", json={
        "values": {"unit_price": "4.6"}, "notes": "Reviewed",
    })
    assert same.status_code == 200
    assert same.json()["revision"] == 0
    assert same.json()["values"]["unit_price"]["current_origin"] == "USER_CORRECTED"
    changed = api.patch(f"/quotes/{quote_id}", json={
        "values": {"unit_price": "4.50", "shipping_cost": "12.00"},
    })
    assert changed.status_code == 200, changed.text
    assert changed.json()["revision"] == 1
    assert changed.json()["values"]["unit_price"]["current_origin"] == "USER_CORRECTED"
    assert changed.json()["values"]["unit_price"]["evidence"] == evidence
    assert changed.json()["values"]["shipping_cost"]["current_origin"] == "USER_CORRECTED"
    assert api.patch(f"/quotes/{quote_id}", json={"values": {"shipping_cost": None}}).json()["revision"] == 2
    restored = api.patch(f"/quotes/{quote_id}", json={"values": {"unit_price": "4.60"}}).json()
    assert restored["revision"] == 3
    assert restored["values"]["unit_price"]["current_origin"] == "AI_EXTRACTED"
    assert restored["values"]["unit_price"]["evidence"] == evidence


def test_stale_boundary_retry_and_no_duplicate_schedule(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, _ = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    uploaded = upload(api, project_id, supplier_id, pdf_bytes())
    quote_id = uploaded.json()["quote"]["id"]
    document_id = UUID(uploaded.json()["document"]["id"])
    now = datetime.now(UTC)
    with Session(engine) as session:
        document = session.get(QuoteDocument, document_id)
        assert document is not None
        document.processing_started_at = now - timedelta(seconds=600)
        assert effective_processing_status(document, now=now, stale_seconds=600) == "PROCESSING"
        assert effective_processing_status(
            document, now=now + timedelta(microseconds=1), stale_seconds=600
        ) == "STALE_PROCESSING"
        document.processing_started_at = now - timedelta(seconds=601)
        session.commit()
    assert api.get(f"/quotes/{quote_id}").json()["status"] == "STALE_PROCESSING"
    assert api.post(f"/quotes/{quote_id}/manual-fallback", json={"values": {}}).status_code == 409
    assert upload(api, project_id, supplier_id, pdf_bytes(2)).status_code == 409
    scheduled: list[tuple[UUID, int]] = []
    monkeypatch.setattr("sourcepilot.main.run_pdf_quote_processing", lambda document_id, attempt: scheduled.append((document_id, attempt)))
    first = api.post(f"/quotes/{quote_id}/retry")
    second = api.post(f"/quotes/{quote_id}/retry")
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"] == quote_id
    assert first.json()["processing"]["attempts"] == second.json()["processing"]["attempts"] == 2
    assert scheduled == [(document_id, 2)]
    assert api.get(f"/quotes/{quote_id}").json()["status"] == "PROCESSING"


def test_initial_processing_attempt_cannot_be_retried(
    storage_client: tuple[TestClient, LocalDocumentStorage],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, _ = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    uploaded = upload(api, project_id, supplier_id, pdf_bytes())
    quote_id = uploaded.json()["quote"]["id"]
    scheduled: list[tuple[UUID, int]] = []
    monkeypatch.setattr("sourcepilot.main.run_pdf_quote_processing",
                        lambda document_id, attempt: scheduled.append((document_id, attempt)))
    response = api.post(f"/quotes/{quote_id}/retry")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "QUOTE_NOT_RETRYABLE"
    assert scheduled == []
    assert api.get(f"/quotes/{quote_id}").json()["processing"]["attempts"] == 1


def test_queued_old_attempt_exits_after_stale_retry_without_side_effects(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    uploaded = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "harbor_primary.pdf").read_bytes())
    quote_id = uploaded.json()["quote"]["id"]
    document_id = UUID(uploaded.json()["document"]["id"])
    with Session(engine) as session:
        document = session.get(QuoteDocument, document_id)
        assert document is not None
        document.processing_started_at = datetime.now(UTC) - timedelta(seconds=601)
        session.commit()
    scheduled: list[tuple[UUID, int]] = []
    monkeypatch.setattr("sourcepilot.main.run_pdf_quote_processing",
                        lambda doc_id, attempt: scheduled.append((doc_id, attempt)))
    assert api.post(f"/quotes/{quote_id}/retry").status_code == 200
    assert api.post(f"/quotes/{quote_id}/retry").status_code == 200
    assert scheduled == [(document_id, 2)]
    with monkeypatch.context() as patch:
        patch.setattr("sourcepilot.documents.processing.parse_and_persist_document",
                      lambda *args, **kwargs: pytest.fail("Old worker parsed"))
        process_pdf_quote(document_id, 1, session_factory=sessionmaker(bind=engine, expire_on_commit=False),
                          storage=storage, settings=document_settings_from_environment(),
                          client_factory=lambda: pytest.fail("Old worker created model client"))
    with Session(engine) as session:
        assert session.scalar(select(DocumentBlock).where(DocumentBlock.quote_document_id == document_id)) is None
        assert session.scalar(select(AIRun).where(AIRun.operation == "quote_extractor")) is None
        assert session.scalar(select(QuoteValue).where(QuoteValue.quote_id == UUID(quote_id))) is None
        document = session.get(QuoteDocument, document_id)
        assert document is not None and document.processing_attempts == 2
        assert document.processing_status == "PROCESSING" and document.processing_completed_at is None


@pytest.mark.parametrize("prior,outcome,complete_newer", [
    (None, "FINAL", False), ("repair", "FINAL", False), ("provider", "FINAL", False),
    (None, "PROVIDER_ERROR", False), (None, "TIMEOUT", False), (None, "ERROR", False),
    (None, "FINAL", True),
])
def test_retry_during_extraction_finalizes_only_old_attempt_trace(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
    monkeypatch: pytest.MonkeyPatch, prior: str | None, outcome: str, complete_newer: bool,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    uploaded = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "harbor_primary.pdf").read_bytes())
    quote_id = uploaded.json()["quote"]["id"]
    document_id = UUID(uploaded.json()["document"]["id"])
    scheduled: list[tuple[UUID, int]] = []
    monkeypatch.setattr("sourcepilot.main.run_pdf_quote_processing",
                        lambda doc_id, attempt: scheduled.append((doc_id, attempt)))
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    newer_result: dict[str, Any] | None = None

    class SupersedingClient(RecordedClient):
        calls = 0

        def invoke(self, **kwargs: object) -> ModelInvocation:
            nonlocal newer_result
            self.calls += 1
            if prior is not None and self.calls == 1:
                if prior == "provider":
                    raise ModelProviderError("private provider detail", retryable=True)
                return ModelInvocation("private invalid model output", 1, 1)
            with Session(engine) as session:
                document = session.get(QuoteDocument, document_id)
                assert document is not None
                document.processing_started_at = datetime.now(UTC) - timedelta(seconds=601)
                session.commit()
            assert api.post(f"/quotes/{quote_id}/retry").status_code == 200
            if complete_newer:
                process_pdf_quote(document_id, 2, session_factory=factory,
                                  storage=storage, settings=document_settings_from_environment(),
                                  client_factory=lambda: RecordedClient("harbor-primary"))
                newer_result = api.get(f"/quotes/{quote_id}").json()
            if outcome == "ERROR":
                raise RuntimeError("private unexpected detail")
            if outcome == "TIMEOUT":
                raise ModelProviderError("private provider detail", retryable=True) from TimeoutError(
                    "private timeout detail")
            if outcome == "PROVIDER_ERROR":
                raise ModelProviderError("private provider detail", retryable=True)
            return super().invoke(**kwargs)

    model = SupersedingClient("harbor-primary")
    process_pdf_quote(document_id, 1, session_factory=factory,
                      storage=storage, settings=document_settings_from_environment(),
                      client_factory=lambda: model)
    assert scheduled == [(document_id, 2)]
    assert model.calls == (2 if prior else 1)
    with Session(engine) as session:
        runs = session.scalars(select(AIRun).where(AIRun.operation == "quote_extractor")
                               .order_by(AIRun.started_at)).all()
        assert len(runs) == (2 if complete_newer else 1)
        run = runs[0]
        assert run is not None
        assert run.status == "FAILED" and run.attempts == model.calls
        assert run.error_type == "StalePdfAttemptError"
        assert run.completed_at is not None
        steps = session.scalars(select(SupplierExplanationRunStep).where(
            SupplierExplanationRunStep.air_run_id == run.id,
        ).order_by(SupplierExplanationRunStep.sequence)).all()
        prefix = ([('model', 'FINAL', None), ('validation', 'INVALID', None),
                   ('retry', 'REPAIR', None)] if prior == "repair" else
                  [('model', 'PROVIDER_ERROR', None), ('retry', 'PROVIDER', None)]
                  if prior == "provider" else [])
        usage = ("PARTIAL" if prior == "provider" else "COMPLETE") if outcome == "FINAL" else "UNAVAILABLE"
        assert [(step.kind, step.outcome, step.name) for step in steps] == prefix + [
            ("model", outcome, None), ("scope", "CHANGED", None),
            ("usage", usage, "input_tokens"), ("usage", usage, "output_tokens"),
            ("run", "FAILED", None),
        ]
        assert [step.sequence for step in steps] == list(range(1, len(steps) + 1))
        assert run.input_tokens == run.output_tokens == (
            (2 if prior == "repair" else 1) if outcome == "FINAL" else None)
        assert run.estimated_cost is None
        if not complete_newer:
            assert session.scalar(select(QuoteValue).where(QuoteValue.quote_id == UUID(quote_id))) is None
            assert session.scalar(select(QuoteFieldEvidence)) is None
        else:
            assert runs[1].status == "COMPLETED" and runs[1].completed_at is not None
        document = session.get(QuoteDocument, document_id)
        assert document is not None and document.processing_attempts == 2
        assert document.processing_status == document.quote.status == (
            "NEEDS_REVIEW" if complete_newer else "PROCESSING")
        assert (document.processing_completed_at is not None) == complete_newer
    if complete_newer:
        assert api.get(f"/quotes/{quote_id}").json() == newer_result


def test_failed_replacement_has_one_active_document_and_rejects_late_worker(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    original = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "harbor_primary.pdf").read_bytes())
    quote_id = original.json()["quote"]["id"]
    old_id = UUID(original.json()["document"]["id"])
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    process_pdf_quote(old_id, 1, session_factory=factory, storage=storage,
                      settings=document_settings_from_environment(),
                      client_factory=lambda: FailedClient("harbor-primary"))
    scheduled: list[tuple[UUID, int]] = []
    monkeypatch.setattr("sourcepilot.main.run_pdf_quote_processing", lambda document_id, attempt: scheduled.append((document_id, attempt)))
    replacement = upload(api, project_id, supplier_id,
                         (FIXTURE_PDFS / "moss_primary.pdf").read_bytes())
    assert replacement.status_code == 201, replacement.text
    assert replacement.json()["quote"]["id"] == quote_id
    new_id = UUID(replacement.json()["document"]["id"])
    assert new_id != old_id
    duplicate = upload(api, project_id, supplier_id,
                       (FIXTURE_PDFS / "moss_primary.pdf").read_bytes())
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_PDF"
    assert scheduled == [(new_id, 1)]
    with Session(engine) as session:
        documents = session.scalars(select(QuoteDocument).where(QuoteDocument.quote_id == UUID(quote_id))).all()
        assert len(documents) == 2
        assert [document.id for document in documents if document.is_active] == [new_id]
        old_blocks = session.scalars(select(DocumentBlock).where(
            DocumentBlock.quote_document_id == old_id
        ).order_by(DocumentBlock.page_number, DocumentBlock.block_number)).all()
        assert old_blocks
        original_block_texts = [block.text for block in old_blocks]
    with monkeypatch.context() as patch:
        patch.setattr("sourcepilot.documents.parse_service.parse_pdf_snapshot",
                      lambda *args, **kwargs: [ParsedBlock(1, 1, "tampered late parse")])
        parse_and_persist_document(factory, old_id, storage=storage,
                                   settings=document_settings_from_environment(), expected_attempt=1)
    with Session(engine) as session:
        assert [block.text for block in session.scalars(select(DocumentBlock).where(
            DocumentBlock.quote_document_id == old_id
        ).order_by(DocumentBlock.page_number, DocumentBlock.block_number)).all()] == original_block_texts
    stale_extraction = QuoteExtraction.model_validate(load_recorded_outputs()["harbor-primary"])
    _finish_success(factory, old_id, 1, stale_extraction)
    assert api.get(f"/quotes/{quote_id}").json()["status"] == "PROCESSING"
    process_pdf_quote(new_id, 1, session_factory=factory, storage=storage,
                      settings=document_settings_from_environment(),
                      client_factory=lambda: RecordedClient("moss-primary"))
    assert api.get(f"/quotes/{quote_id}").json()["status"] == "NEEDS_REVIEW"


def test_failed_pdf_manual_fallback_reuses_manual_lifecycle_and_blocks_old_worker(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    uploaded = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "harbor_primary.pdf").read_bytes())
    quote_id = uploaded.json()["quote"]["id"]
    document_id = UUID(uploaded.json()["document"]["id"])
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    process_pdf_quote(document_id, 1, session_factory=factory, storage=storage,
                      settings=document_settings_from_environment(),
                      client_factory=lambda: FailedClient("harbor-primary"))
    with Session(engine) as session:
        block = session.scalars(select(DocumentBlock).where(DocumentBlock.quote_document_id == document_id)).first()
        assert block is not None
        value = QuoteValue(quote_id=UUID(quote_id), field_key="unit_price", current_value="4.60",
                           current_origin="AI_EXTRACTED", ai_extracted_value="4.60")
        value.evidence.append(QuoteFieldEvidence(block=block, evidence_value="4.60"))
        session.add(value)
        session.commit()
    fallback = api.post(f"/quotes/{quote_id}/manual-fallback", json={
        "values": {"unit_price": "4.75", "currency": "usd"},
    })
    assert fallback.status_code == 200, fallback.text
    body = fallback.json()
    assert body["id"] == quote_id and body["entry_type"] == "MANUAL"
    assert body["status"] == "NEEDS_REVIEW" and body["processing"] is None
    assert body["values"]["unit_price"]["current_origin"] == "USER_ENTERED"
    assert body["values"]["unit_price"]["ai_extracted_value"] is None
    assert body["values"]["unit_price"]["evidence"] == []
    assert body["values"]["currency"]["current_value"] == "USD"
    with Session(engine) as session:
        document = session.get(QuoteDocument, document_id)
        assert document is not None and not document.is_active
        assert session.scalar(select(QuoteFieldEvidence)) is None
        assert session.scalar(select(DocumentBlock).where(DocumentBlock.quote_document_id == document_id)) is not None
    _finish_success(factory, document_id, 1,
                    QuoteExtraction.model_validate(load_recorded_outputs()["harbor-primary"]))
    assert api.get(f"/quotes/{quote_id}").json() == body
    assert api.patch(f"/quotes/{quote_id}", json={"values": {"unit_price": "4.80"}}).status_code == 200
    assert api.post(f"/quotes/{quote_id}/confirm").json()["status"] == "CONFIRMED"
    assert api.post(f"/quotes/{quote_id}/retry").status_code == 409
    with TestClient(app, raise_server_exceptions=False) as stranger:
        assert stranger.post("/demo-session").status_code == 204
        assert stranger.post(f"/quotes/{quote_id}/retry").status_code == 404
        assert stranger.post(f"/quotes/{quote_id}/manual-fallback", json={"values": {}}).status_code == 404


def test_concurrent_failed_retry_schedules_one_attempt(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    uploaded = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "harbor_primary.pdf").read_bytes())
    quote_id = uploaded.json()["quote"]["id"]
    document_id = UUID(uploaded.json()["document"]["id"])
    process_pdf_quote(document_id, 1, session_factory=sessionmaker(bind=engine, expire_on_commit=False),
                      storage=storage, settings=document_settings_from_environment(),
                      client_factory=lambda: FailedClient("harbor-primary"))
    scheduled: list[tuple[UUID, int]] = []
    monkeypatch.setattr("sourcepilot.main.run_pdf_quote_processing", lambda document_id, attempt: scheduled.append((document_id, attempt)))
    ready = Barrier(2)
    with TestClient(app, raise_server_exceptions=False) as second_api, ThreadPoolExecutor(max_workers=2) as pool:
        second_api.cookies.update(api.cookies)
        def request_retry(client: TestClient):
            ready.wait(timeout=10)
            return client.post(f"/quotes/{quote_id}/retry")
        results = [pool.submit(request_retry, client) for client in (api, second_api)]
        responses = [future.result(timeout=20) for future in results]
    assert [response.status_code for response in responses] == [200, 200]
    assert all(response.json()["processing"]["attempts"] == 2 for response in responses)
    assert scheduled == [(document_id, 2)]


def test_concurrent_failed_replacement_schedules_one_new_document(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    uploaded = upload(api, project_id, supplier_id,
                      (FIXTURE_PDFS / "harbor_primary.pdf").read_bytes())
    old_id = UUID(uploaded.json()["document"]["id"])
    process_pdf_quote(old_id, 1, session_factory=sessionmaker(bind=engine, expire_on_commit=False),
                      storage=storage, settings=document_settings_from_environment(),
                      client_factory=lambda: FailedClient("harbor-primary"))
    scheduled: list[tuple[UUID, int]] = []
    monkeypatch.setattr("sourcepilot.main.run_pdf_quote_processing", lambda document_id, attempt: scheduled.append((document_id, attempt)))
    replacement_pdf = (FIXTURE_PDFS / "moss_primary.pdf").read_bytes()
    ready = Barrier(2)
    with TestClient(app, raise_server_exceptions=False) as second_api, ThreadPoolExecutor(max_workers=2) as pool:
        second_api.cookies.update(api.cookies)
        def request_replacement(client: TestClient):
            ready.wait(timeout=10)
            return upload(client, project_id, supplier_id, replacement_pdf)
        results = [pool.submit(request_replacement, client) for client in (api, second_api)]
        responses = [future.result(timeout=20) for future in results]
    assert sorted(response.status_code for response in responses) == [201, 409]
    new_id = UUID(next(response for response in responses if response.status_code == 201).json()["document"]["id"])
    assert next(response for response in responses if response.status_code == 409).json()["error"]["code"] == "DUPLICATE_PDF"
    assert scheduled == [(new_id, 1)]
    with Session(engine) as session:
        documents = session.scalars(select(QuoteDocument)).all()
        assert len(documents) == 2
        assert [document.id for document in documents if document.is_active] == [new_id]
