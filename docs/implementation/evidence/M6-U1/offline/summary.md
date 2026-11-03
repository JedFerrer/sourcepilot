# SourcePilot offline eval baseline

Status: **COMPLETED**; exit 0.
Scope: brief, clarification, supplier_explanation, quote_extraction, comparison, suggestion. Full scope: True.
Accounted for: 90/90; complete: True.

Exit zero is execution completion, not live model-quality approval.
Automated completion does not prove free-text narrative groundedness.

| Category | Case | Status | Exact failures / heuristic signals |
| --- | --- | --- | --- |
| brief | complete-demo | PASS |  |
| brief | missing-destination | PASS |  |
| brief | missing-delivery | PASS |  |
| brief | missing-quantity | PASS |  |
| brief | no-price | PASS |  |
| brief | required-certification | PASS |  |
| brief | preferred-certification | PASS |  |
| brief | unstated-importance | PASS |  |
| brief | ambiguous-delivery | PASS |  |
| brief | dimensions-attribute | PASS |  |
| brief | branding-unknown | PASS |  |
| brief | non-invention | PASS |  |
| brief | boolean-branding | PASS |  |
| brief | no-branding | PASS |  |
| brief | categorical-branding | PASS |  |
| brief | production-limit | PASS |  |
| brief | explicit-moq | PASS |  |
| brief | price-currency | PASS |  |
| brief | delivery-period | PASS |  |
| brief | relative-delivery | PASS |  |
| brief | informational-color | PASS |  |
| brief | informational-packaging | PASS |  |
| brief | ambiguous-material | PASS |  |
| brief | untrusted-request | PASS |  |
| clarification | missing-product | PASS |  |
| clarification | missing-category | PASS |  |
| clarification | missing-quantity | PASS |  |
| clarification | missing-destination | PASS |  |
| clarification | missing-delivery | PASS |  |
| clarification | missing-material | PASS |  |
| clarification | missing-branding | PASS |  |
| clarification | multiple-known-fields | PASS |  |
| clarification | complete-no-price | PASS |  |
| clarification | complete-cosmetic | PASS |  |
| clarification | existing-five-question-cap | PASS |  |
| clarification | optional-price-not-requested | PASS |  |
| supplier_explanation | grounded-mixed-states | PASS |  |
| supplier_explanation | omitted-required-failure | EXPECTED_REJECTION | exact: states_and_evidence |
| supplier_explanation | unknown-as-strength | EXPECTED_REJECTION | exact: states_and_evidence |
| supplier_explanation | invented-evidence | EXPECTED_REJECTION | exact: states_and_evidence |
| supplier_explanation | invented-capability | EXPECTED_REJECTION | exact: states_and_evidence |
| supplier_explanation | invented-numeric-score | EXPECTED_REJECTION | exact: states_and_evidence |
| supplier_explanation | clear-match | PASS |  |
| supplier_explanation | required-failure | PASS |  |
| supplier_explanation | unknown | PASS |  |
| supplier_explanation | conflict | PASS |  |
| supplier_explanation | near-match | PASS |  |
| quote_extraction | harbor-primary | PASS |  |
| quote_extraction | willow-primary | PASS |  |
| quote_extraction | moss-primary | PASS |  |
| quote_extraction | missing-shipping | PASS |  |
| quote_extraction | conflicting-lead-time | PASS |  |
| quote_extraction | included-tooling | PASS |  |
| quote_extraction | missing-moq | PASS |  |
| quote_extraction | quantity-mismatch | PASS |  |
| quote_extraction | non-usd | PASS |  |
| quote_extraction | explicit-unknown | PASS |  |
| quote_extraction | unsupported-image-only | EXPECTED_REJECTION |  |
| quote_extraction | malformed-pdf | EXPECTED_REJECTION |  |
| comparison | meaningful-tradeoff | PASS |  |
| comparison | required-failure | PASS |  |
| comparison | unknown-and-conflict | PASS |  |
| comparison | corrected-quote-provenance | PASS |  |
| comparison | incomplete-evidence | PASS |  |
| comparison | omitted-required-failure | EXPECTED_REJECTION | exact: analysis_contract_states_references, heuristic: bounded_comparison_narrative_signal |
| comparison | invented-shipping-cost | EXPECTED_REJECTION | heuristic: bounded_comparison_narrative_signal |
| comparison | wrong-source-for-correction | EXPECTED_REJECTION | heuristic: bounded_comparison_narrative_signal |
| comparison | general-vs-project | PASS |  |
| comparison | mixed-currencies | PASS |  |
| comparison | unequal-quantities | PASS |  |
| comparison | required-conflict | PASS |  |
| comparison | stale-comparison-no-model | PASS |  |
| suggestion | clear-suggestion | PASS |  |
| suggestion | tie | PASS |  |
| suggestion | critical-unknown | PASS |  |
| suggestion | required-failure | PASS |  |
| suggestion | incomplete-evidence | PASS |  |
| suggestion | user-correction | PASS |  |
| suggestion | incomparable-prices | PASS |  |
| suggestion | invented-price | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | hidden-required-failure | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | wrong-correction-provenance | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | forced-critical-unknown | EXPECTED_REJECTION | exact: advice_contract_states_references, exact: allowed_suggestion_choice, heuristic: bounded_suggestion_narrative_signal |
| suggestion | numeric-score | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | objective-best-claim | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | unqualified-incomparable-price | EXPECTED_REJECTION | heuristic: incomparable_price_ranking_signal |
| suggestion | general-vs-project | PASS |  |
| suggestion | mixed-currencies | PASS |  |
| suggestion | unequal-quantities | PASS |  |
| suggestion | required-conflict | PASS |  |

