# Synthetic quote PDF fixtures

Every supplier, quotation, price, and supporting claim in these PDFs is fictional
demo data. None describes a real supplier or an actual offer.

Use the tracked PDFs directly; generating them is not a prerequisite for startup,
tests or the [manual demo](../../../../../docs/local-development.md#manual-demo-walkthrough).
Shared [local setup](../../../../../docs/local-development.md#configure-and-start)
covers dependencies. Uploading a supported PDF through the app invokes paid AI
extraction; reading these files or running parser-only tests does not.

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

## Usage and optional fixture maintenance

[Parser fixture tests](../../test_quote_pdf_fixtures.py) check the PDFs against
`expected_blocks.json`; [quote extraction eval tests](../../test_quote_extraction_eval.py)
use them with tracked responses and scoring cases. After installing dependencies,
run the parser-only check from `apps/api`:

```text
uv run --no-sync pytest tests/test_quote_pdf_fixtures.py
```

This command needs no model credentials or database. Commands here are source-checked
instructions, not checks executed for this documentation update.

**Optional overwrite operation:** `generate.py` rewrites the original six tracked
PDFs (the first six table rows). Run only when deliberately maintaining fixtures,
from `apps/api` with the existing PyMuPDF dependency:

```text
uv run --no-sync python tests/fixtures/quote_pdfs/generate.py
```

Review parser output and update `expected_blocks.json` deliberately if any
fixture content or the approved parser behavior changes. The unsupported image
case must continue to raise `NoExtractableTextError`.

`generate_m6.py` rewrites only the six additions (the final six table rows), leaving
the original six PDFs unchanged. From `apps/api`:

```text
uv run --no-sync python tests/fixtures/quote_pdfs/generate_m6.py
```

Neither generator updates `expected_blocks.json` automatically. Review generated
changes and parser expectations together; do not regenerate historical outputs
merely to make a test pass. See the [eval guide](../../../evals/README.md) for AI
evaluation inputs and quality limits.

The corpus contains ten text-extractable PDFs and two expected rejections; the
malformed input intentionally cannot contain a valid rendered page.
