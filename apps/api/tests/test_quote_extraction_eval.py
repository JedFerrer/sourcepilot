"""Deterministic M3-U6 quote-extraction eval target."""

from __future__ import annotations

import json
from collections.abc import Iterator
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from sourcepilot.ai.client import AnalystModelInvocation, ModelInvocation
from sourcepilot.ai.quote_extraction_eval import load_cases, load_recorded_outputs, score_case
from sourcepilot.ai.quote_extractor import (
    INSTRUCTIONS,
    QuoteExtraction,
    extract_quote_document,
    validate_source_references,
)
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


def score_parsed_case(result: QuoteExtraction, case: dict[str, Any]) -> dict[str, float]:
    from sourcepilot.ai.eval_baseline import parser_result

    with TemporaryDirectory() as directory:
        parser_result(case, Path(directory))
    return score_case(result, case)


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
    assert len(cases) == 10
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
            assert score_parsed_case(result, case) == {
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
    scores = score_parsed_case(QuoteExtraction.model_validate(output), case)
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


@pytest.mark.parametrize("case", load_cases(), ids=lambda case: case["id"])
def test_numeric_all_curated_cases_preserve_facts_sources_and_request_binding(case: dict[str, Any]) -> None:
    # Curated regression outputs, not a live evaluation or replay of rejected responses.
    blocks = json.loads((FIXTURES / "expected_blocks.json").read_text(encoding="utf-8"))
    document_blocks = blocks[case["pdf"]]["blocks"]
    valid_ids = {reference for reference, _ in document_blocks}
    payload = load_recorded_outputs()[case["id"]]
    result = QuoteExtraction.model_validate(payload)
    assert result.model_dump(mode="json") == payload
    validate_source_references(result, valid_ids)
    assert score_parsed_case(result, case) == {
        "field_accuracy": 1.0, "numeric_accuracy": 1.0, "currency_accuracy": 1.0,
        "unknown_detection": 1.0, "conflict_detection": 1.0,
        "source_block_accuracy": 1.0, "hallucination_rate": 0.0,
    }
    input_text = json.dumps({"document_blocks": [
        {"id": reference, "text": text} for reference, text in document_blocks
    ]}, ensure_ascii=False, separators=(",", ":"))
    assert structured_input_hash(instructions=INSTRUCTIONS, input_text=input_text) == case["request_hash"]


@pytest.mark.parametrize("currency", ["USD", "AUD", "EUR"])
def test_numeric_currency_is_separate_and_does_not_convert_amounts(currency: str) -> None:
    payload = deepcopy(load_recorded_outputs()["non-usd"])
    payload["fields"]["currency"]["extracted_value"] = currency
    result = QuoteExtraction.model_validate(payload)
    assert result.fields.currency.extracted_value == currency
    assert result.fields.unit_price.extracted_value == "4.60"
    assert result.fields.tooling_cost.extracted_value == "150"
    payload["fields"]["currency"].update(
        state="UNKNOWN", extracted_value=None, source_block_ids=[],
    )
    result = QuoteExtraction.model_validate(payload)
    assert result.fields.currency.extracted_value is None
    assert result.fields.unit_price.extracted_value == "4.60"


def test_numeric_included_tooling_preserves_sourced_unknown_not_zero() -> None:
    payload = deepcopy(load_recorded_outputs()["included-tooling"])
    source = json.loads((FIXTURES / "expected_blocks.json").read_text(encoding="utf-8"))
    text = dict(source["included_tooling.pdf"]["blocks"])["p1-b7"]
    assert "included in unit price; no separate charge" in text
    payload["fields"]["tooling_cost"]["uncertainty"] = text + "; no separate numeric amount stated."
    field = QuoteExtraction.model_validate(payload).fields.tooling_cost
    assert field.state == "UNKNOWN"
    assert field.extracted_value is None
    assert field.conflicting_values == []
    assert field.source_block_ids == ["p1-b7"]
    assert field.uncertainty == text + "; no separate numeric amount stated."


@pytest.mark.parametrize("case_id,key,expected_sources", [
    ("missing-moq", "moq", []), ("missing-shipping", "shipping_cost", []),
    ("explicit-unknown", "sample_cost", ["p1-b8"]),
    ("explicit-unknown", "shipping_cost", ["p1-b11"]),
])
def test_numeric_missing_and_explicit_unknowns_keep_distinct_sources(
    case_id: str, key: str, expected_sources: list[str],
) -> None:
    field = getattr(QuoteExtraction.model_validate(load_recorded_outputs()[case_id]).fields, key)
    assert field.state == "UNKNOWN" and field.extracted_value is None
    assert field.source_block_ids == expected_sources
    assert field.conflicting_values == []


@pytest.mark.parametrize("key,values", [
    ("sample_cost", ["40", "45"]), ("packaging_cost", ["1.25", "2.50"]),
    ("quoted_quantity", [2000, 5000]), ("moq", [1000, 2000]),
    ("currency", ["USD", "AUD"]),
])
def test_numeric_synthetic_conflicts_preserve_alternative_source_pairing(
    key: str, values: list[str] | list[int],
) -> None:
    case = deepcopy(load_cases()[0])
    payload = deepcopy(load_recorded_outputs()[case["id"]])
    case["known"].pop(key, None)
    case["conflicts"][key] = [[values[0], ["p1-b8"]], [values[1], ["p1-b7"]]]
    payload["fields"][key] = {
        "state": "CONFLICT", "extracted_value": None, "source_block_ids": ["p1-b8", "p1-b7"],
        "uncertainty": "Synthetic sources disagree.", "conflicting_values": [
            {"value": values[0], "source_block_ids": ["p1-b8"]},
            {"value": values[1], "source_block_ids": ["p1-b7"]},
        ],
    }
    result = QuoteExtraction.model_validate(payload)
    assert result.model_dump(mode="json") == payload
    assert score_parsed_case(result, case)["conflict_detection"] == 1.0
    payload["fields"][key]["conflicting_values"][0]["source_block_ids"] = ["p1-b7"]
    payload["fields"][key]["conflicting_values"][1]["source_block_ids"] = ["p1-b8"]
    mutated = QuoteExtraction.model_validate(payload)
    validate_source_references(mutated, {f"p1-b{i}" for i in range(1, 15)} | {"p2-b4", "p2-b7"})
    assert score_parsed_case(mutated, case)["conflict_detection"] == 0.0


@pytest.mark.parametrize("key", ["unit_price", "currency", "quoted_quantity", "tooling_cost"])
def test_numeric_scorer_detects_in_document_but_misattributed_source(key: str) -> None:
    case = load_cases()[0]
    payload = deepcopy(load_recorded_outputs()[case["id"]])
    payload["fields"][key]["source_block_ids"] = ["p1-b1"]
    result = QuoteExtraction.model_validate(payload)
    blocks = json.loads((FIXTURES / "expected_blocks.json").read_text(encoding="utf-8"))
    validate_source_references(result, {ref for ref, _ in blocks[case["pdf"]]["blocks"]})
    scores = score_parsed_case(result, case)
    assert scores["source_block_accuracy"] < 1.0
    assert scores["numeric_accuracy"] == 1.0


@pytest.fixture
def harbor_case(tmp_path: Path) -> dict[str, Any]:
    from sourcepilot.ai.eval_baseline import parser_result

    case = deepcopy(load_cases()[0])
    assert case["id"] == "harbor-primary"
    blocks, checks = parser_result(case, tmp_path)
    assert blocks is not None and len(blocks) == 21
    assert all(check["passed"] for check in checks)
    return case


def quote_checks(case: dict[str, Any], payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    from sourcepilot.ai.eval_scoring import score_output

    return {check["name"]: check for check in score_output("quote_extraction", case, payload)}


@pytest.mark.parametrize("references,member,attributed", [
    (["p1-b5"], True, True),
    (["p1-b1"], True, False),  # Actual disclaimer omitted from expected citations.
    (["p2-b1"], True, False),
    (["p1-b5", "p1-b4"], True, False),
    (["p99-b1"], False, False),
    (["p1-b5", "p99-b1"], False, False),
])
def test_membership_does_not_replace_attribution(
    harbor_case: dict[str, Any], references: list[str], member: bool, attributed: bool,
) -> None:
    payload = deepcopy(load_recorded_outputs()["harbor-primary"])
    payload["fields"]["unit_price"]["source_block_ids"] = references
    checks = quote_checks(harbor_case, payload)
    assert checks["source_references"]["passed"] is member
    assert checks["field.unit_price.sources"]["passed"] is attributed
    assert checks["field.unit_price.value"]["passed"]
    if not attributed:
        assert not checks["field.unit_price.misattributed_evidence"]["passed"]


@pytest.mark.parametrize("references", [
    ["p1-b5"], ["p1-b7"], ["p1-b8"], ["p1-b11"],
    ["p1-b11", "p1-b8", "p1-b7", "p1-b5"], ["p1-b7", "p1-b8"],
])
def test_reviewed_currency_evidence_sets(harbor_case: dict[str, Any], references: list[str]) -> None:
    from sourcepilot.ai.quote_extraction_eval import metric_counts

    payload = deepcopy(load_recorded_outputs()["harbor-primary"])
    payload["fields"]["currency"]["source_block_ids"] = references
    checks = quote_checks(harbor_case, payload)
    counts = metric_counts(QuoteExtraction.model_validate(payload), harbor_case)
    assert checks["field.currency.sources"]["passed"]
    assert checks["source_block_accuracy"]["passed"]
    assert counts["source_block_accuracy"] == (21, 21)


@pytest.mark.parametrize("value,refs", [
    ("USD", ["p1-b4"]), ("USD", ["p1-b5", "p1-b1"]),
    ("AUD", ["p1-b7"]), ("EUR", ["p1-b11"]),
])
def test_currency_equivalence_rejects_irrelevant_and_wrong_currency(
    harbor_case: dict[str, Any], value: str, refs: list[str],
) -> None:
    payload = deepcopy(load_recorded_outputs()["harbor-primary"])
    payload["fields"]["currency"].update(extracted_value=value, source_block_ids=refs)
    checks = quote_checks(harbor_case, payload)
    assert not checks["field.currency.sources"]["passed"]
    if value != "USD":
        assert not checks["field.currency.value"]["passed"]


@pytest.mark.parametrize("value,qualification,refs,accepted", [
    ("GRS", "The document describes this as a synthetic record, current for this fictional supplier.", ["p2-b4"], True),
    ("GRS", None, ["p2-b4"], False),
    ("GRS", "Current for this supplier.", ["p2-b4"], False),
    ("GRS", "Synthetic record; not current for this fictional supplier.", ["p2-b4"], False),
    ("GRS", "The document describes this as a synthetic record, current for this fictional supplier. Independently verified.", ["p2-b4"], False),
    ("GRS", "The document describes this as a synthetic record, current for this fictional supplier.", ["p2-b3"], False),
    ("GRS verified", "The document describes this as a synthetic record, current for this fictional supplier.", ["p2-b4"], False),
])
def test_grs_requires_exact_reviewed_qualification_and_evidence(
    harbor_case: dict[str, Any], value: str, qualification: str | None,
    refs: list[str], accepted: bool,
) -> None:
    from sourcepilot.ai.quote_extraction_eval import metric_counts

    payload = deepcopy(load_recorded_outputs()["harbor-primary"])
    payload["fields"]["certifications"].update(
        extracted_value=value, uncertainty=qualification, source_block_ids=refs,
    )
    checks = quote_checks(harbor_case, payload)
    assert checks["field.certifications.value"]["passed"] is accepted
    assert checks["field_accuracy"]["passed"] is accepted
    assert metric_counts(QuoteExtraction.model_validate(payload), harbor_case)["field_accuracy"] == (
        21 if accepted else 20, 21,
    )
    if not accepted:
        assert checks["field.certifications.unresolved_support"]["critical"]


@pytest.mark.parametrize("value,accepted", [
    ("Import duties are not included", True), ("IMPORT DUTIES ARE NOT INCLUDED", True),
    ("import duties are included", False), ("import duties are not included except VAT", False),
    ("import duties excluded", False),
])
def test_exclusion_equivalence_only_changes_case(
    harbor_case: dict[str, Any], value: str, accepted: bool,
) -> None:
    payload = deepcopy(load_recorded_outputs()["harbor-primary"])
    payload["fields"]["exclusions"]["extracted_value"] = value
    checks = quote_checks(harbor_case, payload)
    assert checks["field.exclusions.value"]["passed"] is accepted
    assert checks["field_accuracy"]["passed"] is accepted


def test_disclaimer_is_assignment_error_with_unknown_correctness_preserved(
    harbor_case: dict[str, Any],
) -> None:
    from sourcepilot.ai.quote_extraction_eval import metric_counts

    payload = deepcopy(load_recorded_outputs()["harbor-primary"])
    assert all(check["passed"] for check in quote_checks(harbor_case, payload).values())
    payload["fields"]["supplier_notes"].update(
        state="KNOWN", extracted_value="Synthetic demo quote - not a real supplier offer",
        source_block_ids=["p1-b1", "p2-b1"],
    )
    checks = quote_checks(harbor_case, payload)
    counts = metric_counts(QuoteExtraction.model_validate(payload), harbor_case)
    assert checks["source_references"]["passed"]
    assert checks["field.supplier_notes.field_assignment"]["critical"]
    assert not checks["field.supplier_notes.unknown"]["passed"]
    assert counts["field_accuracy"] == counts["source_block_accuracy"] == (20, 21)
    assert counts["unknown_detection"] == (6, 7)
    assert counts["hallucination_rate"] == (0, 7)
    assert counts["expected_unknown_known_rate"] == (1, 7)
    assert counts["unsupported_value_rate"] == counts["unresolved_support_rate"] == (0, 21)


@pytest.mark.parametrize("key,value,refs,classification", [
    ("packaging_cost", "40", ["p1-b8"], "field_assignment"),
    ("unit_price", "2000", ["p1-b4"], "field_assignment"),
    ("packaging_cost", "999", ["p1-b8"], "unsupported_value"),
    ("unit_price", "999", ["p1-b5"], "unsupported_value"),
    ("warranty", "Lifetime warranty", ["p1-b1"], "unresolved_support"),
    ("supplier_notes", "Synthetic demo quote - not a real supplier offer. Free samples.", ["p1-b1"], "unresolved_support"),
    ("compliance_notes", "Synthetic demo quote - not a real supplier offer", ["p1-b1"], "unresolved_support"),
])
def test_invention_assignment_and_unresolved_text_remain_critical(
    harbor_case: dict[str, Any], key: str, value: str, refs: list[str], classification: str,
) -> None:
    from sourcepilot.ai.quote_extraction_eval import metric_counts

    payload = deepcopy(load_recorded_outputs()["harbor-primary"])
    payload["fields"][key].update(state="KNOWN", extracted_value=value, source_block_ids=refs)
    checks = quote_checks(harbor_case, payload)
    counts = metric_counts(QuoteExtraction.model_validate(payload), harbor_case)
    assert checks["source_references"]["passed"]
    assert not checks["field_accuracy"]["passed"]
    finding = checks[f"field.{key}.{classification}"]
    assert finding["critical"] and not finding["passed"]
    if classification == "unsupported_value":
        assert counts["unsupported_value_rate"] == (1, 21)
        assert counts["hallucination_rate"] == (0 if key == "unit_price" else 1, 7)
    if classification == "unresolved_support":
        assert counts["unresolved_support_rate"] == (1, 21)


@pytest.mark.parametrize("mutation", ["missing", "pdf", "hash", "incomplete", "text", "duplicate"])
def test_wrong_or_incomplete_document_context_is_scorer_error(
    harbor_case: dict[str, Any], mutation: str,
) -> None:
    from sourcepilot.ai.quote_extraction_eval import QuoteScorerContextError

    context = harbor_case["_scoring_document"]
    if mutation == "missing":
        harbor_case.pop("_scoring_document")
    elif mutation == "pdf":
        context["pdf"] = "willow_primary.pdf"
    elif mutation == "hash":
        context["sha256"] = "0" * 64
    elif mutation == "incomplete":
        context["blocks"].pop()
    elif mutation == "text":
        # Same ID, wrong supplier's price.
        context["blocks"][4][1] = "Unit price: USD 4.20"
    else:
        context["blocks"].append(context["blocks"][0])
    with pytest.raises(QuoteScorerContextError):
        quote_checks(harbor_case, load_recorded_outputs()["harbor-primary"])


def test_conflict_alternatives_require_membership_and_correct_pairing(
    tmp_path: Path,
) -> None:
    from sourcepilot.ai.eval_baseline import parser_result

    case = next(case for case in load_cases() if case["id"] == "conflicting-lead-time")
    parser_result(case, tmp_path)
    payload = deepcopy(load_recorded_outputs()[case["id"]])
    assert all(check["passed"] for check in quote_checks(case, payload).values())
    field = payload["fields"]["production_lead_time"]
    first, second = field["conflicting_values"]
    first["source_block_ids"], second["source_block_ids"] = second["source_block_ids"], first["source_block_ids"]
    checks = quote_checks(case, payload)
    assert checks["source_references"]["passed"]
    assert not checks["source_block_accuracy"]["passed"]
    assert not checks["conflict_detection"]["passed"]
    assert not checks["field.production_lead_time.conflict"]["passed"]
    assert not checks["field_accuracy"]["passed"]
    first["source_block_ids"] = ["p99-b1"]
    field["source_block_ids"] = first["source_block_ids"] + second["source_block_ids"]
    assert not quote_checks(case, payload)["source_references"]["passed"]


def test_wrong_document_with_overlapping_ids_cannot_supply_context(
    harbor_case: dict[str, Any], tmp_path: Path,
) -> None:
    from sourcepilot.ai.eval_baseline import parser_result
    from sourcepilot.ai.quote_extraction_eval import QuoteScorerContextError

    willow = next(case for case in load_cases() if case["id"] == "willow-primary")
    parser_result(willow, tmp_path)
    assert "p1-b5" in dict(willow["_scoring_document"]["blocks"])
    harbor_case["_scoring_document"] = willow["_scoring_document"]
    with pytest.raises(QuoteScorerContextError):
        quote_checks(harbor_case, load_recorded_outputs()["harbor-primary"])


@pytest.mark.parametrize("field", ["currency", "certifications", "exclusions", "supplier_notes"])
def test_harbor_rules_do_not_apply_to_another_case(
    harbor_case: dict[str, Any], field: str,
) -> None:
    from sourcepilot.ai.quote_extraction_eval import HARBOR_QUALIFICATION

    harbor_case["id"] = "another-case"
    payload = deepcopy(load_recorded_outputs()["harbor-primary"])
    replacement = {
        "currency": ("USD", ["p1-b7"], None),
        "certifications": ("GRS", ["p2-b4"], HARBOR_QUALIFICATION),
        "exclusions": ("Import duties are not included", ["p2-b7"], None),
        "supplier_notes": ("Synthetic demo quote - not a real supplier offer", ["p1-b1"], None),
    }
    value, refs, uncertainty = replacement[field]
    payload["fields"][field].update(
        state="KNOWN", extracted_value=value, source_block_ids=refs, uncertainty=uncertainty,
    )
    checks = quote_checks(harbor_case, payload)
    if field == "currency":
        assert not checks["field.currency.sources"]["passed"]
    elif field == "supplier_notes":
        assert checks["field.supplier_notes.unresolved_support"]["critical"]
    else:
        assert not checks[f"field.{field}.value"]["passed"]


@pytest.mark.parametrize("case_id,key,refs", [
    ("missing-moq", "moq", ["p1-b4"]),
    ("missing-shipping", "shipping_cost", ["p1-b4"]),
    ("explicit-unknown", "sample_cost", ["p1-b8"]),
])
def test_unknown_does_not_become_invented_numeric(
    tmp_path: Path, case_id: str, key: str, refs: list[str],
) -> None:
    from sourcepilot.ai.eval_baseline import parser_result
    from sourcepilot.ai.quote_extraction_eval import metric_counts

    case = next(case for case in load_cases() if case["id"] == case_id)
    parser_result(case, tmp_path)
    payload = deepcopy(load_recorded_outputs()[case_id])
    assert all(check["passed"] for check in quote_checks(case, payload).values())
    payload["fields"][key].update(
        state="KNOWN", extracted_value=1 if key == "moq" else "0", source_block_ids=refs,
    )
    checks = quote_checks(case, payload)
    counts = metric_counts(QuoteExtraction.model_validate(payload), case)
    assert not checks[f"field.{key}.unknown"]["passed"]
    assert not checks["unknown_detection"]["passed"]
    assert checks[f"field.{key}.unsupported_value"]["critical"]
    assert counts["hallucination_rate"][0] == 1


@pytest.fixture(scope="module")
def retained_cases() -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    from sourcepilot.ai import eval_baseline as baseline

    evidence = FIXTURES.parent / "retained_quote_eval" / "quote-v2-results.json"
    report = json.loads(evidence.read_text(encoding="utf-8"))
    expected = baseline.load_scope(["quote_extraction"])["quote_extraction"]
    assert len(report["cases"]) == len(expected) == 12
    assert {item["id"] for item in report["cases"]} == {case["id"] for case in expected}
    outputs = {item["id"]: item["output"] for item in report["cases"] if item.get("output")}
    cases = load_cases()
    assert len(cases) == len(outputs) == 10
    assert set(outputs) == {case["id"] for case in cases}
    with TemporaryDirectory() as directory:
        for case in cases:
            baseline.parser_result(case, Path(directory))
    return {case["id"]: (case, outputs[case["id"]]) for case in cases}


@pytest.mark.parametrize("case_id", [case["id"] for case in load_cases()])
def test_approved_retained_assignments_stay_critical(
    retained_cases: dict[str, Any],
    case_id: str,
) -> None:
    from sourcepilot.ai.quote_extraction_eval import field_evaluations, metric_counts

    case, payload = retained_cases[case_id]
    result = QuoteExtraction.model_validate(payload)
    evaluated = field_evaluations(result, case)
    keys = ["supplier_notes"] + (["compliance_notes"] if case_id == "quantity-mismatch" else [])
    checks = quote_checks(case, payload)
    for key in keys:
        assert evaluated[key]["classification"] == "field_assignment"
        assert not evaluated[key]["field_match"] and not evaluated[key]["source_match"]
        assert checks[f"field.{key}.field_assignment"]["critical"]
        assert not checks[f"field.{key}.unknown"]["passed"]
    assert metric_counts(result, case)["unsupported_value_rate"] == (0, 21)
    assert metric_counts(result, case)["unresolved_support_rate"] == (0, 21)


@pytest.mark.parametrize("case_id", [case["id"] for case in load_cases()])
@pytest.mark.parametrize(
    "mutation", ["addition", "negation", "uncertainty", "refs", "field", "case", "text"]
)
def test_assignment_recognition_does_not_excuse_new_claims_or_wrong_evidence(
    retained_cases: dict[str, Any],
    case_id: str,
    mutation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sourcepilot.ai.quote_extraction_eval import document_blocks, field_evaluations

    original, output = retained_cases[case_id]
    case, payload = deepcopy(original), deepcopy(output)
    field = payload["fields"]["supplier_notes"]
    key = "supplier_notes"
    if mutation == "addition":
        field["extracted_value"] += ". Free samples."
    elif mutation == "negation":
        field["extracted_value"] = (
            field["extracted_value"].replace("NOT", "IS").replace("not", "is")
        )
    elif mutation == "uncertainty":
        field["uncertainty"] = "Free samples"
    elif mutation == "refs":
        field["source_block_ids"] = ["p1-b4"]
    elif mutation == "field":
        key = "warranty"
        payload["fields"][key] = field
    elif mutation == "case":
        case["id"] = "another-case"
    else:
        from sourcepilot.ai import quote_extraction_eval

        blocks = document_blocks(case)
        for ref in field["source_block_ids"]:
            blocks[ref] = "SYNTHETIC DEMO QUOTE - A REAL SUPPLIER OFFER"
        monkeypatch.setattr(quote_extraction_eval, "document_blocks", lambda _: blocks)
    evaluated = field_evaluations(QuoteExtraction.model_validate(payload), case)
    assert evaluated[key]["classification"] == "unresolved_support"
    assert quote_checks(case, payload)[f"field.{key}.unresolved_support"]["critical"]


@pytest.mark.parametrize(
    "case_id", [case["id"] for case in load_cases() if case["id"] != "harbor-primary"]
)
@pytest.mark.parametrize(
    "mutation",
    [
        "approved",
        "original",
        "subset",
        "extra",
        "absent",
        "currency",
        "text",
        "case",
        "pdf",
        "hash",
        "request",
        "blocks",
    ],
)
def test_nine_currency_alternatives_are_complete_and_source_bound(
    retained_cases: dict[str, Any],
    case_id: str,
    mutation: str,
) -> None:
    from sourcepilot.ai.quote_extraction_eval import (
        QuoteScorerContextError,
        document_blocks,
        field_evaluations,
        source_rule,
    )

    original, output = retained_cases[case_id]
    case, payload = deepcopy(original), deepcopy(output)
    field = payload["fields"]["currency"]
    if mutation == "original":
        field["source_block_ids"] = ["p1-b5"]
    elif mutation == "subset":
        field["source_block_ids"] = [field["source_block_ids"][-1]]
    elif mutation in {"extra", "absent"}:
        field["source_block_ids"].append("p1-b4" if mutation == "extra" else "p99-b1")
    elif mutation == "currency":
        field["extracted_value"] = "EUR"
    elif mutation == "case":
        case["id"] = "another-case"
    elif mutation == "text":
        blocks = document_blocks(case)
        blocks[field["source_block_ids"][-1]] = "Unrelated USD statement"
        assert source_rule("currency", field, case, blocks) is None
        return
    elif mutation in {"pdf", "hash", "request", "blocks"}:
        context = case["_scoring_document"]
        if mutation == "pdf":
            context["pdf"] = "harbor_primary.pdf"
        elif mutation == "hash":
            context["sha256"] = "0" * 64
        elif mutation == "request":
            case["request_hash"] = "0" * 64
        else:
            context["blocks"][0][1] = "Changed notice"
        with pytest.raises(QuoteScorerContextError):
            quote_checks(case, payload)
        return
    field["source_block_ids"].reverse()
    accepted = mutation in {"approved", "original"}
    evaluated = field_evaluations(QuoteExtraction.model_validate(payload), case)["currency"]
    checks = quote_checks(case, payload)
    assert evaluated["source_match"] is accepted
    assert checks["field.currency.sources"]["passed"] is accepted
    if mutation == "approved":
        assert (
            json.loads(checks["field.currency.sources"]["detail"])["rule"]
            == f"{case_id}_currency_{field['extracted_value'].lower()}"
        )
    if mutation == "currency":
        assert checks["field.currency.unsupported_value"]["critical"]


@pytest.mark.parametrize(
    "case_id,key",
    [
        (case_id, "exclusions")
        for case_id in [
            "missing-shipping",
            "included-tooling",
            "missing-moq",
            "quantity-mismatch",
            "non-usd",
            "explicit-unknown",
        ]
    ]
    + [("quantity-mismatch", "certifications")],
)
@pytest.mark.parametrize(
    "mutation",
    [
        "approved",
        "exact",
        "negation",
        "qualification",
        "addition",
        "refs",
        "extra",
        "case",
        "uncertainty",
        "text",
    ],
)
def test_seven_text_aliases_preserve_meaning_and_sources(
    retained_cases: dict[str, Any],
    case_id: str,
    key: str,
    mutation: str,
) -> None:
    from sourcepilot.ai.quote_extraction_eval import document_blocks, field_evaluations, value_rule

    original, output = retained_cases[case_id]
    case, payload = deepcopy(original), deepcopy(output)
    field = payload["fields"][key]
    if mutation == "exact":
        field["extracted_value"] = case["known"][key][0]
    elif mutation == "negation":
        field["extracted_value"] = (
            field["extracted_value"]
            .replace("not included", "included")
            .replace("current", "expired")
        )
    elif mutation == "qualification":
        field["extracted_value"] = (
            "GRS verified" if key == "certifications" else "IMPORT DUTIES ARE NOT INCLUDED"
        )
    elif mutation == "addition":
        field["extracted_value"] += ". Independently verified."
    elif mutation in {"refs", "extra"}:
        field["source_block_ids"] = (
            ["p1-b4"] if mutation == "refs" else field["source_block_ids"] + ["p1-b4"]
        )
    elif mutation == "case":
        case["id"] = "another-case"
    elif mutation == "uncertainty":
        field["uncertainty"] = "Independently verified"
    elif mutation == "text":
        blocks = document_blocks(case)
        blocks[field["source_block_ids"][0]] = "Unrelated text"
        assert value_rule(key, field, case, blocks) is None
        return
    accepted = mutation in {"approved", "exact"}
    evaluated = field_evaluations(QuoteExtraction.model_validate(payload), case)[key]
    assert evaluated["field_match"] is accepted
    assert quote_checks(case, payload)[f"field.{key}.value"]["passed"] is accepted


@pytest.mark.parametrize(
    "value",
    [
        "GRS verified",
        "GRS record; current for this fictional supplier",
        "Synthetic GRS record; current",
        "Synthetic GRS record; expired for this fictional supplier",
        "Synthetic GRS record; current for this fictional supplier. Free samples.",
    ],
)
def test_compliance_duplicate_requires_all_qualifications(
    retained_cases: dict[str, Any], value: str
) -> None:
    from sourcepilot.ai.quote_extraction_eval import field_evaluations

    case, output = retained_cases["quantity-mismatch"]
    payload = deepcopy(output)
    payload["fields"]["compliance_notes"]["extracted_value"] = value
    assert (
        field_evaluations(QuoteExtraction.model_validate(payload), case)["compliance_notes"][
            "classification"
        ]
        == "unresolved_support"
    )


@pytest.mark.parametrize("case_id", ["willow-primary", "quantity-mismatch"])
def test_retained_unicode_is_an_em_dash_not_mojibake(
    retained_cases: dict[str, Any], case_id: str
) -> None:
    case, output = retained_cases[case_id]
    value = output["fields"]["supplier_notes"]["extracted_value"]
    assert "\u2014" in value
    payload = deepcopy(output)
    payload["fields"]["supplier_notes"]["extracted_value"] = value.replace(
        "\u2014", "\u00e2\u20ac\u201d"
    )
    assert quote_checks(case, payload)["field.supplier_notes.unresolved_support"]["critical"]


@pytest.mark.parametrize("mutation", ["case", "field", "refs", "extra", "uncertainty", "text"])
def test_compliance_assignment_is_fixture_and_source_specific(
    retained_cases: dict[str, Any],
    mutation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sourcepilot.ai import quote_extraction_eval as scorer

    original, output = retained_cases["quantity-mismatch"]
    case, payload = deepcopy(original), deepcopy(output)
    key = "compliance_notes"
    field = payload["fields"][key]
    if mutation == "case":
        case["id"] = "another-case"
    elif mutation == "field":
        key = "warranty"
        payload["fields"][key] = field
    elif mutation == "refs":
        field["source_block_ids"] = ["p1-b4"]
    elif mutation == "extra":
        field["source_block_ids"].append("p1-b4")
    elif mutation == "uncertainty":
        field["uncertainty"] = "Free samples"
    else:
        blocks = scorer.document_blocks(case)
        blocks["p2-b4"] = "GRS verified"
        monkeypatch.setattr(scorer, "document_blocks", lambda _: blocks)
    evaluated = scorer.field_evaluations(QuoteExtraction.model_validate(payload), case)
    assert evaluated[key]["classification"] == "unresolved_support"
    assert quote_checks(case, payload)[f"field.{key}.unresolved_support"]["critical"]
