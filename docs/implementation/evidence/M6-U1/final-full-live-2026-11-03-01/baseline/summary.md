# SourcePilot live eval baseline

Status: **ERROR**; exit 2.
Scope: brief, clarification, supplier_explanation, quote_extraction, comparison, suggestion. Full scope: True.
Accounted for: 90/90; complete: True.

Exit zero is execution completion, not live model-quality approval.
Automated completion does not prove free-text narrative groundedness.

| Category | Case | Status | Exact failures / heuristic signals |
| --- | --- | --- | --- |
| brief | complete-demo | QUALITY_FINDING | exact: brief.category, exact: brief.attributes, exact: brief.requirements, exact: brief.ambiguities |
| brief | missing-destination | QUALITY_FINDING | exact: brief.requirements |
| brief | missing-delivery | QUALITY_FINDING | exact: brief.category, exact: brief.requirements |
| brief | missing-quantity | QUALITY_FINDING | exact: brief.requirements |
| brief | no-price | PASS |  |
| brief | required-certification | QUALITY_FINDING | exact: brief.product_name |
| brief | preferred-certification | PASS |  |
| brief | unstated-importance | PASS |  |
| brief | ambiguous-delivery | QUALITY_FINDING | exact: brief.delivery_target, exact: brief.requirements, exact: brief.ambiguities |
| brief | dimensions-attribute | PASS |  |
| brief | branding-unknown | QUALITY_FINDING | exact: brief.attributes, exact: brief.requirements |
| brief | non-invention | QUALITY_FINDING | exact: brief.category, exact: brief.attributes |
| brief | boolean-branding | QUALITY_FINDING | exact: brief.category |
| brief | no-branding | QUALITY_FINDING | exact: brief.category |
| brief | categorical-branding | QUALITY_FINDING | exact: brief.requirements |
| brief | production-limit | QUALITY_FINDING | exact: brief.ambiguities |
| brief | explicit-moq | QUALITY_FINDING | exact: brief.ambiguities |
| brief | price-currency | QUALITY_FINDING | exact: brief.requirements, exact: brief.ambiguities |
| brief | delivery-period | QUALITY_FINDING | exact: brief.requirements |
| brief | relative-delivery | QUALITY_FINDING | exact: brief.requirements |
| brief | informational-color | PASS |  |
| brief | informational-packaging | QUALITY_FINDING | exact: brief.requirements |
| brief | ambiguous-material | QUALITY_FINDING | exact: brief.ambiguities |
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
| supplier_explanation | clear-match | PASS |  |
| supplier_explanation | required-failure | PASS |  |
| supplier_explanation | unknown | PASS |  |
| supplier_explanation | conflict | PASS |  |
| supplier_explanation | near-match | PASS |  |
| quote_extraction | harbor-primary | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.supplier_notes.unknown, exact: field.supplier_notes.unresolved_support |
| quote_extraction | willow-primary | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.supplier_notes.unknown, exact: field.supplier_notes.unresolved_support |
| quote_extraction | moss-primary | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.supplier_notes.unknown, exact: field.supplier_notes.field_assignment |
| quote_extraction | missing-shipping | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.supplier_notes.unknown, exact: field.supplier_notes.field_assignment |
| quote_extraction | conflicting-lead-time | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.supplier_notes.unknown, exact: field.supplier_notes.field_assignment |
| quote_extraction | included-tooling | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.supplier_notes.unknown, exact: field.supplier_notes.unresolved_support |
| quote_extraction | missing-moq | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.supplier_notes.unknown, exact: field.supplier_notes.unresolved_support |
| quote_extraction | quantity-mismatch | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.supplier_notes.unknown, exact: field.supplier_notes.unresolved_support |
| quote_extraction | non-usd | PASS |  |
| quote_extraction | explicit-unknown | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.supplier_notes.unknown, exact: field.supplier_notes.field_assignment |
| quote_extraction | unsupported-image-only | EXPECTED_REJECTION |  |
| quote_extraction | malformed-pdf | EXPECTED_REJECTION |  |
| comparison | meaningful-tradeoff | RUNTIME_ERROR | exact: runtime_completion |
| comparison | required-failure | RUNTIME_ERROR | exact: runtime_completion |
| comparison | unknown-and-conflict | RUNTIME_ERROR | exact: runtime_completion |
| comparison | corrected-quote-provenance | RUNTIME_ERROR | exact: runtime_completion |
| comparison | incomplete-evidence | RUNTIME_ERROR | exact: runtime_completion |
| comparison | omitted-required-failure | EXPECTED_REJECTION | exact: analysis_contract_states_references, heuristic: bounded_comparison_narrative_signal |
| comparison | invented-shipping-cost | EXPECTED_REJECTION | heuristic: bounded_comparison_narrative_signal |
| comparison | wrong-source-for-correction | EXPECTED_REJECTION | heuristic: bounded_comparison_narrative_signal |
| comparison | general-vs-project | RUNTIME_ERROR | exact: runtime_completion |
| comparison | mixed-currencies | RUNTIME_ERROR | exact: runtime_completion |
| comparison | unequal-quantities | RUNTIME_ERROR | exact: runtime_completion |
| comparison | required-conflict | RUNTIME_ERROR | exact: runtime_completion |
| comparison | stale-comparison-no-model | EXPECTED_REJECTION |  |
| suggestion | clear-suggestion | RUNTIME_ERROR | exact: runtime_completion |
| suggestion | tie | RUNTIME_ERROR | exact: runtime_completion |
| suggestion | critical-unknown | RUNTIME_ERROR | exact: runtime_completion |
| suggestion | required-failure | RUNTIME_ERROR | exact: runtime_completion |
| suggestion | incomplete-evidence | RUNTIME_ERROR | exact: runtime_completion |
| suggestion | user-correction | RUNTIME_ERROR | exact: runtime_completion |
| suggestion | incomparable-prices | RUNTIME_ERROR | exact: runtime_completion |
| suggestion | invented-price | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | hidden-required-failure | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | wrong-correction-provenance | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | forced-critical-unknown | EXPECTED_REJECTION | exact: advice_contract_states_references, exact: allowed_suggestion_choice, heuristic: bounded_suggestion_narrative_signal |
| suggestion | numeric-score | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | objective-best-claim | EXPECTED_REJECTION | heuristic: bounded_suggestion_narrative_signal |
| suggestion | unqualified-incomparable-price | EXPECTED_REJECTION | heuristic: incomparable_price_ranking_signal |
| suggestion | general-vs-project | RUNTIME_ERROR | exact: runtime_completion |
| suggestion | mixed-currencies | RUNTIME_ERROR | exact: runtime_completion |
| suggestion | unequal-quantities | RUNTIME_ERROR | exact: runtime_completion |
| suggestion | required-conflict | RUNTIME_ERROR | exact: runtime_completion |