## Exact deterministic assertions (passed / checked)

| Category | Assertion | Counts |
| --- | --- | --- |
| brief | brief.ambiguities | 24 / 24 |
| brief | brief.attributes | 24 / 24 |
| brief | brief.category | 24 / 24 |
| brief | brief.delivery_target | 24 / 24 |
| brief | brief.destination | 24 / 24 |
| brief | brief.product_name | 24 / 24 |
| brief | brief.quantity | 24 / 24 |
| brief | brief.requirements | 24 / 24 |
| brief | brief.target_unit_price | 24 / 24 |
| clarification | field_coverage | 9 / 9 |
| clarification | irrelevant_question_rate | 12 / 12 |
| clarification | missing_field_coverage | 12 / 12 |
| clarification | no_questions_when_ready | 3 / 3 |
| clarification | readiness_keys | 12 / 12 |
| clarification | redundant_question_rate | 12 / 12 |
| supplier_explanation | states_and_evidence | 6 / 6 |
| quote_extraction | conflict_detection | 10 / 10 |
| quote_extraction | currency_accuracy | 10 / 10 |
| quote_extraction | extraction_input_hash | 10 / 10 |
| quote_extraction | field.certifications.sources | 7 / 7 |
| quote_extraction | field.certifications.unknown | 3 / 3 |
| quote_extraction | field.certifications.value | 7 / 7 |
| quote_extraction | field.compliance_notes.unknown | 10 / 10 |
| quote_extraction | field.currency.sources | 10 / 10 |
| quote_extraction | field.currency.value | 10 / 10 |
| quote_extraction | field.exclusions.sources | 7 / 7 |
| quote_extraction | field.exclusions.unknown | 3 / 3 |
| quote_extraction | field.exclusions.value | 7 / 7 |
| quote_extraction | field.incoterm.unknown | 10 / 10 |
| quote_extraction | field.moq.sources | 9 / 9 |
| quote_extraction | field.moq.unknown | 1 / 1 |
| quote_extraction | field.moq.value | 9 / 9 |
| quote_extraction | field.packaging_cost.unknown | 10 / 10 |
| quote_extraction | field.payment_terms.sources | 10 / 10 |
| quote_extraction | field.payment_terms.value | 10 / 10 |
| quote_extraction | field.production_lead_time.conflict | 1 / 1 |
| quote_extraction | field.production_lead_time.sources | 9 / 9 |
| quote_extraction | field.production_lead_time.value | 9 / 9 |
| quote_extraction | field.quote_validity.sources | 10 / 10 |
| quote_extraction | field.quote_validity.value | 10 / 10 |
| quote_extraction | field.quoted_quantity.sources | 10 / 10 |
| quote_extraction | field.quoted_quantity.value | 10 / 10 |
| quote_extraction | field.sample_cost.sources | 9 / 9 |
| quote_extraction | field.sample_cost.unknown | 1 / 1 |
| quote_extraction | field.sample_cost.value | 9 / 9 |
| quote_extraction | field.sample_lead_time.sources | 8 / 8 |
| quote_extraction | field.sample_lead_time.unknown | 2 / 2 |
| quote_extraction | field.sample_lead_time.value | 8 / 8 |
| quote_extraction | field.shipping_cost.sources | 8 / 8 |
| quote_extraction | field.shipping_cost.unknown | 2 / 2 |
| quote_extraction | field.shipping_cost.value | 8 / 8 |
| quote_extraction | field.shipping_time.sources | 8 / 8 |
| quote_extraction | field.shipping_time.unknown | 2 / 2 |
| quote_extraction | field.shipping_time.value | 8 / 8 |
| quote_extraction | field.special_conditions.unknown | 10 / 10 |
| quote_extraction | field.supplier_notes.unknown | 10 / 10 |
| quote_extraction | field.tooling_cost.sources | 9 / 9 |
| quote_extraction | field.tooling_cost.unknown | 1 / 1 |
| quote_extraction | field.tooling_cost.value | 9 / 9 |
| quote_extraction | field.total_lead_time.unknown | 10 / 10 |
| quote_extraction | field.unit_price.sources | 10 / 10 |
| quote_extraction | field.unit_price.value | 10 / 10 |
| quote_extraction | field.warranty.unknown | 10 / 10 |
| quote_extraction | field_accuracy | 10 / 10 |
| quote_extraction | hallucination_rate | 10 / 10 |
| quote_extraction | numeric_accuracy | 10 / 10 |
| quote_extraction | parser_blocks | 10 / 10 |
| quote_extraction | parser_rejection | 2 / 2 |
| quote_extraction | source_block_accuracy | 10 / 10 |
| quote_extraction | source_references | 10 / 10 |
| quote_extraction | unknown_detection | 10 / 10 |
| comparison | analysis_contract_states_references | 9 / 9 |
| comparison | stale_comparison_predicate | 1 / 1 |
| suggestion | advice_contract_states_references | 11 / 11 |
| suggestion | allowed_suggestion_choice | 11 / 11 |

