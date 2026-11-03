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
| `included_tooling.pdf` | Tooling included in unit price; no invented separate numeric charge. |
| `missing_moq.pdf` | MOQ absent. |
| `quantity_mismatch.pdf` | Quote for 5,000 units against a 2,000-unit request. |
| `non_usd.pdf` | AUD values preserved. |
| `explicit_unknown.pdf` | Sample/shipping values explicitly unstated or to be confirmed. |
| `malformed.pdf` | Intentionally invalid synthetic PDF bytes; parser rejection. |

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

Regenerate only the six M6 additions with `uv run --no-sync python
tests/fixtures/quote_pdfs/generate_m6.py`. This leaves the original six PDFs unchanged.
The corpus contains ten text-extractable PDFs and two expected rejections; the
malformed input intentionally cannot contain a valid rendered page.