## Exact deterministic assertions (passed / checked)

| Category | Assertion | Counts |
| --- | --- | --- |
| brief | brief.ambiguities | 18 / 24 |
| brief | brief.attributes | 21 / 24 |
| brief | brief.category | 18 / 24 |
| brief | brief.delivery_target | 23 / 24 |
| brief | brief.destination | 24 / 24 |
| brief | brief.product_name | 23 / 24 |
| brief | brief.quantity | 24 / 24 |
| brief | brief.requirements | 13 / 24 |
| brief | brief.target_unit_price | 24 / 24 |
| clarification | field_coverage | 9 / 9 |
| clarification | irrelevant_question_rate | 12 / 12 |
| clarification | missing_field_coverage | 12 / 12 |
| clarification | no_questions_when_ready | 3 / 3 |
| clarification | readiness_keys | 12 / 12 |
| clarification | redundant_question_rate | 12 / 12 |
| supplier_explanation | rendered_states_and_evidence | 6 / 6 |
| quote_extraction | conflict_detection | 10 / 10 |
| quote_extraction | currency_accuracy | 10 / 10 |
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
| quote_extraction | field.supplier_notes.field_assignment | 0 / 4 |
| quote_extraction | field.supplier_notes.unknown | 1 / 10 |
| quote_extraction | field.supplier_notes.unresolved_support | 0 / 5 |
| quote_extraction | field.tooling_cost.sources | 9 / 9 |
| quote_extraction | field.tooling_cost.unknown | 1 / 1 |
| quote_extraction | field.tooling_cost.value | 9 / 9 |
| quote_extraction | field.total_lead_time.unknown | 10 / 10 |
| quote_extraction | field.unit_price.sources | 10 / 10 |
| quote_extraction | field.unit_price.value | 10 / 10 |
| quote_extraction | field.warranty.unknown | 10 / 10 |
| quote_extraction | field_accuracy | 1 / 10 |
| quote_extraction | hallucination_rate | 10 / 10 |
| quote_extraction | numeric_accuracy | 10 / 10 |
| quote_extraction | parser_rejection | 2 / 2 |
| quote_extraction | source_block_accuracy | 1 / 10 |
| quote_extraction | source_references | 10 / 10 |
| quote_extraction | unknown_detection | 1 / 10 |
| comparison | runtime_completion | 0 / 9 |
| comparison | stale_no_model | 1 / 1 |
| suggestion | runtime_completion | 0 / 11 |