## Measured metrics (numerator / denominator)

| Category | Metric | Kind | Counts | Measured cases |
| --- | --- | --- | --- | --- |
| brief | ambiguities_accuracy | exact | 24 / 24 | 24 |
| brief | attributes_accuracy | exact | 24 / 24 | 24 |
| brief | category_accuracy | exact | 24 / 24 | 24 |
| brief | delivery_target_accuracy | exact | 24 / 24 | 24 |
| brief | destination_accuracy | exact | 24 / 24 | 24 |
| brief | hallucinated_field_rate | exact | 0 / 111 | 24 |
| brief | product_name_accuracy | exact | 24 / 24 | 24 |
| brief | quantity_accuracy | exact | 24 / 24 | 24 |
| brief | requirements_accuracy | exact | 24 / 24 | 24 |
| brief | target_unit_price_accuracy | exact | 24 / 24 | 24 |
| clarification | clarity_heuristic | heuristic | 14 / 14 | 12 |
| clarification | conciseness_heuristic | heuristic | 14 / 14 | 12 |
| clarification | irrelevant_question_rate | exact | 0 / 14 | 12 |
| clarification | missing_field_coverage | exact | 14 / 14 | 12 |
| clarification | redundant_question_rate | exact | 0 / 14 | 12 |
| quote_extraction | conflict_detection | exact | 1 / 1 | 10 |
| quote_extraction | currency_accuracy | exact | 10 / 10 | 10 |
| quote_extraction | field_accuracy | exact | 210 / 210 | 10 |
| quote_extraction | hallucination_rate | exact | 0 / 85 | 10 |
| quote_extraction | numeric_accuracy | exact | 55 / 55 | 10 |
| quote_extraction | source_block_accuracy | exact | 210 / 210 | 10 |
| quote_extraction | unknown_detection | exact | 85 / 85 | 10 |

Zero denominators are not applicable. Exact assertion pass counts are separate in results.json.
Failed runtime cases remain in case/status totals even when extracted-value metrics are unavailable.

## Heuristic signals (triggered / inspected)

A non-trigger is not a factual-groundedness pass. These are bounded warning cues.

| Category | Signal | Counts |
| --- | --- | --- |
| clarification | clarity_rate | 0 / 12 |
| clarification | conciseness_rate | 0 / 12 |
| supplier_explanation | supplier_free_text_capability_signal | 0 / 6 |
| comparison | bounded_comparison_narrative_signal | 0 / 9 |
| comparison | incomparable_price_ranking_signal | 0 / 9 |
| comparison | lead_time_context_signal | 0 / 9 |
| suggestion | bounded_suggestion_narrative_signal | 0 / 11 |
| suggestion | incomparable_price_ranking_signal | 0 / 11 |
| suggestion | lead_time_context_signal | 0 / 11 |

## Critical findings

- None in accepted recorded outputs; expected negative controls remain in the case table.

## Human review required — PENDING

10 difficult narrative examples require a person's judgment. No result has been recorded.

| Example | Review criterion |
| --- | --- |
| mixed-currency-ranking | Flag a relative price conclusion when original currencies differ and no conversion basis exists; inspect the full paragraph for qualification. |
| mixed-currency-warning | Accept accurate supplier-bound prices and an unambiguous warning; do not infer an FX conversion. |
| unequal-quantity-ranking | Flag an equivalent-order price ranking when quoted quantities differ and the mismatch is not resolved. |
| unequal-quantity-warning | Accept the exact figures when tied to their suppliers and quantities and the mismatch is clear. |
| unsupported-supplier-action | Flag the surgical-implant design capability; a valid but unrelated evidence ID does not support it. |
| supported-capability-paraphrase | Accept the making-action paraphrase if the cited evidence supports the same product and capability. |
| general-lead-paraphrase | Accept 50 days as general context and 25 days as the project quotation, with both sources kept distinct. |
| wrong-general-lead | Flag the 25-day value when attributed to the catalog; 25 days belongs to the project quote, while general lead time is 50 days. |
| combined-correct-lead | Accept the combined sentence only if each duration is attributed to its correct general or project-specific source. |
| combined-wrong-lead | Flag both reversed attributions; the catalog value is 50 days and the project quote is 25 days. |

Source: apps/api/evals/human_review/narrative_cases.json.
No production tuning or release acceptance is implied by this baseline.
