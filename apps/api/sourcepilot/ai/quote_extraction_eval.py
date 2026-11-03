"""Versioned, offline quote-extraction cases and deterministic scoring."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sourcepilot.ai.quote_extractor import INSTRUCTIONS, QuoteExtraction
from sourcepilot.ai.structured import structured_input_hash
from sourcepilot.documents.parse_pdf import ParsedBlock
from sourcepilot.quotes.domain import QUOTE_FIELD_KEYS, QUOTE_INTEGER_FIELDS, QUOTE_MONEY_FIELDS

EVAL_DIRECTORY = Path(__file__).resolve().parents[2] / "evals" / "quote_extraction"


def load_cases() -> list[dict[str, Any]]:
    return json.loads((EVAL_DIRECTORY / "cases.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def load_recorded_outputs() -> dict[str, dict[str, Any]]:
    return json.loads((EVAL_DIRECTORY / "model_outputs.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


class QuoteScorerContextError(ValueError):
    """Missing, incomplete or wrong-document parsed evidence; never a quality finding."""


def bind_document(case: dict[str, Any], pdf: Path, blocks: list[ParsedBlock]) -> None:
    """Attach transient parsed context, never change the dataset or expected citations."""
    case["_scoring_document"] = {
        "pdf": pdf.name,
        "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "blocks": [[block.reference, block.text] for block in blocks],
    }
    document_blocks(case)


def document_blocks(case: dict[str, Any]) -> dict[str, str]:
    context = case.get("_scoring_document")
    if not isinstance(context, dict) or context.get("pdf") != case["pdf"]:
        raise QuoteScorerContextError("Complete parsed context for the selected PDF is required.")
    pdf = EVAL_DIRECTORY.parents[1] / "tests/fixtures/quote_pdfs" / case["pdf"]
    if context.get("sha256") != hashlib.sha256(pdf.read_bytes()).hexdigest():
        raise QuoteScorerContextError("Parsed evidence PDF identity differs from the selected PDF.")
    pairs = context.get("blocks")
    if not isinstance(pairs, list) or not pairs:
        raise QuoteScorerContextError("Complete parsed blocks are required.")
    blocks = dict(pairs)
    input_text = json.dumps(
        {"document_blocks": [{"id": ref, "text": text} for ref, text in pairs]},
        ensure_ascii=False, separators=(",", ":"),
    )
    if len(blocks) != len(pairs) or structured_input_hash(
        instructions=INSTRUCTIONS, input_text=input_text,
    ) != case["request_hash"]:
        raise QuoteScorerContextError("Parsed evidence differs from the case's complete request binding.")
    return blocks


HARBOR_CURRENCY_BLOCKS = {
    "p1-b5": "Unit price: USD 4.60",
    "p1-b7": "Tooling/setup cost: USD 150",
    "p1-b8": "Sample cost: USD 40",
    "p1-b11": "Shipping cost: USD 320 to Manila",
}
HARBOR_CERTIFICATION = "Synthetic GRS record: current for this fictional supplier"
HARBOR_QUALIFICATION = (
    "The document describes this as a synthetic record, current for this fictional supplier."
)
HARBOR_NOTICE = "SYNTHETIC DEMO QUOTE - NOT A REAL SUPPLIER OFFER"
# Explicit fixture identities and full citation alternatives approved in M6-U1.
APPROVED_PDFS = {
    "harbor-primary": "harbor_primary.pdf",
    "willow-primary": "willow_primary.pdf",
    "moss-primary": "moss_primary.pdf",
    "missing-shipping": "missing_shipping.pdf",
    "conflicting-lead-time": "conflicting_lead_time.pdf",
    "included-tooling": "included_tooling.pdf",
    "missing-moq": "missing_moq.pdf",
    "quantity-mismatch": "quantity_mismatch.pdf",
    "non-usd": "non_usd.pdf",
    "explicit-unknown": "explicit_unknown.pdf",
}
# Currency, unit price, and exact additional supporting block texts.
CURRENCY_ALTERNATIVES = {
    "willow-primary": (
        "USD",
        "4.20",
        {
            "p1-b7": "Tooling/setup cost: USD 100",
            "p1-b8": "Sample cost: USD 35",
            "p1-b11": "Shipping cost: USD 280 to Manila",
        },
    ),
    "moss-primary": (
        "USD",
        "4.45",
        {
            "p1-b7": "Tooling/setup cost: USD 600",
            "p1-b8": "Sample cost: USD 45",
            "p1-b11": "Shipping cost: USD 360 to Manila",
        },
    ),
    "missing-shipping": (
        "USD",
        "4.60",
        {"p1-b7": "Tooling/setup cost: USD 150", "p1-b8": "Sample cost: USD 40"},
    ),
    "conflicting-lead-time": (
        "USD",
        "4.45",
        {
            "p1-b7": "Tooling/setup cost: USD 600",
            "p1-b8": "Sample cost: USD 45",
            "p1-b11": "Shipping cost: USD 360 to Manila",
        },
    ),
    "included-tooling": (
        "USD",
        "4.60",
        {"p1-b8": "Sample cost: USD 40", "p1-b11": "Shipping cost: USD 320 to Manila"},
    ),
    "missing-moq": (
        "USD",
        "4.60",
        {
            "p1-b6": "Tooling/setup cost: USD 150",
            "p1-b7": "Sample cost: USD 40",
            "p1-b10": "Shipping cost: USD 320 to Manila",
        },
    ),
    "quantity-mismatch": (
        "USD",
        "4.60",
        {
            "p1-b7": "Tooling/setup cost: USD 150",
            "p1-b8": "Sample cost: USD 40",
            "p1-b11": "Shipping cost: USD 320 to Manila",
        },
    ),
    "non-usd": (
        "AUD",
        "4.60",
        {
            "p1-b7": "Tooling/setup cost: AUD 150",
            "p1-b8": "Sample cost: AUD 40",
            "p1-b11": "Shipping cost: AUD 320 to Manila",
        },
    ),
    "explicit-unknown": ("USD", "4.60", {"p1-b7": "Tooling/setup cost: USD 150"}),
}
EXCLUSION_CASES = {
    "missing-shipping",
    "included-tooling",
    "missing-moq",
    "quantity-mismatch",
    "non-usd",
    "explicit-unknown",
}
NOTICE_VALUES = {
    "harbor-primary": HARBOR_NOTICE,
    "moss-primary": HARBOR_NOTICE,
    "missing-shipping": HARBOR_NOTICE,
    "missing-moq": HARBOR_NOTICE,
    "non-usd": HARBOR_NOTICE,
    "willow-primary": "Synthetic demo quote \u2014 not a real supplier offer.",
    "quantity-mismatch": "Synthetic demo quote\u2014not a real supplier offer",
    "conflicting-lead-time": "Synthetic demo quote - not a real supplier offer",
    "included-tooling": "Synthetic demo quote - not a real supplier offer",
    "explicit-unknown": "Synthetic demo quote - not a real supplier offer",
}


def _approved_case(case: dict[str, Any]) -> bool:
    return case["id"] in APPROVED_PDFS and case["pdf"] == APPROVED_PDFS[case["id"]]


METRIC_NAMES = (
    "field_accuracy", "numeric_accuracy", "currency_accuracy", "unknown_detection",
    "conflict_detection", "source_block_accuracy", "hallucination_rate",
)


def _harbor(case: dict[str, Any]) -> bool:
    return case["id"] == "harbor-primary" and case["pdf"] == "harbor_primary.pdf"


def _same_value(key: str, actual: Any, expected: Any) -> bool:
    if key in QUOTE_MONEY_FIELDS and actual is not None:
        return Decimal(str(actual)) == Decimal(str(expected))
    return actual == expected


def _same_documented_fact(key: str, actual: Any, expected: Any) -> bool:
    # Cross-field numeric support is separate from accepting a field's representation.
    if key in QUOTE_INTEGER_FIELDS | QUOTE_MONEY_FIELDS:
        try:
            return Decimal(str(actual)) == Decimal(str(expected))
        except InvalidOperation:
            return False
    return actual == expected


def value_rule(
    key: str, field: dict[str, Any], case: dict[str, Any], blocks: dict[str, str],
) -> str | None:
    """Only the reviewed case/field/content-specific representations are equivalent."""
    value = field["extracted_value"]
    expected = case["known"][key][0]
    if _same_value(key, value, expected):
        return "exact_value"
    if _approved_case(case) and field["uncertainty"] is None:
        if (case["id"] in EXCLUSION_CASES and key == "exclusions"
                and expected == "import duties are not included"
                and value == "Import duties are not included"
                and set(field["source_block_ids"]) == {"p2-b7"}
                and blocks.get("p2-b7") == "Exclusion: import duties are not included"):
            return "approved_exclusion_initial_case"
        if (case["id"] == "quantity-mismatch" and key == "certifications"
                and expected == HARBOR_CERTIFICATION
                and value == "Synthetic GRS record; current for this fictional supplier"
                and set(field["source_block_ids"]) == {"p2-b4"}
                and blocks.get("p2-b4") == HARBOR_CERTIFICATION):
            return "quantity_mismatch_certification_punctuation"
    if _harbor(case):
        if (key == "exclusions" and expected == "import duties are not included"
                and isinstance(value, str) and value.casefold() == expected.casefold()
                and blocks.get("p2-b7") == "Exclusion: import duties are not included"):
            return "harbor_exclusion_case"
        if (key == "certifications" and expected == HARBOR_CERTIFICATION and value == "GRS"
                and field["uncertainty"] == HARBOR_QUALIFICATION
                and set(field["source_block_ids"]) == {"p2-b4"}
                and blocks.get("p2-b4") == HARBOR_CERTIFICATION):
            return "harbor_qualified_grs"
    return None


def source_rule(
    key: str, field: dict[str, Any], case: dict[str, Any], blocks: dict[str, str],
) -> str | None:
    references = set(field["source_block_ids"])
    if not references <= blocks.keys():
        return None
    if key in case["known"]:
        if (_harbor(case) and key == "currency" and case["known"][key][0] == "USD"
                and field["extracted_value"] == "USD" and references
                and references <= HARBOR_CURRENCY_BLOCKS.keys()
                and all(blocks[ref] == HARBOR_CURRENCY_BLOCKS[ref] for ref in references)):
            return "harbor_currency_usd"
        if _approved_case(case) and key == "currency" and case["id"] in CURRENCY_ALTERNATIVES:
            currency, price, extras = CURRENCY_ALTERNATIVES[case["id"]]
            support = {"p1-b5": f"Unit price: {currency} {price}", **extras}
            if (case["known"][key] == [currency, ["p1-b5"]]
                    and field["extracted_value"] == currency
                    and references == support.keys()
                    and all(blocks.get(ref) == text for ref, text in support.items())):
                return f"{case['id']}_currency_{currency.lower()}"
        return "exact_evidence" if references == set(case["known"][key][1]) else None
    if key in case["conflicts"]:
        # Pairing remains exact, separately from the union's document membership.
        expected = sorted(json.dumps([value, sorted(refs)])
                          for value, refs in case["conflicts"][key])
        actual = sorted(json.dumps([item["value"], sorted(item["source_block_ids"])])
                        for item in field["conflicting_values"])
        return "exact_conflict_evidence" if (actual == expected and references == {
            ref for _, refs in case["conflicts"][key] for ref in refs
        }) else None
    return "exact_evidence" if references == set(case["unknown_sources"].get(key, [])) else None


def field_evaluations(result: QuoteExtraction, case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    blocks = document_blocks(case)
    fields = result.model_dump(mode="json")["fields"]
    evaluations = {}
    for key, field in fields.items():
        rule = None
        matched_source_rule = source_rule(key, field, case, blocks)
        source_match = matched_source_rule is not None
        if key in case["known"]:
            rule = value_rule(key, field, case, blocks)
            match = field["state"] == "KNOWN" and rule is not None
        elif key in case["conflicts"]:
            match = (field["state"] == "CONFLICT" and field["extracted_value"] is None
                     and source_match)
        else:
            match = field["state"] == "UNKNOWN" and field["extracted_value"] is None
        classification = "accepted" if match and source_match else "field_correctness"
        if field["state"] == "KNOWN":
            if match:
                classification = "accepted" if source_match else "misattributed_evidence"
            else:
                # Only a reviewed disclaimer exception, never a generic notes rule.
                refs = set(field["source_block_ids"])
                notice_refs = ({"p1-b1"} if case["id"] in {
                    "harbor-primary", "willow-primary", "moss-primary", "explicit-unknown",
                } else {"p1-b1", "p2-b1"})
                notice = (_approved_case(case) and key == "supplier_notes"
                          and field["uncertainty"] is None
                          and ((field["extracted_value"] == NOTICE_VALUES[case["id"]]
                                and refs == notice_refs)
                               or (_harbor(case) and field["extracted_value"] ==
                                   "Synthetic demo quote - not a real supplier offer"
                                   and bool(refs) and refs <= {"p1-b1", "p2-b1"}))
                          and all(blocks.get(ref) == HARBOR_NOTICE for ref in refs))
                compliance_duplicate = (
                    _approved_case(case) and case["id"] == "quantity-mismatch"
                    and key == "compliance_notes" and field["uncertainty"] is None
                    and field["extracted_value"] == "Synthetic GRS record; current for this fictional supplier"
                    and refs == {"p2-b4"} and blocks.get("p2-b4") == HARBOR_CERTIFICATION
                )
                other_fact = any(
                    field["uncertainty"] is None and other != key and _same_documented_fact(other, field["extracted_value"], value)
                    and refs == set(references) and refs <= blocks.keys()
                    for other, (value, references) in case["known"].items()
                )
                if notice or compliance_duplicate or other_fact:
                    classification = "field_assignment"
                    rule = ("approved_demo_notice" if notice else
                            "quantity_mismatch_compliance_duplicate" if compliance_duplicate
                            else "other_expected_fact")
                elif key in QUOTE_INTEGER_FIELDS | QUOTE_MONEY_FIELDS or key == "currency":
                    classification = "unsupported_value"
                else:
                    # No unrestricted entailment claim for unfamiliar natural language.
                    classification = "unresolved_support"
        evaluations[key] = {
            "field_match": match, "source_match": source_match,
            "classification": classification, "rule": rule, "source_rule": matched_source_rule,
        }
    return evaluations


def metric_counts(result: QuoteExtraction, case: dict[str, Any]) -> dict[str, tuple[int, int]]:
    """Preserve field denominators; distinguish invention from assignment and unresolved prose."""
    actual = result.model_dump(mode="json")["fields"]
    evaluated = field_evaluations(result, case)
    known, conflicts = case["known"], case["conflicts"]
    unknown = QUOTE_FIELD_KEYS - known.keys() - conflicts.keys()
    numeric = QUOTE_INTEGER_FIELDS | QUOTE_MONEY_FIELDS
    unsupported = {key for key, item in evaluated.items()
                   if item["classification"] == "unsupported_value"}
    return {
        "field_accuracy": (sum(item["field_match"] for item in evaluated.values()), len(QUOTE_FIELD_KEYS)),
        "numeric_accuracy": (sum(evaluated[key]["field_match"] for key in known if key in numeric),
                             sum(key in numeric for key in known)),
        "currency_accuracy": (int(evaluated["currency"]["field_match"]), int("currency" in known))
        if "currency" in known else (0, 0),
        "unknown_detection": (sum(evaluated[key]["field_match"] for key in unknown), len(unknown)),
        "conflict_detection": (sum(evaluated[key]["field_match"] and evaluated[key]["source_match"]
                                   for key in conflicts), len(conflicts)),
        "source_block_accuracy": (sum(item["source_match"] for item in evaluated.values()), len(QUOTE_FIELD_KEYS)),
        "hallucination_rate": (len(unsupported & unknown), len(unknown)),
        "expected_unknown_known_rate": (sum(actual[key]["state"] == "KNOWN" for key in unknown), len(unknown)),
        "unsupported_value_rate": (len(unsupported), len(QUOTE_FIELD_KEYS)),
        "unresolved_support_rate": (sum(item["classification"] == "unresolved_support"
                                        for item in evaluated.values()), len(QUOTE_FIELD_KEYS)),
    }


def score_case(result: QuoteExtraction, case: dict[str, Any]) -> dict[str, float]:
    return {
        name: numerator / denominator
        if denominator
        else (0.0 if name == "hallucination_rate" else 1.0)
        for name, (numerator, denominator) in metric_counts(result, case).items()
        if name in METRIC_NAMES
    }
