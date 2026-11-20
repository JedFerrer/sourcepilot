# Retained synthetic quote regressions

These inputs describe fictional suppliers and synthetic quotes. They preserve
captured outputs and historical failures for deterministic scorer regression tests;
they do not establish live-model quality or human approval.

- `harbor-extraction.json` retains the complete `fields` object.
- `harbor-inspection.json` retains only the historical assertion counts, 34/43.
- `harbor-outcome.json` retains only `case_id` and `classification` as a third immutable input.
- `quote-v2-results.json` retains pending human review and all 12 cases' IDs,
  assertions and outputs, including null outputs. Only willow-primary and
  quantity-mismatch also retain the first captured response's `output_text` for
  exact Unicode equality checks. The historical exact assertion total is 359/443;
  current rescoring is 375/427 with 52 critical findings and 11 field assignments.
- `provenance.json` records original identifiers, hashes, projection rules and
  the four data-file hashes. Source identifiers are historical provenance, not
  required files or links.

Tests use these tracked inputs directly, alongside the tracked eval datasets and
synthetic PDFs. No private archive, provider call or regenerated output is needed.
Missing or malformed inputs must fail. Do not remove failing cases or reinterpret
pending reviews as approvals. Operational timestamps, run IDs, provider diagnostics,
usage and approval history are excluded from these projections.

## Usage

Follow shared [API dependency setup](../../../../../docs/local-development.md#configure-and-start).
The existing [quote extraction eval tests](../../test_quote_extraction_eval.py)
load these files to compare historical assertions with current deterministic
rescoring. For the retained-assignment regression alone, run from `apps/api`:

```text
uv run --no-sync pytest tests/test_quote_extraction_eval.py::test_approved_retained_assignments_stay_critical
```

This provider-free selection uses tracked inputs and does not need a database or
regenerated reports. The command is source-checked, not an executed result for
this documentation update. See the [eval guide](../../../evals/README.md) for
metric definitions, offline baseline usage and separately opt-in paid live runs.
Retained results must remain unchanged when producing a new local rescore.

**Destructive reset for the full module:** other tests in that file use an
`engine` fixture that resets the separate test database. Before running the entire
module, follow the shared [test database safeguards](../../../../../docs/local-development.md#migrations-and-persistence-tests)
and load `TEST_DATABASE_URL` as described there.
