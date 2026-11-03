# SourcePilot live eval baseline

Status: **ERROR**; exit 2.
Scope: brief, clarification, supplier_explanation, quote_extraction, comparison, suggestion. Full scope: True.
Accounted for: 90/90; complete: True.

Exit zero is execution completion, not live model-quality approval.
Automated completion does not prove free-text narrative groundedness.

| Category | Case | Status | Exact failures / heuristic signals |
| --- | --- | --- | --- |
| brief | complete-demo | QUALITY_FINDING | exact: brief.requirements, exact: brief.ambiguities |
| brief | missing-destination | QUALITY_FINDING | exact: brief.category, exact: brief.requirements |
| brief | missing-delivery | QUALITY_FINDING | exact: brief.category, exact: brief.requirements |
| brief | missing-quantity | QUALITY_FINDING | exact: brief.requirements |
| brief | no-price | QUALITY_FINDING | exact: brief.category, exact: brief.requirements |
| brief | required-certification | QUALITY_FINDING | exact: brief.product_name, exact: brief.category |
| brief | preferred-certification | QUALITY_FINDING | exact: brief.product_name, exact: brief.category |
| brief | unstated-importance | QUALITY_FINDING | exact: brief.product_name |
| brief | ambiguous-delivery | QUALITY_FINDING | exact: brief.category, exact: brief.delivery_target, exact: brief.requirements, exact: brief.ambiguities |
| brief | dimensions-attribute | QUALITY_FINDING | exact: brief.category |
| brief | branding-unknown | QUALITY_FINDING | exact: brief.product_name, exact: brief.attributes, exact: brief.requirements, exact: brief.ambiguities |
| brief | non-invention | QUALITY_FINDING | exact: brief.product_name, exact: brief.attributes |
| brief | boolean-branding | QUALITY_FINDING | exact: brief.category |
| brief | no-branding | PASS |  |
| brief | categorical-branding | QUALITY_FINDING | exact: brief.product_name |
| brief | production-limit | QUALITY_FINDING | exact: brief.product_name, exact: brief.category, exact: brief.requirements |
| brief | explicit-moq | QUALITY_FINDING | exact: brief.product_name, exact: brief.category, exact: brief.requirements, exact: brief.ambiguities |
| brief | price-currency | QUALITY_FINDING | exact: runtime_completion |
| brief | delivery-period | QUALITY_FINDING | exact: runtime_completion |
| brief | relative-delivery | QUALITY_FINDING | exact: runtime_completion |
| brief | informational-color | QUALITY_FINDING | exact: brief.product_name, exact: brief.requirements |
| brief | informational-packaging | QUALITY_FINDING | exact: brief.category, exact: brief.requirements |
| brief | ambiguous-material | QUALITY_FINDING | exact: brief.product_name, exact: brief.requirements |
| brief | untrusted-request | QUALITY_FINDING | exact: brief.category |
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
| supplier_explanation | clear-match | RUNTIME_ERROR | exact: runtime_completion |
| supplier_explanation | required-failure | PASS |  |
| supplier_explanation | unknown | PASS |  |
| supplier_explanation | conflict | RUNTIME_ERROR | exact: runtime_completion |
| supplier_explanation | near-match | PASS |  |
| quote_extraction | harbor-primary | QUALITY_FINDING | exact: runtime_completion |
| quote_extraction | willow-primary | QUALITY_FINDING | exact: runtime_completion |
| quote_extraction | moss-primary | QUALITY_FINDING | exact: runtime_completion |
| quote_extraction | missing-shipping | QUALITY_FINDING | exact: runtime_completion |
| quote_extraction | conflicting-lead-time | QUALITY_FINDING | exact: runtime_completion |
| quote_extraction | included-tooling | QUALITY_FINDING | exact: runtime_completion |
| quote_extraction | missing-moq | QUALITY_FINDING | exact: runtime_completion |
| quote_extraction | quantity-mismatch | QUALITY_FINDING | exact: runtime_completion |
| quote_extraction | non-usd | QUALITY_FINDING | exact: runtime_completion |
| quote_extraction | explicit-unknown | QUALITY_FINDING | exact: runtime_completion |
| quote_extraction | unsupported-image-only | EXPECTED_REJECTION |  |
| quote_extraction | malformed-pdf | EXPECTED_REJECTION |  |
| comparison | meaningful-tradeoff | QUALITY_FINDING | exact: runtime_completion |
| comparison | required-failure | QUALITY_FINDING | exact: runtime_completion |
| comparison | unknown-and-conflict | RUNTIME_ERROR | exact: runtime_completion |
| comparison | corrected-quote-provenance | RUNTIME_ERROR | exact: runtime_completion |
| comparison | incomplete-evidence | RUNTIME_ERROR | exact: runtime_completion |
| comparison | omitted-required-failure | EXPECTED_REJECTION | exact: analysis_contract_states_references, heuristic: bounded_comparison_narrative_signal |
| comparison | invented-shipping-cost | EXPECTED_REJECTION | heuristic: bounded_comparison_narrative_signal |
| comparison | wrong-source-for-correction | EXPECTED_REJECTION | heuristic: bounded_comparison_narrative_signal |
| comparison | general-vs-project | QUALITY_FINDING | exact: runtime_completion |
| comparison | mixed-currencies | RUNTIME_ERROR | exact: runtime_completion |
| comparison | unequal-quantities | QUALITY_FINDING | exact: runtime_completion |
| comparison | required-conflict | QUALITY_FINDING | exact: runtime_completion |
| comparison | stale-comparison-no-model | EXPECTED_REJECTION |  |
| suggestion | clear-suggestion | RUNTIME_ERROR | exact: runtime_completion |
| suggestion | tie | QUALITY_FINDING | exact: runtime_completion |
| suggestion | critical-unknown | QUALITY_FINDING | exact: runtime_completion |
| suggestion | required-failure | QUALITY_FINDING | exact: runtime_completion |
| suggestion | incomplete-evidence | QUALITY_FINDING | exact: runtime_completion |
| suggestion | user-correction | QUALITY_FINDING | exact: runtime_completion |
| suggestion | incomparable-prices | QUALITY_FINDING | exact: runtime_completion |
| suggestion | invented-price | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | hidden-required-failure | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | wrong-correction-provenance | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | forced-critical-unknown | EXPECTED_REJECTION | exact: advice_contract_states_references, exact: allowed_suggestion_choice, heuristic: bounded_suggestion_narrative_signal |
| suggestion | numeric-score | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | objective-best-claim | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | unqualified-incomparable-price | EXPECTED_REJECTION | heuristic: incomparable_price_ranking_signal |
| suggestion | general-vs-project | QUALITY_FINDING | exact: runtime_completion |
| suggestion | mixed-currencies | QUALITY_FINDING | exact: runtime_completion |
| suggestion | unequal-quantities | QUALITY_FINDING | exact: runtime_completion |
| suggestion | required-conflict | QUALITY_FINDING | exact: runtime_completion |

