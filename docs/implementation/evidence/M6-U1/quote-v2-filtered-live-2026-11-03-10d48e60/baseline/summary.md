# SourcePilot live eval baseline

Status: **COMPLETED_WITH_FINDINGS**; exit 0.
Scope: quote_extraction. Full scope: False.
Accounted for: 12/12; complete: True.

Exit zero is execution completion, not live model-quality approval.
Automated completion does not prove free-text narrative groundedness.

| Category | Case | Status | Exact failures / heuristic signals |
| --- | --- | --- | --- |
| quote_extraction | harbor-primary | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.supplier_notes.unknown, exact: field.supplier_notes.unresolved_support |
| quote_extraction | willow-primary | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.currency.sources, exact: field.supplier_notes.unknown, exact: field.currency.misattributed_evidence, exact: field.supplier_notes.unresolved_support |
| quote_extraction | moss-primary | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.currency.sources, exact: field.supplier_notes.unknown, exact: field.currency.misattributed_evidence, exact: field.supplier_notes.unresolved_support |
| quote_extraction | missing-shipping | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.currency.sources, exact: field.exclusions.value, exact: field.supplier_notes.unknown, exact: field.currency.misattributed_evidence, exact: field.exclusions.unresolved_support, exact: field.supplier_notes.unresolved_support |
| quote_extraction | conflicting-lead-time | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.currency.sources, exact: field.supplier_notes.unknown, exact: field.currency.misattributed_evidence, exact: field.supplier_notes.unresolved_support |
| quote_extraction | included-tooling | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.currency.sources, exact: field.exclusions.value, exact: field.supplier_notes.unknown, exact: field.currency.misattributed_evidence, exact: field.exclusions.unresolved_support, exact: field.supplier_notes.unresolved_support |
| quote_extraction | missing-moq | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.currency.sources, exact: field.exclusions.value, exact: field.supplier_notes.unknown, exact: field.currency.misattributed_evidence, exact: field.exclusions.unresolved_support, exact: field.supplier_notes.unresolved_support |
| quote_extraction | quantity-mismatch | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.currency.sources, exact: field.certifications.value, exact: field.compliance_notes.unknown, exact: field.exclusions.value, exact: field.supplier_notes.unknown, exact: field.currency.misattributed_evidence, exact: field.certifications.unresolved_support, exact: field.compliance_notes.unresolved_support, exact: field.exclusions.unresolved_support, exact: field.supplier_notes.unresolved_support |
| quote_extraction | non-usd | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.currency.sources, exact: field.exclusions.value, exact: field.supplier_notes.unknown, exact: field.currency.misattributed_evidence, exact: field.exclusions.unresolved_support, exact: field.supplier_notes.unresolved_support |
| quote_extraction | explicit-unknown | QUALITY_FINDING | exact: field_accuracy, exact: unknown_detection, exact: source_block_accuracy, exact: field.currency.sources, exact: field.exclusions.value, exact: field.supplier_notes.unknown, exact: field.currency.misattributed_evidence, exact: field.exclusions.unresolved_support, exact: field.supplier_notes.unresolved_support |
| quote_extraction | unsupported-image-only | EXPECTED_REJECTION |  |
| quote_extraction | malformed-pdf | EXPECTED_REJECTION |  |

## Exact deterministic assertions (passed / checked)

