# SourcePilot live eval baseline

Status: **ERROR**; exit 2.
Scope: comparison, suggestion. Full scope: False.
Accounted for: 31/31; complete: True.

Exit zero is execution completion, not live model-quality approval.
Automated completion does not prove free-text narrative groundedness.

| Category | Case | Status | Exact failures / heuristic signals |
| --- | --- | --- | --- |
| comparison | meaningful-tradeoff | RUNTIME_ERROR | exact: runtime_completion |
| comparison | required-failure | QUALITY_FINDING | exact: analysis_contract_states_references, heuristic: bounded_comparison_narrative_signal |
| comparison | unknown-and-conflict | RUNTIME_ERROR | exact: runtime_completion |
| comparison | corrected-quote-provenance | QUALITY_FINDING | heuristic: bounded_comparison_narrative_signal |
| comparison | incomplete-evidence | RUNTIME_ERROR | exact: runtime_completion |
| comparison | omitted-required-failure | EXPECTED_REJECTION | exact: analysis_contract_states_references, heuristic: bounded_comparison_narrative_signal |
| comparison | invented-shipping-cost | EXPECTED_REJECTION | heuristic: bounded_comparison_narrative_signal |
| comparison | wrong-source-for-correction | EXPECTED_REJECTION | heuristic: bounded_comparison_narrative_signal |
| comparison | general-vs-project | RUNTIME_ERROR | exact: runtime_completion |
| comparison | mixed-currencies | RUNTIME_ERROR | exact: runtime_completion |
| comparison | unequal-quantities | PASS |  |
| comparison | required-conflict | QUALITY_FINDING | heuristic: bounded_comparison_narrative_signal |
| comparison | stale-comparison-no-model | EXPECTED_REJECTION |  |
| suggestion | clear-suggestion | RUNTIME_ERROR | exact: runtime_completion |
| suggestion | tie | QUALITY_FINDING | heuristic: bounded_suggestion_narrative_signal |
| suggestion | critical-unknown | RUNTIME_ERROR | exact: runtime_completion |
| suggestion | required-failure | RUNTIME_ERROR | exact: runtime_completion |
| suggestion | incomplete-evidence | RUNTIME_ERROR | exact: runtime_completion |
| suggestion | user-correction | QUALITY_FINDING | heuristic: bounded_suggestion_narrative_signal |
| suggestion | incomparable-prices | QUALITY_FINDING | heuristic: bounded_suggestion_narrative_signal |
| suggestion | invented-price | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | hidden-required-failure | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | wrong-correction-provenance | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | forced-critical-unknown | EXPECTED_REJECTION | exact: advice_contract_states_references, exact: allowed_suggestion_choice, heuristic: bounded_suggestion_narrative_signal |
| suggestion | numeric-score | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | objective-best-claim | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | unqualified-incomparable-price | EXPECTED_REJECTION | heuristic: incomparable_price_ranking_signal |
| suggestion | general-vs-project | QUALITY_FINDING | heuristic: bounded_suggestion_narrative_signal |
| suggestion | mixed-currencies | QUALITY_FINDING | exact: allowed_suggestion_choice, heuristic: bounded_suggestion_narrative_signal |
| suggestion | unequal-quantities | QUALITY_FINDING | exact: allowed_suggestion_choice, heuristic: bounded_suggestion_narrative_signal |
| suggestion | required-conflict | RUNTIME_ERROR | exact: runtime_completion |

## Exact deterministic assertions (passed / checked)

| Category | Assertion | Counts |
| --- | --- | --- |
| comparison | analysis_contract_states_references | 3 / 4 |
| comparison | runtime_completion | 0 / 5 |
| comparison | stale_no_model | 1 / 1 |
| suggestion | advice_contract_states_references | 6 / 6 |
| suggestion | allowed_suggestion_choice | 4 / 6 |
| suggestion | runtime_completion | 0 / 5 |

## Measured metrics (numerator / denominator)

| Category | Metric | Kind | Counts | Measured cases |
| --- | --- | --- | --- | --- |

Zero denominators are not applicable. Exact assertion pass counts are separate in results.json.
Failed runtime cases remain in case/status totals even when extracted-value metrics are unavailable.

## Heuristic signals (triggered / inspected)

A non-trigger is not a factual-groundedness pass. These are bounded warning cues.

| Category | Signal | Counts |
| --- | --- | --- |
| comparison | bounded_comparison_narrative_signal | 3 / 4 |
| comparison | incomparable_price_ranking_signal | 0 / 4 |
| comparison | lead_time_context_signal | 0 / 4 |
| suggestion | bounded_suggestion_narrative_signal | 6 / 6 |
| suggestion | incomparable_price_ranking_signal | 0 / 6 |
| suggestion | lead_time_context_signal | 0 / 6 |

## Critical findings

- comparison/required-failure [exact]: analysis_contract_states_references — Requirement-state assertion has an unsupported topic or supplier.
- comparison/required-failure [heuristic]: bounded_comparison_narrative_signal — Recognized numeric, disclosure or topic check failed; inspect output.
- comparison/corrected-quote-provenance [heuristic]: bounded_comparison_narrative_signal — Recognized numeric, disclosure or topic check failed; inspect output.
- comparison/required-conflict [heuristic]: bounded_comparison_narrative_signal — Recognized numeric, disclosure or topic check failed; inspect output.
- suggestion/tie [heuristic]: bounded_suggestion_narrative_signal — Recognized narrative, disclosure or suggestion check failed; inspect output.
- suggestion/user-correction [heuristic]: bounded_suggestion_narrative_signal — Recognized narrative, disclosure or suggestion check failed; inspect output.
- suggestion/incomparable-prices [heuristic]: bounded_suggestion_narrative_signal — Recognized narrative, disclosure or suggestion check failed; inspect output.
- suggestion/general-vs-project [heuristic]: bounded_suggestion_narrative_signal — Recognized narrative, disclosure or suggestion check failed; inspect output.
- suggestion/mixed-currencies [exact]: allowed_suggestion_choice — See case output.
- suggestion/mixed-currencies [heuristic]: bounded_suggestion_narrative_signal — Recognized narrative, disclosure or suggestion check failed; inspect output.
- suggestion/unequal-quantities [exact]: allowed_suggestion_choice — See case output.
- suggestion/unequal-quantities [heuristic]: bounded_suggestion_narrative_signal — Recognized narrative, disclosure or suggestion check failed; inspect output.

## Human review required — PENDING

8 difficult narrative examples require a person's judgment. No result has been recorded.

| Example | Review criterion |
| --- | --- |
| mixed-currency-ranking | Flag a relative price conclusion when original currencies differ and no conversion basis exists; inspect the full paragraph for qualification. |
| mixed-currency-warning | Accept accurate supplier-bound prices and an unambiguous warning; do not infer an FX conversion. |
| unequal-quantity-ranking | Flag an equivalent-order price ranking when quoted quantities differ and the mismatch is not resolved. |
| unequal-quantity-warning | Accept the exact figures when tied to their suppliers and quantities and the mismatch is clear. |
| general-lead-paraphrase | Accept 50 days as general context and 25 days as the project quotation, with both sources kept distinct. |
| wrong-general-lead | Flag the 25-day value when attributed to the catalog; 25 days belongs to the project quote, while general lead time is 50 days. |
| combined-correct-lead | Accept the combined sentence only if each duration is attributed to its correct general or project-specific source. |
| combined-wrong-lead | Flag both reversed attributions; the catalog value is 50 days and the project quote is 25 days. |

Source: apps/api/evals/human_review/narrative_cases.json.
No production tuning or release acceptance is implied by this baseline.