## Exact deterministic assertions (passed / checked)

| Category | Assertion | Counts |
| --- | --- | --- |
| brief | brief.ambiguities | 17 / 21 |
| brief | brief.attributes | 19 / 21 |
| brief | brief.category | 9 / 21 |
| brief | brief.delivery_target | 20 / 21 |
| brief | brief.destination | 21 / 21 |
| brief | brief.product_name | 11 / 21 |
| brief | brief.quantity | 21 / 21 |
| brief | brief.requirements | 9 / 21 |
| brief | brief.target_unit_price | 21 / 21 |
| brief | runtime_completion | 0 / 3 |
| clarification | field_coverage | 9 / 9 |
| clarification | irrelevant_question_rate | 12 / 12 |
| clarification | missing_field_coverage | 12 / 12 |
| clarification | no_questions_when_ready | 3 / 3 |
| clarification | readiness_keys | 12 / 12 |
| clarification | redundant_question_rate | 12 / 12 |
| supplier_explanation | rendered_states_and_evidence | 4 / 4 |
| supplier_explanation | runtime_completion | 0 / 2 |
| quote_extraction | parser_rejection | 2 / 2 |
| quote_extraction | runtime_completion | 0 / 10 |
| comparison | runtime_completion | 0 / 9 |
| comparison | stale_no_model | 1 / 1 |
| suggestion | runtime_completion | 0 / 11 |