## Measured metrics (numerator / denominator)

| Category | Metric | Kind | Counts | Measured cases |
| --- | --- | --- | --- | --- |
| brief | ambiguities_accuracy | exact | 18 / 24 | 24 |
| brief | attributes_accuracy | exact | 21 / 24 | 24 |
| brief | category_accuracy | exact | 18 / 24 | 24 |
| brief | delivery_target_accuracy | exact | 23 / 24 | 24 |
| brief | destination_accuracy | exact | 24 / 24 | 24 |
| brief | hallucinated_field_rate | exact | 16 / 111 | 24 |
| brief | product_name_accuracy | exact | 23 / 24 | 24 |
| brief | quantity_accuracy | exact | 24 / 24 | 24 |
| brief | requirements_accuracy | exact | 13 / 24 | 24 |
| brief | target_unit_price_accuracy | exact | 24 / 24 | 24 |
| clarification | clarity_heuristic | heuristic | 14 / 14 | 12 |
| clarification | conciseness_heuristic | heuristic | 14 / 14 | 12 |
| clarification | irrelevant_question_rate | exact | 0 / 14 | 12 |
| clarification | missing_field_coverage | exact | 14 / 14 | 12 |
| clarification | redundant_question_rate | exact | 0 / 14 | 12 |
| quote_extraction | conflict_detection | exact | 1 / 1 | 10 |
| quote_extraction | currency_accuracy | exact | 10 / 10 | 10 |
| quote_extraction | expected_unknown_known_rate | exact | 9 / 85 | 10 |
| quote_extraction | field_accuracy | exact | 201 / 210 | 10 |
| quote_extraction | hallucination_rate | exact | 0 / 85 | 10 |
| quote_extraction | numeric_accuracy | exact | 55 / 55 | 10 |
| quote_extraction | source_block_accuracy | exact | 201 / 210 | 10 |
| quote_extraction | unknown_detection | exact | 76 / 85 | 10 |
| quote_extraction | unresolved_support_rate | exact | 5 / 210 | 10 |
| quote_extraction | unsupported_value_rate | exact | 0 / 210 | 10 |

Zero denominators are not applicable. Exact assertion pass counts are separate in results.json.
Failed runtime cases remain in case/status totals even when extracted-value metrics are unavailable.

## Heuristic signals (triggered / inspected)

A non-trigger is not a factual-groundedness pass. These are bounded warning cues.

| Category | Signal | Counts |
| --- | --- | --- |
| clarification | clarity_rate | 0 / 12 |
| clarification | conciseness_rate | 0 / 12 |
| supplier_explanation | supplier_free_text_capability_signal | 0 / 6 |

## Critical findings