| Category | Assertion | Counts |
| --- | --- | --- |
| quote_extraction | conflict_detection | 10 / 10 |
| quote_extraction | currency_accuracy | 10 / 10 |
| quote_extraction | field.certifications.sources | 7 / 7 |
| quote_extraction | field.certifications.unknown | 3 / 3 |
| quote_extraction | field.certifications.unresolved_support | 0 / 1 |
| quote_extraction | field.certifications.value | 6 / 7 |
| quote_extraction | field.compliance_notes.unknown | 9 / 10 |
| quote_extraction | field.compliance_notes.unresolved_support | 0 / 1 |
| quote_extraction | field.currency.misattributed_evidence | 0 / 9 |
| quote_extraction | field.currency.sources | 1 / 10 |
| quote_extraction | field.currency.value | 10 / 10 |
| quote_extraction | field.exclusions.sources | 7 / 7 |
| quote_extraction | field.exclusions.unknown | 3 / 3 |
| quote_extraction | field.exclusions.unresolved_support | 0 / 6 |
| quote_extraction | field.exclusions.value | 1 / 7 |
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
| quote_extraction | field.supplier_notes.unknown | 0 / 10 |
| quote_extraction | field.supplier_notes.unresolved_support | 0 / 10 |
| quote_extraction | field.tooling_cost.sources | 9 / 9 |
| quote_extraction | field.tooling_cost.unknown | 1 / 1 |
| quote_extraction | field.tooling_cost.value | 9 / 9 |
| quote_extraction | field.total_lead_time.unknown | 10 / 10 |
| quote_extraction | field.unit_price.sources | 10 / 10 |
| quote_extraction | field.unit_price.value | 10 / 10 |
| quote_extraction | field.warranty.unknown | 10 / 10 |
| quote_extraction | field_accuracy | 0 / 10 |
| quote_extraction | hallucination_rate | 10 / 10 |
| quote_extraction | numeric_accuracy | 10 / 10 |
| quote_extraction | parser_rejection | 2 / 2 |
| quote_extraction | source_block_accuracy | 0 / 10 |
| quote_extraction | source_references | 10 / 10 |
| quote_extraction | unknown_detection | 0 / 10 |

## Measured metrics (numerator / denominator)

| Category | Metric | Kind | Counts | Measured cases |
| --- | --- | --- | --- | --- |
| quote_extraction | conflict_detection | exact | 1 / 1 | 10 |
| quote_extraction | currency_accuracy | exact | 10 / 10 | 10 |
| quote_extraction | expected_unknown_known_rate | exact | 11 / 85 | 10 |
| quote_extraction | field_accuracy | exact | 192 / 210 | 10 |
| quote_extraction | hallucination_rate | exact | 0 / 85 | 10 |
| quote_extraction | numeric_accuracy | exact | 55 / 55 | 10 |
| quote_extraction | source_block_accuracy | exact | 190 / 210 | 10 |
| quote_extraction | unknown_detection | exact | 74 / 85 | 10 |
| quote_extraction | unresolved_support_rate | exact | 18 / 210 | 10 |
| quote_extraction | unsupported_value_rate | exact | 0 / 210 | 10 |

Zero denominators are not applicable. Exact assertion pass counts are separate in results.json.
Failed runtime cases remain in case/status totals even when extracted-value metrics are unavailable.

## Heuristic signals (triggered / inspected)

A non-trigger is not a factual-groundedness pass. These are bounded warning cues.

| Category | Signal | Counts |
| --- | --- | --- |

## Critical findings

