"""Regenerate only the six repository-owned synthetic quote PDF fixtures.

Run from apps/api with: uv run --no-sync python tests/fixtures/quote_pdfs/generate.py
The checked-in expected_blocks.json is reviewed separately and is not generated here.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
NOTICE = "SYNTHETIC DEMO QUOTE - NOT A REAL SUPPLIER OFFER"
REQUEST = "Product: recycled-polyester cosmetic travel bags with custom logo"

HARBOR_PAGE_1 = [
    NOTICE,
    "Harbor Pouch Works | Quote HPW-2000 | 27 September 2026",
    REQUEST,
    "Quoted quantity: 2,000 units",
    "Unit price: USD 4.60",
    "Minimum order quantity: 1,000 units",
    "Tooling/setup cost: USD 150",
    "Sample cost: USD 40",
    "Sample lead time: 7 days",
    "Production lead time: 32 days after sample approval",
    "Shipping cost: USD 320 to Manila",
    "Shipping time: 12 days after production",
    "Payment terms: 30% deposit, 70% before dispatch",
    "Quote validity: 30 days",
]
HARBOR_PAGE_2 = [
    NOTICE,
    "Harbor Pouch Works | Quotation supporting details",
    "Material: recycled polyester; logo: screen print",
    "Synthetic GRS record: current for this fictional supplier",
    "Synthetic material sheet: recycled-polyester bag production",
    "Synthetic branding sheet: custom screen-printed logos",
    "Exclusion: import duties are not included",
]
WILLOW_PAGE = [
    NOTICE,
    "Willow Stitch Studio | Quote WSS-2000 | 27 September 2026",
    REQUEST,
    "Quoted quantity: 2,000 units",
    "Unit price: USD 4.20",
    "Minimum order quantity: 1,800 units",
    "Tooling/setup cost: USD 100",
    "Sample cost: USD 35",
    "Sample lead time: 10 days",
    "Production lead time: 40 days after sample approval",
    "Shipping cost: USD 280 to Manila",
    "Shipping time: 14 days after production",
    "Preferred GRS certification: not stated in this quote",
    "Payment terms: 50% deposit, 50% before dispatch",
    "Quote validity: 30 days",
]
MOSS_PAGE = [
    NOTICE,
    "Moss Thread Bags | Quote MTB-2000 | 27 September 2026",
    REQUEST,
    "Quoted quantity: 2,000 units",
    "Unit price: USD 4.45",
    "Minimum order quantity: 800 units",
    "Tooling/setup cost: USD 600",
    "Sample cost: USD 45",
    "Sample lead time: not stated in this quote",
    "Production lead time: 25 days after sample approval",
    "Shipping cost: USD 360 to Manila",
    "Shipping time: 10 days after production",
    "Material: recycled polyester; logo: custom print",
    "Payment terms: 40% deposit, 60% before dispatch",
    "Quote validity: 21 days",
]


def _write_text_pdf(filename: str, pages: list[list[str]]) -> None:
    document = pymupdf.open()
    try:
        for lines in pages:
            page = document.new_page(width=595, height=842)
            for index, line in enumerate(lines):
                page.insert_text((45, 55 + index * 31), line, fontsize=10, fontname="helv")
        document.set_metadata({"title": f"Synthetic quote fixture: {filename}",
                               "creator": "SourcePilot fixture generator"})
        document.save(HERE / filename, garbage=4, deflate=True, reproducible=True)
    finally:
        document.close()


def _write_image_only_pdf() -> None:
    source = pymupdf.open()
    target = pymupdf.open()
    try:
        page = source.new_page(width=595, height=842)
        for index, line in enumerate([
            NOTICE,
            "IMAGE-ONLY SCANNED QUOTE FIXTURE",
            "No selectable text layer is present in the saved PDF.",
        ]):
            page.insert_text((45, 55 + index * 40), line, fontsize=12, fontname="helv")
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
        target_page = target.new_page(width=595, height=842)
        target_page.insert_image(target_page.rect, pixmap=pixmap)
        target.set_metadata({"title": "Synthetic image-only quote fixture",
                             "creator": "SourcePilot fixture generator"})
        target.save(HERE / "image_only.pdf", garbage=4, deflate=True, reproducible=True)
    finally:
        source.close()
        target.close()


def main() -> None:
    _write_text_pdf("harbor_primary.pdf", [HARBOR_PAGE_1, HARBOR_PAGE_2])
    _write_text_pdf("willow_primary.pdf", [WILLOW_PAGE])
    _write_text_pdf("moss_primary.pdf", [MOSS_PAGE])
    _write_text_pdf("missing_shipping.pdf", [[
        line for line in HARBOR_PAGE_1
        if not line.startswith(("Shipping cost:", "Shipping time:"))
    ], HARBOR_PAGE_2])
    _write_text_pdf("conflicting_lead_time.pdf", [MOSS_PAGE, [
        NOTICE,
        "Moss Thread Bags | Revised schedule note for quote MTB-2000",
        "Production lead time: 30-35 days after sample approval",
        "This conflicts with the 25-day production lead time on page 1.",
    ]])
    _write_image_only_pdf()


if __name__ == "__main__":
    main()