- brief/complete-demo [exact]: brief.category — expected='cosmetic travel bags'; actual='bags'
- brief/complete-demo [exact]: brief.attributes — expected=[]; actual=[{'subject': 'BRANDING_NOTES', 'text': 'with our logo'}]
- brief/complete-demo [exact]: brief.requirements — expected=[{'kind': 'MATERIAL', 'importance': None, 'expected_value': {'value': 'recycled polyester'}}, {'kind': 'CERTIFICATION', 'importance': 'PREFERRED', 'expected_value': {'value': 'GRS'}}]; actual=[{'kind': 'MATERIAL', 'importance': None, 'expected_value': {'value': 'recycled polyester'}}, {'kind': 'UNIT_PRICE', 'importance': None, 'expected_value': {'amount': '5', 'currency': 'USD'}}, {'kind': 'CERTIFICATION', 'importance': 'PREFERRED', 'expected_value': {'value': 'GRS'}}, {'kind': 'CAPABILITY', 'importance': None, 'expected_value': {'capability_key': 'CUSTOM_BRANDING', 'value': True}}]
- brief/complete-demo [exact]: brief.ambiguities — expected=[]; actual=['The unit price is under USD 5; the price fields do not express the strict upper bound.']
- brief/missing-destination [exact]: brief.requirements — expected=[]; actual=[{'kind': 'MATERIAL', 'importance': None, 'expected_value': {'value': 'cotton'}}, {'kind': 'QUANTITY', 'importance': None, 'expected_value': {'quantity': 500}}, {'kind': 'DELIVERY', 'importance': None, 'expected_value': {'kind': 'DATE', 'date': '2026-12-01'}}]
- brief/missing-delivery [exact]: brief.category — expected='tote bags'; actual='bags'
- brief/missing-delivery [exact]: brief.requirements — expected=[]; actual=[{'kind': 'QUANTITY', 'importance': None, 'expected_value': {'quantity': 800}}]
- brief/missing-quantity [exact]: brief.requirements — expected=[]; actual=[{'kind': 'MATERIAL', 'importance': None, 'expected_value': {'value': 'recycled'}}]
- brief/required-certification [exact]: brief.product_name — expected='bags'; actual=None
- brief/ambiguous-delivery [exact]: brief.delivery_target — expected=None; actual={'kind': 'PERIOD', 'label': 'around November, maybe December', 'start_date': None, 'end_date': None}
- brief/ambiguous-delivery [exact]: brief.requirements — expected=[]; actual=[{'kind': 'QUANTITY', 'importance': None, 'expected_value': {'quantity': 100}}, {'kind': 'DELIVERY', 'importance': None, 'expected_value': {'kind': 'PERIOD', 'label': 'around November, maybe December', 'start_date': None, 'end_date': None}}]
- brief/ambiguous-delivery [exact]: brief.ambiguities — expected=['Delivery may be in November or December.']; actual=['The delivery timing is approximate and could be November or December; no year is stated.']
- brief/branding-unknown [exact]: brief.attributes — expected=[]; actual=[{'subject': 'BRANDING_NOTES', 'text': 'Branding has not been decided.'}]
- brief/branding-unknown [exact]: brief.requirements — expected=[]; actual=[{'kind': 'QUANTITY', 'importance': None, 'expected_value': {'quantity': 500}}]
- brief/non-invention [exact]: brief.category — expected='cosmetic bags'; actual='bags'
- brief/non-invention [exact]: brief.attributes — expected=[]; actual=[{'subject': 'OTHER_CONTEXT', 'text': 'For our new brand.'}]
- brief/boolean-branding [exact]: brief.category — expected='cosmetic bags'; actual='bags'
- brief/no-branding [exact]: brief.category — expected='cosmetic bags'; actual='bags'
- brief/categorical-branding [exact]: brief.requirements — expected=[{'kind': 'CAPABILITY', 'importance': 'REQUIRED', 'expected_value': {'capability_key': 'BRANDING_METHOD', 'value': 'screen printing'}}]; actual=[{'kind': 'QUANTITY', 'importance': None, 'expected_value': {'quantity': 750}}, {'kind': 'CAPABILITY', 'importance': 'REQUIRED', 'expected_value': {'capability_key': 'BRANDING_METHOD', 'value': 'screen printing'}}]
- brief/production-limit [exact]: brief.ambiguities — expected=[]; actual=['Production must take at most 30 days.']
- brief/explicit-moq [exact]: brief.ambiguities — expected=[]; actual=['MOQ must not exceed 500 units.']
- brief/price-currency [exact]: brief.requirements — expected=[{'kind': 'UNIT_PRICE', 'importance': 'REQUIRED', 'expected_value': {'amount': '6', 'currency': 'AUD'}}]; actual=[{'kind': 'QUANTITY', 'importance': None, 'expected_value': {'quantity': 100}}, {'kind': 'UNIT_PRICE', 'importance': 'REQUIRED', 'expected_value': {'amount': '6', 'currency': 'AUD'}}]
- brief/price-currency [exact]: brief.ambiguities — expected=[]; actual=["Unit price must be below AUD 6; the strict 'below' bound is not represented by the price value."]
- brief/delivery-period [exact]: brief.requirements — expected=[]; actual=[{'kind': 'QUANTITY', 'importance': None, 'expected_value': {'quantity': 900}}, {'kind': 'DELIVERY', 'importance': None, 'expected_value': {'kind': 'PERIOD', 'label': 'November 2026', 'start_date': '2026-11-01', 'end_date': '2026-11-30'}}]
- brief/relative-delivery [exact]: brief.requirements — expected=[]; actual=[{'kind': 'DELIVERY', 'importance': None, 'expected_value': {'kind': 'PERIOD', 'label': 'next month', 'start_date': None, 'end_date': None}}]
- brief/informational-packaging [exact]: brief.requirements — expected=[]; actual=[{'kind': 'QUANTITY', 'importance': None, 'expected_value': {'quantity': 350}}]
- brief/ambiguous-material [exact]: brief.ambiguities — expected=['Material may be cotton or polyester.']; actual=['Material might be cotton or polyester; undecided.']
- brief/untrusted-request [exact]: brief.category — expected='cosmetic bags'; actual='bags'
- quote_extraction/harbor-primary [exact]: field_accuracy — See case output.
- quote_extraction/harbor-primary [exact]: unknown_detection — See case output.
- quote_extraction/harbor-primary [exact]: source_block_accuracy — See case output.
- quote_extraction/harbor-primary [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/harbor-primary [exact]: field.supplier_notes.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "SYNTHETIC DEMO QUOTE - NOT A REAL SUPPLIER OFFER", "source_block_ids": ["p1-b1", "p2-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": null, "source_match": false, "source_rule": null}
- quote_extraction/willow-primary [exact]: field_accuracy — See case output.
- quote_extraction/willow-primary [exact]: unknown_detection — See case output.
- quote_extraction/willow-primary [exact]: source_block_accuracy — See case output.
- quote_extraction/willow-primary [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/willow-primary [exact]: field.supplier_notes.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "SYNTHETIC DEMO QUOTE - NOT A REAL SUPPLIER OFFER", "source_block_ids": ["p1-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": null, "source_match": false, "source_rule": null}
- quote_extraction/moss-primary [exact]: field_accuracy — See case output.
- quote_extraction/moss-primary [exact]: unknown_detection — See case output.
- quote_extraction/moss-primary [exact]: source_block_accuracy — See case output.
- quote_extraction/moss-primary [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/moss-primary [exact]: field.supplier_notes.field_assignment — {"actual": {"conflicting_values": [], "extracted_value": "SYNTHETIC DEMO QUOTE - NOT A REAL SUPPLIER OFFER", "source_block_ids": ["p1-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "field_assignment", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": "approved_demo_notice", "source_match": false, "source_rule": null}
- quote_extraction/missing-shipping [exact]: field_accuracy — See case output.
- quote_extraction/missing-shipping [exact]: unknown_detection — See case output.
- quote_extraction/missing-shipping [exact]: source_block_accuracy — See case output.
- quote_extraction/missing-shipping [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/missing-shipping [exact]: field.supplier_notes.field_assignment — {"actual": {"conflicting_values": [], "extracted_value": "SYNTHETIC DEMO QUOTE - NOT A REAL SUPPLIER OFFER", "source_block_ids": ["p1-b1", "p2-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "field_assignment", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": "approved_demo_notice", "source_match": false, "source_rule": null}
- quote_extraction/conflicting-lead-time [exact]: field_accuracy — See case output.
- quote_extraction/conflicting-lead-time [exact]: unknown_detection — See case output.
- quote_extraction/conflicting-lead-time [exact]: source_block_accuracy — See case output.
- quote_extraction/conflicting-lead-time [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/conflicting-lead-time [exact]: field.supplier_notes.field_assignment — {"actual": {"conflicting_values": [], "extracted_value": "Synthetic demo quote - not a real supplier offer", "source_block_ids": ["p1-b1", "p2-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "field_assignment", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": "approved_demo_notice", "source_match": false, "source_rule": null}
- quote_extraction/included-tooling [exact]: field_accuracy — See case output.
- quote_extraction/included-tooling [exact]: unknown_detection — See case output.
- quote_extraction/included-tooling [exact]: source_block_accuracy — See case output.
- quote_extraction/included-tooling [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/included-tooling [exact]: field.supplier_notes.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "Synthetic demo quote \u2014 not a real supplier offer", "source_block_ids": ["p1-b1", "p2-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": null, "source_match": false, "source_rule": null}
- quote_extraction/missing-moq [exact]: field_accuracy — See case output.
- quote_extraction/missing-moq [exact]: unknown_detection — See case output.
- quote_extraction/missing-moq [exact]: source_block_accuracy — See case output.
- quote_extraction/missing-moq [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/missing-moq [exact]: field.supplier_notes.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "Synthetic demo quote - not a real supplier offer", "source_block_ids": ["p1-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": null, "source_match": false, "source_rule": null}
- quote_extraction/quantity-mismatch [exact]: field_accuracy — See case output.
- quote_extraction/quantity-mismatch [exact]: unknown_detection — See case output.
- quote_extraction/quantity-mismatch [exact]: source_block_accuracy — See case output.
- quote_extraction/quantity-mismatch [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/quantity-mismatch [exact]: field.supplier_notes.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "Synthetic demo quote - not a real supplier offer", "source_block_ids": ["p1-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": null, "source_match": false, "source_rule": null}
- quote_extraction/explicit-unknown [exact]: field_accuracy — See case output.
- quote_extraction/explicit-unknown [exact]: unknown_detection — See case output.
- quote_extraction/explicit-unknown [exact]: source_block_accuracy — See case output.
- quote_extraction/explicit-unknown [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/explicit-unknown [exact]: field.supplier_notes.field_assignment — {"actual": {"conflicting_values": [], "extracted_value": "Synthetic demo quote - not a real supplier offer", "source_block_ids": ["p1-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "field_assignment", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": "approved_demo_notice", "source_match": false, "source_rule": null}

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