## Measured metrics (numerator / denominator)

| Category | Metric | Kind | Counts | Measured cases |
| --- | --- | --- | --- | --- |
| brief | ambiguities_accuracy | exact | 17 / 21 | 21 |
| brief | attributes_accuracy | exact | 19 / 21 | 21 |
| brief | category_accuracy | exact | 9 / 21 | 21 |
| brief | delivery_target_accuracy | exact | 20 / 21 | 21 |
| brief | destination_accuracy | exact | 21 / 21 | 21 |
| brief | hallucinated_field_rate | exact | 14 / 100 | 21 |
| brief | product_name_accuracy | exact | 11 / 21 | 21 |
| brief | quantity_accuracy | exact | 21 / 21 | 21 |
| brief | requirements_accuracy | exact | 9 / 21 | 21 |
| brief | target_unit_price_accuracy | exact | 21 / 21 | 21 |
| clarification | clarity_heuristic | heuristic | 14 / 14 | 12 |
| clarification | conciseness_heuristic | heuristic | 14 / 14 | 12 |
| clarification | irrelevant_question_rate | exact | 0 / 14 | 12 |
| clarification | missing_field_coverage | exact | 14 / 14 | 12 |
| clarification | redundant_question_rate | exact | 0 / 14 | 12 |

Zero denominators are not applicable. Exact assertion pass counts are separate in results.json.
Failed runtime cases remain in case/status totals even when extracted-value metrics are unavailable.

## Heuristic signals (triggered / inspected)

A non-trigger is not a factual-groundedness pass. These are bounded warning cues.

| Category | Signal | Counts |
| --- | --- | --- |
| clarification | clarity_rate | 0 / 12 |
| clarification | conciseness_rate | 0 / 12 |
| supplier_explanation | supplier_free_text_capability_signal | 0 / 4 |

## Critical findings

