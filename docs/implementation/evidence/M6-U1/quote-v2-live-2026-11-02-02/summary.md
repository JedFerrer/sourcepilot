# SourcePilot live eval baseline

Status: **ERROR**; exit 2.
Scope: quote_extraction. Full scope: False.
Accounted for: 12/12; complete: True.

Exit zero is execution completion, not live model-quality approval.
Automated completion does not prove free-text narrative groundedness.

| Category | Case | Status | Exact failures / heuristic signals |
| --- | --- | --- | --- |
| quote_extraction | harbor-primary | PROVIDER_ERROR | exact: runtime_completion |
| quote_extraction | willow-primary | PROVIDER_ERROR | exact: runtime_completion |
| quote_extraction | moss-primary | PROVIDER_ERROR | exact: runtime_completion |
| quote_extraction | missing-shipping | PROVIDER_ERROR | exact: runtime_completion |
| quote_extraction | conflicting-lead-time | PROVIDER_ERROR | exact: runtime_completion |
| quote_extraction | included-tooling | PROVIDER_ERROR | exact: runtime_completion |
| quote_extraction | missing-moq | PROVIDER_ERROR | exact: runtime_completion |
| quote_extraction | quantity-mismatch | PROVIDER_ERROR | exact: runtime_completion |
| quote_extraction | non-usd | PROVIDER_ERROR | exact: runtime_completion |
| quote_extraction | explicit-unknown | PROVIDER_ERROR | exact: runtime_completion |
| quote_extraction | unsupported-image-only | EXPECTED_REJECTION |  |
| quote_extraction | malformed-pdf | EXPECTED_REJECTION |  |

## Exact deterministic assertions (passed / checked)

| Category | Assertion | Counts |
| --- | --- | --- |
| quote_extraction | parser_rejection | 2 / 2 |
| quote_extraction | runtime_completion | 0 / 10 |

## Measured metrics (numerator / denominator)

| Category | Metric | Kind | Counts | Measured cases |
| --- | --- | --- | --- | --- |

Zero denominators are not applicable. Exact assertion pass counts are separate in results.json.
Failed runtime cases remain in case/status totals even when extracted-value metrics are unavailable.

## Heuristic signals (triggered / inspected)

A non-trigger is not a factual-groundedness pass. These are bounded warning cues.

| Category | Signal | Counts |
| --- | --- | --- |

## Critical findings

- None in accepted recorded outputs; expected negative controls remain in the case table.

## Human review required — PENDING

0 difficult narrative examples require a person's judgment. No result has been recorded.

| Example | Review criterion |
| --- | --- |

Source: apps/api/evals/human_review/narrative_cases.json.
No production tuning or release acceptance is implied by this baseline.