- quote_extraction/harbor-primary [exact]: field_accuracy — See case output.
- quote_extraction/harbor-primary [exact]: unknown_detection — See case output.
- quote_extraction/harbor-primary [exact]: source_block_accuracy — See case output.
- quote_extraction/harbor-primary [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/harbor-primary [exact]: field.supplier_notes.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "SYNTHETIC DEMO QUOTE - NOT A REAL SUPPLIER OFFER", "source_block_ids": ["p1-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": null, "source_match": false}
- quote_extraction/willow-primary [exact]: field_accuracy — See case output.
- quote_extraction/willow-primary [exact]: unknown_detection — See case output.
- quote_extraction/willow-primary [exact]: source_block_accuracy — See case output.
- quote_extraction/willow-primary [exact]: field.currency.sources — {"actual": ["p1-b5", "p1-b7", "p1-b8", "p1-b11"], "expected": ["p1-b5"], "rule": "evidence_mismatch"}
- quote_extraction/willow-primary [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/willow-primary [exact]: field.currency.misattributed_evidence — {"actual": {"conflicting_values": [], "extracted_value": "USD", "source_block_ids": ["p1-b5", "p1-b7", "p1-b8", "p1-b11"], "state": "KNOWN", "uncertainty": null}, "classification": "misattributed_evidence", "expected": ["USD", ["p1-b5"]], "field": "currency", "field_match": true, "rule": "exact_value", "source_match": false}
- quote_extraction/willow-primary [exact]: field.supplier_notes.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "Synthetic demo quote \u2014 not a real supplier offer.", "source_block_ids": ["p1-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": null, "source_match": false}
- quote_extraction/moss-primary [exact]: field_accuracy — See case output.
- quote_extraction/moss-primary [exact]: unknown_detection — See case output.
- quote_extraction/moss-primary [exact]: source_block_accuracy — See case output.
- quote_extraction/moss-primary [exact]: field.currency.sources — {"actual": ["p1-b5", "p1-b7", "p1-b8", "p1-b11"], "expected": ["p1-b5"], "rule": "evidence_mismatch"}
- quote_extraction/moss-primary [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/moss-primary [exact]: field.currency.misattributed_evidence — {"actual": {"conflicting_values": [], "extracted_value": "USD", "source_block_ids": ["p1-b5", "p1-b7", "p1-b8", "p1-b11"], "state": "KNOWN", "uncertainty": null}, "classification": "misattributed_evidence", "expected": ["USD", ["p1-b5"]], "field": "currency", "field_match": true, "rule": "exact_value", "source_match": false}
- quote_extraction/moss-primary [exact]: field.supplier_notes.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "SYNTHETIC DEMO QUOTE - NOT A REAL SUPPLIER OFFER", "source_block_ids": ["p1-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": null, "source_match": false}
- quote_extraction/missing-shipping [exact]: field_accuracy — See case output.
- quote_extraction/missing-shipping [exact]: unknown_detection — See case output.
- quote_extraction/missing-shipping [exact]: source_block_accuracy — See case output.
- quote_extraction/missing-shipping [exact]: field.currency.sources — {"actual": ["p1-b5", "p1-b7", "p1-b8"], "expected": ["p1-b5"], "rule": "evidence_mismatch"}
- quote_extraction/missing-shipping [exact]: field.exclusions.value — {"actual": "Import duties are not included", "expected": "import duties are not included", "rule": null, "uncertainty": null}
- quote_extraction/missing-shipping [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/missing-shipping [exact]: field.currency.misattributed_evidence — {"actual": {"conflicting_values": [], "extracted_value": "USD", "source_block_ids": ["p1-b5", "p1-b7", "p1-b8"], "state": "KNOWN", "uncertainty": null}, "classification": "misattributed_evidence", "expected": ["USD", ["p1-b5"]], "field": "currency", "field_match": true, "rule": "exact_value", "source_match": false}
- quote_extraction/missing-shipping [exact]: field.exclusions.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "Import duties are not included", "source_block_ids": ["p2-b7"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": ["import duties are not included", ["p2-b7"]], "field": "exclusions", "field_match": false, "rule": null, "source_match": true}
- quote_extraction/missing-shipping [exact]: field.supplier_notes.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "SYNTHETIC DEMO QUOTE - NOT A REAL SUPPLIER OFFER", "source_block_ids": ["p1-b1", "p2-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": null, "source_match": false}
- quote_extraction/conflicting-lead-time [exact]: field_accuracy — See case output.
- quote_extraction/conflicting-lead-time [exact]: unknown_detection — See case output.
- quote_extraction/conflicting-lead-time [exact]: source_block_accuracy — See case output.
- quote_extraction/conflicting-lead-time [exact]: field.currency.sources — {"actual": ["p1-b5", "p1-b7", "p1-b8", "p1-b11"], "expected": ["p1-b5"], "rule": "evidence_mismatch"}
- quote_extraction/conflicting-lead-time [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/conflicting-lead-time [exact]: field.currency.misattributed_evidence — {"actual": {"conflicting_values": [], "extracted_value": "USD", "source_block_ids": ["p1-b5", "p1-b7", "p1-b8", "p1-b11"], "state": "KNOWN", "uncertainty": null}, "classification": "misattributed_evidence", "expected": ["USD", ["p1-b5"]], "field": "currency", "field_match": true, "rule": "exact_value", "source_match": false}
- quote_extraction/conflicting-lead-time [exact]: field.supplier_notes.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "Synthetic demo quote - not a real supplier offer", "source_block_ids": ["p1-b1", "p2-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": null, "source_match": false}
- quote_extraction/included-tooling [exact]: field_accuracy — See case output.
- quote_extraction/included-tooling [exact]: unknown_detection — See case output.
- quote_extraction/included-tooling [exact]: source_block_accuracy — See case output.
- quote_extraction/included-tooling [exact]: field.currency.sources — {"actual": ["p1-b5", "p1-b8", "p1-b11"], "expected": ["p1-b5"], "rule": "evidence_mismatch"}
- quote_extraction/included-tooling [exact]: field.exclusions.value — {"actual": "Import duties are not included", "expected": "import duties are not included", "rule": null, "uncertainty": null}
- quote_extraction/included-tooling [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/included-tooling [exact]: field.currency.misattributed_evidence — {"actual": {"conflicting_values": [], "extracted_value": "USD", "source_block_ids": ["p1-b5", "p1-b8", "p1-b11"], "state": "KNOWN", "uncertainty": null}, "classification": "misattributed_evidence", "expected": ["USD", ["p1-b5"]], "field": "currency", "field_match": true, "rule": "exact_value", "source_match": false}
- quote_extraction/included-tooling [exact]: field.exclusions.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "Import duties are not included", "source_block_ids": ["p2-b7"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": ["import duties are not included", ["p2-b7"]], "field": "exclusions", "field_match": false, "rule": null, "source_match": true}
- quote_extraction/included-tooling [exact]: field.supplier_notes.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "Synthetic demo quote - not a real supplier offer", "source_block_ids": ["p1-b1", "p2-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": null, "source_match": false}
- quote_extraction/missing-moq [exact]: field_accuracy — See case output.
- quote_extraction/missing-moq [exact]: unknown_detection — See case output.
- quote_extraction/missing-moq [exact]: source_block_accuracy — See case output.
- quote_extraction/missing-moq [exact]: field.currency.sources — {"actual": ["p1-b5", "p1-b6", "p1-b7", "p1-b10"], "expected": ["p1-b5"], "rule": "evidence_mismatch"}
- quote_extraction/missing-moq [exact]: field.exclusions.value — {"actual": "Import duties are not included", "expected": "import duties are not included", "rule": null, "uncertainty": null}
- quote_extraction/missing-moq [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/missing-moq [exact]: field.currency.misattributed_evidence — {"actual": {"conflicting_values": [], "extracted_value": "USD", "source_block_ids": ["p1-b5", "p1-b6", "p1-b7", "p1-b10"], "state": "KNOWN", "uncertainty": null}, "classification": "misattributed_evidence", "expected": ["USD", ["p1-b5"]], "field": "currency", "field_match": true, "rule": "exact_value", "source_match": false}
- quote_extraction/missing-moq [exact]: field.exclusions.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "Import duties are not included", "source_block_ids": ["p2-b7"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": ["import duties are not included", ["p2-b7"]], "field": "exclusions", "field_match": false, "rule": null, "source_match": true}
- quote_extraction/missing-moq [exact]: field.supplier_notes.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "SYNTHETIC DEMO QUOTE - NOT A REAL SUPPLIER OFFER", "source_block_ids": ["p1-b1", "p2-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": null, "source_match": false}
- quote_extraction/quantity-mismatch [exact]: field_accuracy — See case output.
- quote_extraction/quantity-mismatch [exact]: unknown_detection — See case output.
- quote_extraction/quantity-mismatch [exact]: source_block_accuracy — See case output.
- quote_extraction/quantity-mismatch [exact]: field.currency.sources — {"actual": ["p1-b5", "p1-b7", "p1-b8", "p1-b11"], "expected": ["p1-b5"], "rule": "evidence_mismatch"}
- quote_extraction/quantity-mismatch [exact]: field.certifications.value — {"actual": "Synthetic GRS record; current for this fictional supplier", "expected": "Synthetic GRS record: current for this fictional supplier", "rule": null, "uncertainty": null}
- quote_extraction/quantity-mismatch [exact]: field.compliance_notes.unknown — See case output.
- quote_extraction/quantity-mismatch [exact]: field.exclusions.value — {"actual": "Import duties are not included", "expected": "import duties are not included", "rule": null, "uncertainty": null}
- quote_extraction/quantity-mismatch [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/quantity-mismatch [exact]: field.currency.misattributed_evidence — {"actual": {"conflicting_values": [], "extracted_value": "USD", "source_block_ids": ["p1-b5", "p1-b7", "p1-b8", "p1-b11"], "state": "KNOWN", "uncertainty": null}, "classification": "misattributed_evidence", "expected": ["USD", ["p1-b5"]], "field": "currency", "field_match": true, "rule": "exact_value", "source_match": false}
- quote_extraction/quantity-mismatch [exact]: field.certifications.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "Synthetic GRS record; current for this fictional supplier", "source_block_ids": ["p2-b4"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": ["Synthetic GRS record: current for this fictional supplier", ["p2-b4"]], "field": "certifications", "field_match": false, "rule": null, "source_match": true}
- quote_extraction/quantity-mismatch [exact]: field.compliance_notes.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "Synthetic GRS record; current for this fictional supplier", "source_block_ids": ["p2-b4"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": "UNKNOWN", "field": "compliance_notes", "field_match": false, "rule": null, "source_match": false}
- quote_extraction/quantity-mismatch [exact]: field.exclusions.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "Import duties are not included", "source_block_ids": ["p2-b7"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": ["import duties are not included", ["p2-b7"]], "field": "exclusions", "field_match": false, "rule": null, "source_match": true}
- quote_extraction/quantity-mismatch [exact]: field.supplier_notes.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "Synthetic demo quote\u2014not a real supplier offer", "source_block_ids": ["p1-b1", "p2-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": null, "source_match": false}
- quote_extraction/non-usd [exact]: field_accuracy — See case output.
- quote_extraction/non-usd [exact]: unknown_detection — See case output.
- quote_extraction/non-usd [exact]: source_block_accuracy — See case output.
- quote_extraction/non-usd [exact]: field.currency.sources — {"actual": ["p1-b5", "p1-b7", "p1-b8", "p1-b11"], "expected": ["p1-b5"], "rule": "evidence_mismatch"}
- quote_extraction/non-usd [exact]: field.exclusions.value — {"actual": "Import duties are not included", "expected": "import duties are not included", "rule": null, "uncertainty": null}
- quote_extraction/non-usd [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/non-usd [exact]: field.currency.misattributed_evidence — {"actual": {"conflicting_values": [], "extracted_value": "AUD", "source_block_ids": ["p1-b5", "p1-b7", "p1-b8", "p1-b11"], "state": "KNOWN", "uncertainty": null}, "classification": "misattributed_evidence", "expected": ["AUD", ["p1-b5"]], "field": "currency", "field_match": true, "rule": "exact_value", "source_match": false}
- quote_extraction/non-usd [exact]: field.exclusions.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "Import duties are not included", "source_block_ids": ["p2-b7"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": ["import duties are not included", ["p2-b7"]], "field": "exclusions", "field_match": false, "rule": null, "source_match": true}
- quote_extraction/non-usd [exact]: field.supplier_notes.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "SYNTHETIC DEMO QUOTE - NOT A REAL SUPPLIER OFFER", "source_block_ids": ["p1-b1", "p2-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": null, "source_match": false}
- quote_extraction/explicit-unknown [exact]: field_accuracy — See case output.
- quote_extraction/explicit-unknown [exact]: unknown_detection — See case output.
- quote_extraction/explicit-unknown [exact]: source_block_accuracy — See case output.
- quote_extraction/explicit-unknown [exact]: field.currency.sources — {"actual": ["p1-b5", "p1-b7"], "expected": ["p1-b5"], "rule": "evidence_mismatch"}
- quote_extraction/explicit-unknown [exact]: field.exclusions.value — {"actual": "Import duties are not included", "expected": "import duties are not included", "rule": null, "uncertainty": null}
- quote_extraction/explicit-unknown [exact]: field.supplier_notes.unknown — See case output.
- quote_extraction/explicit-unknown [exact]: field.currency.misattributed_evidence — {"actual": {"conflicting_values": [], "extracted_value": "USD", "source_block_ids": ["p1-b5", "p1-b7"], "state": "KNOWN", "uncertainty": null}, "classification": "misattributed_evidence", "expected": ["USD", ["p1-b5"]], "field": "currency", "field_match": true, "rule": "exact_value", "source_match": false}
- quote_extraction/explicit-unknown [exact]: field.exclusions.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "Import duties are not included", "source_block_ids": ["p2-b7"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": ["import duties are not included", ["p2-b7"]], "field": "exclusions", "field_match": false, "rule": null, "source_match": true}
- quote_extraction/explicit-unknown [exact]: field.supplier_notes.unresolved_support — {"actual": {"conflicting_values": [], "extracted_value": "Synthetic demo quote - not a real supplier offer", "source_block_ids": ["p1-b1"], "state": "KNOWN", "uncertainty": null}, "classification": "unresolved_support", "expected": "UNKNOWN", "field": "supplier_notes", "field_match": false, "rule": null, "source_match": false}

## Human review required — PENDING

0 difficult narrative examples require a person's judgment. No result has been recorded.

| Example | Review criterion |
| --- | --- |

Source: apps/api/evals/human_review/narrative_cases.json.
No production tuning or release acceptance is implied by this baseline.