- brief/complete-demo [exact]: brief.requirements — expected=[{'kind': 'MATERIAL', 'importance': None, 'expected_value': {'value': 'recycled polyester'}}, {'kind': 'CERTIFICATION', 'importance': 'PREFERRED', 'expected_value': {'value': 'GRS'}}]; actual=[{'kind': 'MATERIAL', 'importance': None, 'expected_value': {'value': 'recycled polyester'}}, {'kind': 'CAPABILITY', 'importance': None, 'expected_value': {'capability_key': 'CUSTOM_BRANDING', 'value': True}}, {'kind': 'UNIT_PRICE', 'importance': None, 'expected_value': {'amount': '5', 'currency': 'USD'}}, {'kind': 'DELIVERY', 'importance': None, 'expected_value': {'kind': 'DATE', 'date': '2026-11-01'}}, {'kind': 'CERTIFICATION', 'importance': 'PREFERRED', 'expected_value': {'value': 'GRS'}}]
- brief/complete-demo [exact]: brief.ambiguities — expected=[]; actual=["The price is stated as under USD 5 each; the schema's price fields represent only the numeric threshold and do not encode the strict 'under' condition."]
- brief/missing-destination [exact]: brief.category — expected='pouches'; actual=None
- brief/missing-destination [exact]: brief.requirements — expected=[]; actual=[{'kind': 'MATERIAL', 'importance': None, 'expected_value': {'value': 'cotton'}}, {'kind': 'QUANTITY', 'importance': None, 'expected_value': {'quantity': 500}}, {'kind': 'DELIVERY', 'importance': None, 'expected_value': {'kind': 'DATE', 'date': '2026-12-01'}}]
- brief/missing-delivery [exact]: brief.category — expected='tote bags'; actual=None
- brief/missing-delivery [exact]: brief.requirements — expected=[]; actual=[{'kind': 'QUANTITY', 'importance': None, 'expected_value': {'quantity': 800}}]
- brief/missing-quantity [exact]: brief.requirements — expected=[]; actual=[{'kind': 'MATERIAL', 'importance': None, 'expected_value': {'value': 'recycled'}}]
- brief/no-price [exact]: brief.category — expected='bottles'; actual=None
- brief/no-price [exact]: brief.requirements — expected=[]; actual=[{'kind': 'QUANTITY', 'importance': None, 'expected_value': {'quantity': 100}}, {'kind': 'DELIVERY', 'importance': None, 'expected_value': {'kind': 'DATE', 'date': '2026-10-01'}}]
- brief/required-certification [exact]: brief.product_name — expected='bags'; actual=None
- brief/required-certification [exact]: brief.category — expected='bags'; actual=None
- brief/preferred-certification [exact]: brief.product_name — expected='bags'; actual=None
- brief/preferred-certification [exact]: brief.category — expected='bags'; actual=None
- brief/unstated-importance [exact]: brief.product_name — expected='bags'; actual=None
- brief/ambiguous-delivery [exact]: brief.category — expected='pouches'; actual=None
- brief/ambiguous-delivery [exact]: brief.delivery_target — expected=None; actual={'kind': 'PERIOD', 'label': 'around November, maybe December', 'start_date': None, 'end_date': None}
- brief/ambiguous-delivery [exact]: brief.requirements — expected=[]; actual=[{'kind': 'QUANTITY', 'importance': None, 'expected_value': {'quantity': 100}}]
- brief/ambiguous-delivery [exact]: brief.ambiguities — expected=['Delivery may be in November or December.']; actual=['The delivery timing is approximate and may be around November or possibly December; no year is stated.']
- brief/dimensions-attribute [exact]: brief.category — expected='bags'; actual=None
- brief/branding-unknown [exact]: brief.product_name — expected='bags'; actual=None
- brief/branding-unknown [exact]: brief.attributes — expected=[]; actual=[{'subject': 'BRANDING_NOTES', 'text': 'Branding has not been decided.'}]
- brief/branding-unknown [exact]: brief.requirements — expected=[]; actual=[{'kind': 'QUANTITY', 'importance': None, 'expected_value': {'quantity': 500}}]
- brief/branding-unknown [exact]: brief.ambiguities — expected=['Branding has not been decided.']; actual=[]
- brief/non-invention [exact]: brief.product_name — expected='cosmetic bags'; actual=None
- brief/non-invention [exact]: brief.attributes — expected=[]; actual=[{'subject': 'BRANDING_NOTES', 'text': 'for our new brand'}]
- brief/boolean-branding [exact]: brief.category — expected='cosmetic bags'; actual=None
- brief/categorical-branding [exact]: brief.product_name — expected='bags'; actual=None
- brief/production-limit [exact]: brief.product_name — expected='bags'; actual=None
- brief/production-limit [exact]: brief.category — expected='bags'; actual=None
- brief/production-limit [exact]: brief.requirements — expected=[{'kind': 'PRODUCTION_LEAD_TIME', 'importance': 'REQUIRED', 'expected_value': {'max_days': 30}}]; actual=[{'kind': 'PRODUCTION_LEAD_TIME', 'importance': None, 'expected_value': {'max_days': 30}}]
- brief/explicit-moq [exact]: brief.product_name — expected='bags'; actual=None
- brief/explicit-moq [exact]: brief.category — expected='bags'; actual=None
- brief/explicit-moq [exact]: brief.requirements — expected=[{'kind': 'MOQ', 'importance': 'REQUIRED', 'expected_value': {'quantity': 500}}]; actual=[{'kind': 'MOQ', 'importance': None, 'expected_value': {'quantity': 500}}]
- brief/explicit-moq [exact]: brief.ambiguities — expected=[]; actual=['The MOQ is stated as a maximum of 500 units; the requirement value schema does not encode an upper-bound operator.']
- brief/price-currency [exact]: runtime_completion — VALIDATION_FAILED
- brief/delivery-period [exact]: runtime_completion — VALIDATION_FAILED
- brief/relative-delivery [exact]: runtime_completion — VALIDATION_FAILED
- brief/informational-color [exact]: brief.product_name — expected='bags'; actual=None
- brief/informational-color [exact]: brief.requirements — expected=[]; actual=[{'kind': 'QUANTITY', 'importance': None, 'expected_value': {'quantity': 300}}]
- brief/informational-packaging [exact]: brief.category — expected='bags'; actual=None
- brief/informational-packaging [exact]: brief.requirements — expected=[]; actual=[{'kind': 'QUANTITY', 'importance': None, 'expected_value': {'quantity': 350}}]
- brief/ambiguous-material [exact]: brief.product_name — expected='bags'; actual=None
- brief/ambiguous-material [exact]: brief.requirements — expected=[]; actual=[{'kind': 'MATERIAL', 'importance': None, 'expected_value': {'value': 'cotton or polyester'}}]
- brief/untrusted-request [exact]: brief.category — expected='cosmetic bags'; actual=None
- quote_extraction/harbor-primary [exact]: runtime_completion — VALIDATION_FAILED
- quote_extraction/willow-primary [exact]: runtime_completion — VALIDATION_FAILED
- quote_extraction/moss-primary [exact]: runtime_completion — VALIDATION_FAILED
- quote_extraction/missing-shipping [exact]: runtime_completion — VALIDATION_FAILED
- quote_extraction/conflicting-lead-time [exact]: runtime_completion — VALIDATION_FAILED
- quote_extraction/included-tooling [exact]: runtime_completion — VALIDATION_FAILED
- quote_extraction/missing-moq [exact]: runtime_completion — VALIDATION_FAILED
- quote_extraction/quantity-mismatch [exact]: runtime_completion — VALIDATION_FAILED
- quote_extraction/non-usd [exact]: runtime_completion — VALIDATION_FAILED
- quote_extraction/explicit-unknown [exact]: runtime_completion — VALIDATION_FAILED
- comparison/meaningful-tradeoff [exact]: runtime_completion — FAILED_LIMIT_REACHED
- comparison/required-failure [exact]: runtime_completion — FAILED_LIMIT_REACHED
- comparison/general-vs-project [exact]: runtime_completion — FAILED_LIMIT_REACHED
- comparison/unequal-quantities [exact]: runtime_completion — FAILED_LIMIT_REACHED
- comparison/required-conflict [exact]: runtime_completion — FAILED_LIMIT_REACHED
- suggestion/tie [exact]: runtime_completion — FAILED_LIMIT_REACHED
- suggestion/critical-unknown [exact]: runtime_completion — FAILED_LIMIT_REACHED
- suggestion/required-failure [exact]: runtime_completion — FAILED_LIMIT_REACHED
- suggestion/incomplete-evidence [exact]: runtime_completion — FAILED_LIMIT_REACHED
- suggestion/user-correction [exact]: runtime_completion — FAILED_LIMIT_REACHED
- suggestion/incomparable-prices [exact]: runtime_completion — FAILED_LIMIT_REACHED
- suggestion/general-vs-project [exact]: runtime_completion — FAILED_LIMIT_REACHED
- suggestion/mixed-currencies [exact]: runtime_completion — FAILED_LIMIT_REACHED
- suggestion/unequal-quantities [exact]: runtime_completion — FAILED_LIMIT_REACHED
- suggestion/required-conflict [exact]: runtime_completion — FAILED_LIMIT_REACHED

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
