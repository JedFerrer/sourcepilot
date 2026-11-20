# Comparison advice fixtures

These tracked synthetic inputs exercise comparison advice, correction provenance
and currency conflict handling. They describe fictional sourcing records, not
real offers or a live-model quality baseline.

| File | Purpose |
| --- | --- |
| `corrected-pdf-snapshot.json` | Comparison snapshot retaining a user-corrected amount and unresolved currency conflict. |
| `corrected-pdf-confirmed.json` | Confirmed quote response used to check the snapshot against the saved correction. |
| `pdf-extracted-before-correction.json` | Original extraction response before the user correction. |
| `currency-conflict.pdf` | Original synthetic document for the correction/conflict scenario. |
| `manual-delivery-snapshot.json` | Retained comparison snapshot for the manual quote/delivery scenario. |
| `observed-v7-currency-contradiction.json` | Exact observed paragraph and factual context preserving a historical currency error. |
| `provenance.json` | Original identifiers, hashes and derivation rules for these inputs. |

The current 4.50 correction, original 4.22 extraction and unresolved USD/EUR
remain distinct. The observed currency contradiction remains a historical factual
failure. Keep these fixtures tracked; changes require review.

The `source` paths in `provenance.json` are historical identifiers for archived
originals, not links or files supplied by a fresh clone. The tracked fixtures are
self-contained regression inputs; running their tests requires no private records.

## Usage

Install API dependencies using the shared [local setup](../../../../../docs/local-development.md#configure-and-start).
Existing consumers include [correction/conflict tests](../../test_advice_corrected_conflict.py)
and [currency-grounding tests](../../test_currency_grounding_guidance.py).
For the focused correction/rendering check, run from `apps/api`:

```text
uv run --no-sync pytest tests/test_advice_corrected_conflict.py
```

This is a provider-free fixture check, not a command executed for this documentation
update. No regeneration or database setup is needed for that focused check.
Broader database-backed tests have separate [reset safeguards](../../../../../docs/local-development.md#migrations-and-persistence-tests).
See the [eval guide](../../../evals/README.md) for offline/live evaluation boundaries.
