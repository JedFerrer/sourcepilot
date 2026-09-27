# Synthetic quote PDF fixtures

Every supplier, quotation, price, and supporting claim in these PDFs is fictional
demo data. None describes a real supplier or an actual offer.

| File | Parser scenario |
| --- | --- |
| `harbor_primary.pdf` | Slightly higher unit price, acceptable lead time, strongest stated supporting details. |
| `willow_primary.pdf` | Lowest unit price, slower production, preferred GRS certification unstated. |
| `moss_primary.pdf` | Fastest production, higher tooling, sample lead time unstated; shipping cost and time stated. |
| `missing_shipping.pdf` | Harbor variant with shipping cost and time absent. |
| `conflicting_lead_time.pdf` | Moss variant with 25 days on page 1 and 30–35 days on page 2. |
| `image_only.pdf` | Visible synthetic notice rasterized into an image, with no PDF text layer. |

The primary three quote 2,000 units in USD. They are project-specific synthetic
offers; the supplier catalog's general terms are indicative rather than these
quotation values. `expected_blocks.json` stores only exact parser text, page
numbers, and `p<page>-b<block>` references. It contains no extracted quote
fields or AI-eval expectations.

Regenerate PDFs from `apps/api` with the existing PyMuPDF dependency:

```text
uv run --no-sync python tests/fixtures/quote_pdfs/generate.py
```

Review parser output and update `expected_blocks.json` deliberately if any
fixture content or the approved parser behavior changes. The unsupported image
case must continue to raise `NoExtractableTextError`.
