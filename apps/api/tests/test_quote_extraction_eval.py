"""Deterministic M3-U6 quote-extraction eval target."""

from __future__ import annotations

import json
from collections.abc import Iterator
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from sourcepilot.ai.client import AnalystModelInvocation, ModelInvocation
from sourcepilot.ai.quote_extraction_eval import load_cases, load_recorded_outputs, score_case
from sourcepilot.ai.quote_extractor import QuoteExtraction, extract_quote_document
from sourcepilot.ai.structured import structured_input_hash
from sourcepilot.documents.parse_pdf import NoExtractableTextError, parse_pdf_snapshot
from sourcepilot.persistence.models import (
    DemoSession,
    DocumentBlock,
    Project,
    Quote,
    QuoteDocument,
    Supplier,
)
from tests.database_test_support import (
    create_test_engine,
    persistence_test_database_url_from_environment,
    reset_test_database,
)

FIXTURES = Path(__file__).parent / "fixtures" / "quote_pdfs"


class RecordedClient:
    model = "recorded-quote-extraction"

    def __init__(self, *, request_hash: str, output: dict[str, object]) -> None:
        self.request_hash = request_hash
        self.output = output
        self.calls = 0

    def invoke(self, *, instructions: str, input_text: str, schema_name: str,
               schema: dict[str, object]) -> ModelInvocation:
        self.calls += 1
        assert schema_name == "QuoteExtraction"
        assert schema == QuoteExtraction.model_json_schema()
        assert structured_input_hash(instructions=instructions, input_text=input_text) == self.request_hash
        return ModelInvocation(json.dumps(self.output), input_tokens=1, output_tokens=1)

    def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
        raise AssertionError("Quote extraction must never use tools.")


@pytest.fixture
def engine() -> Iterator[Engine]:
    url = persistence_test_database_url_from_environment()
    reset_test_database(url)
    database = create_test_engine(url)
    try:
        yield database
    finally:
        database.dispose()
        reset_test_database(url)


def test_recorded_quote_extraction_cases_score_expected_metrics(engine: Engine, tmp_path: Path) -> None:
    cases = load_cases()
    outputs = load_recorded_outputs()
    assert len(cases) == 5
    assert {case["id"] for case in cases} == set(outputs)
    assert len({case["id"] for case in cases}) == len(cases)
    with Session(engine) as session:
        for case in cases:
            parsed = parse_pdf_snapshot(
                FIXTURES / case["pdf"], tmp_path / f"{case['id']}.json",
                timeout_seconds=10, max_pages=15, expected_pages=None,
            )
            now = datetime.now(UTC)
            owner = DemoSession(
                opaque_token=f"eval-{uuid4()}", last_seen_at=now,
                expires_at=now + timedelta(hours=1),
            )
            project = Project(demo_session=owner, name="Quote eval", original_request="Source bags")
            supplier = Supplier(
                id=uuid4(), name=f"Synthetic Eval Supplier {uuid4()}",
                country="Testland", description="Synthetic fixture supplier",
            )
            session.add_all([project, supplier])
            session.flush()
            quote = Quote(
                project_id=project.id, supplier_id=supplier.id,
                entry_type="PDF", status="PROCESSING", revision=0,
            )
            document = QuoteDocument(
                quote=quote, storage_key=f"{uuid4()}.pdf", original_filename=case["pdf"],
                sha256="0" * 64, page_count=max(block.page_number for block in parsed),
                processing_status="PROCESSING", processing_attempts=0,
            )
            session.add(document)
            session.flush()
            session.add_all([
                DocumentBlock(
                    id=uuid4(), quote_document_id=document.id,
                    page_number=block.page_number, block_number=block.block_number,
                    text=block.text,
                ) for block in parsed
            ])
            session.commit()
            client = RecordedClient(
                request_hash=case["request_hash"], output=outputs[case["id"]],
            )
            result, run = extract_quote_document(
                session, demo_session=owner, document_id=document.id, client=client,
            )
            assert client.calls == 1, case["id"]
            assert run.status == "COMPLETED", case["id"]
            assert result is not None, case["id"]
            assert score_case(result, case) == {
                "field_accuracy": 1.0,
                "numeric_accuracy": 1.0,
                "currency_accuracy": 1.0,
                "unknown_detection": 1.0,
                "conflict_detection": 1.0,
                "source_block_accuracy": 1.0,
                "hallucination_rate": 0.0,
            }, case["id"]


def test_scorer_detects_invented_missing_value_and_wrong_source() -> None:
    case = next(item for item in load_cases() if item["id"] == "missing-shipping")
    output = deepcopy(load_recorded_outputs()[case["id"]])
    output["fields"]["shipping_cost"] = {
        "state": "KNOWN", "extracted_value": "320", "source_block_ids": ["p1-b4"],
        "uncertainty": None, "conflicting_values": [],
    }
    scores = score_case(QuoteExtraction.model_validate(output), case)
    assert scores["unknown_detection"] < 1.0
    assert scores["hallucination_rate"] > 0
    assert scores["source_block_accuracy"] < 1.0


def test_recorded_response_rejects_changed_extraction_request() -> None:
    case = load_cases()[0]
    client = RecordedClient(
        request_hash=case["request_hash"], output=load_recorded_outputs()[case["id"]],
    )
    with pytest.raises(AssertionError):
        client.invoke(
            instructions="Changed extraction prompt", input_text='{"document_blocks":[]}',
            schema_name="QuoteExtraction", schema=QuoteExtraction.model_json_schema(),
        )


def test_image_only_fixture_fails_before_quote_extraction(tmp_path: Path) -> None:
    client = RecordedClient(request_hash="never-called", output={})
    with pytest.raises(NoExtractableTextError):
        parse_pdf_snapshot(
            FIXTURES / "image_only.pdf", tmp_path / "blocks.json",
            timeout_seconds=10, max_pages=15, expected_pages=1,
        )
    assert client.calls == 0
