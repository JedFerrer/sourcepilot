"""Parser-only regression coverage for the M3-U5 synthetic PDF corpus."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pymupdf
import pytest

from sourcepilot.documents.parse_pdf import NoExtractableTextError, parse_pdf_snapshot

FIXTURES = Path(__file__).parent / "fixtures" / "quote_pdfs"
TEXT_PDFS = {
    "harbor_primary.pdf",
    "willow_primary.pdf",
    "moss_primary.pdf",
    "missing_shipping.pdf",
    "conflicting_lead_time.pdf",
    "included_tooling.pdf",
    "missing_moq.pdf",
    "quantity_mismatch.pdf",
    "non_usd.pdf",
    "explicit_unknown.pdf",
}


def _expected() -> dict[str, Any]:
    return json.loads((FIXTURES / "expected_blocks.json").read_text(encoding="utf-8"))


def _expected_text(name: str) -> list[str]:
    return [text for _, text in _expected()[name]["blocks"]]


@pytest.mark.parametrize("name", sorted(TEXT_PDFS))
def test_versioned_quote_pdf_parser_blocks_are_repeatable(name: str, tmp_path: Path) -> None:
    pdf = FIXTURES / name
    expected = _expected()[name]
    original_hash = hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert pdf.stat().st_size <= 10_000_000
    with pymupdf.open(pdf) as document:
        assert document.is_pdf and not document.needs_pass
        assert document.page_count == expected["page_count"]
        assert document.page_count <= 15

    for iteration in range(2):
        blocks = parse_pdf_snapshot(
            pdf, tmp_path / f"blocks-{iteration}.json", timeout_seconds=10,
            max_pages=15, expected_pages=expected["page_count"],
        )
        assert [[block.reference, block.text] for block in blocks] == expected["blocks"]
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == original_hash


def test_corpus_is_complete_synthetic_and_has_primary_tradeoffs() -> None:
    assert {path.name for path in FIXTURES.glob("*.pdf")} == TEXT_PDFS | {"image_only.pdf", "malformed.pdf"}
    assert set(_expected()) == TEXT_PDFS
    for name in TEXT_PDFS:
        pages = _expected()[name]["page_count"]
        blocks = _expected()[name]["blocks"]
        assert pages in {1, 2}
        assert blocks[0] == ["p1-b1", "SYNTHETIC DEMO QUOTE - NOT A REAL SUPPLIER OFFER"]
        assert all("SYNTHETIC DEMO QUOTE" in text for ref, text in blocks if ref.endswith("-b1"))

    harbor = _expected_text("harbor_primary.pdf")
    willow = _expected_text("willow_primary.pdf")
    moss = _expected_text("moss_primary.pdf")
    for texts in (harbor, willow, moss):
        assert "Quoted quantity: 2,000 units" in texts
        assert sum(text.startswith("Unit price: USD ") for text in texts) == 1
    assert "Unit price: USD 4.60" in harbor
    assert "Unit price: USD 4.20" in willow
    assert "Unit price: USD 4.45" in moss
    assert "Production lead time: 32 days after sample approval" in harbor
    assert "Production lead time: 40 days after sample approval" in willow
    assert "Production lead time: 25 days after sample approval" in moss
    assert "Tooling/setup cost: USD 600" in moss
    assert "Synthetic GRS record: current for this fictional supplier" in harbor
    assert "Synthetic material sheet: recycled-polyester bag production" in harbor
    assert "Preferred GRS certification: not stated in this quote" in willow


def test_unknown_sample_time_is_distinct_from_missing_shipping() -> None:
    moss = _expected_text("moss_primary.pdf")
    missing_shipping = _expected_text("missing_shipping.pdf")
    assert "Sample lead time: not stated in this quote" in moss
    assert "Shipping cost: USD 360 to Manila" in moss
    assert "Shipping time: 10 days after production" in moss
    assert "Sample lead time: 7 days" in missing_shipping
    assert not any(text.startswith(("Shipping cost:", "Shipping time:"))
                   for text in missing_shipping)


def test_conflicting_lead_time_remains_two_separate_source_blocks() -> None:
    expected = _expected()["conflicting_lead_time.pdf"]["blocks"]
    assert [ref for ref, text in expected if text.startswith("Production lead time:")] == [
        "p1-b10", "p2-b3",
    ]
    assert [text for _, text in expected if text.startswith("Production lead time:")] == [
        "Production lead time: 25 days after sample approval",
        "Production lead time: 30-35 days after sample approval",
    ]


def test_image_only_pdf_is_visibly_synthetic_but_has_no_text_layer(tmp_path: Path) -> None:
    pdf = FIXTURES / "image_only.pdf"
    assert pdf.stat().st_size <= 10_000_000
    with pymupdf.open(pdf) as document:
        assert document.page_count == 1
        metadata = document.metadata
        assert metadata is not None and "Synthetic" in metadata["title"]
        assert document[0].get_images(full=True)
        assert document[0].get_text("text") == ""
    with pytest.raises(NoExtractableTextError, match="no extractable text"):
        parse_pdf_snapshot(
            pdf, tmp_path / "image-only.json", timeout_seconds=10,
            max_pages=15, expected_pages=1,
        )
