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
