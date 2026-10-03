"""Synthetic M4-U6 comparison and checks for produced analyst results."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from sourcepilot.ai.analyst_tools import ComparisonSnapshotResult, EvaluationAvailability
from sourcepilot.ai.tradeoff_analysis import TradeoffAnalysis, validate_analysis

CASES_PATH = Path(__file__).resolve().parents[2] / "evals" / "tradeoff_analysis" / "cases.json"
OUTPUTS_PATH = CASES_PATH.with_name("model_outputs.json")
A, B, C = ("11111111-1111-1111-1111-111111111111",
           "11111111-1111-1111-1111-111111111112",
           "11111111-1111-1111-1111-111111111113")
QA, QB, QC = ("22222222-2222-2222-2222-222222222221",
              "22222222-2222-2222-2222-222222222222",
              "22222222-2222-2222-2222-222222222223")
CERT, LEAD = ("33333333-3333-3333-3333-333333333331",
              "33333333-3333-3333-3333-333333333332")
PDF_PRICE = "44444444-4444-4444-4444-444444444441"
PRICE = re.compile(r"\bUSD\s*(\d+(?:\.\d+)?)|\b(\d+\.\d{2})\b", re.IGNORECASE)
QUANTITY = re.compile(
    r"\b(quoted quantity|MOQ|minimum order quantity|requested quantity)\s*"
    r"(?:is|of|:|=)?\s*([\d,]+)\b", re.IGNORECASE,
)
PROVENANCE = re.compile(r"\b(PDF|source|evidence|current|confirmed|corrected)\b", re.IGNORECASE)
PROVENANCE_CLAUSE = re.compile(
    r";|\.(?!\d)|\bversus\b|"
    r"\b(?:and|but)\b(?=\s+(?:(?:its|the|Supplier\s+[ABC](?:'s)?)\s+)?"
    r"(?:PDF|source|evidence|current|confirmed|corrected)\b)|"
    r",(?=\s*(?:(?:its|the|Supplier\s+[ABC](?:'s)?)\s+)?"
    r"(?:PDF|source|evidence|current|confirmed|corrected)\b)",
    re.IGNORECASE,
)


def load_cases() -> list[dict[str, Any]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def fixture_snapshot() -> ComparisonSnapshotResult:
    """One deterministic comparison with tradeoffs, failures, uncertainty, and correction."""
    def supplier(supplier_id: str, quote_id: str, price: str, days: int,
                 cert: str, lead: str, *, corrected: bool = False) -> dict[str, Any]:
        price_field: dict[str, Any] = {
            "field_key": "unit_price", "current_value": price,
            "current_origin": "USER_CORRECTED" if corrected else "USER_ENTERED",
            "evidence": ([{"id": PDF_PRICE, "evidence_value": "4.22"}] if corrected else []),
        }
        return {
            "supplier_id": supplier_id, "quote_id": quote_id,
            "supplier_name": f"Supplier {'ABC'[(A, B, C).index(supplier_id)]}",
            "quote_fields": [price_field, {"field_key": "production_lead_time",
                                           "current_value": days, "evidence": []},
                             {"field_key": "quoted_quantity", "current_value": {
                                 A: 2000, B: 5000, C: 2000}[supplier_id],
                              "evidence": []},
                             {"field_key": "moq", "current_value": {
                                 A: 500, B: 1000, C: 300}[supplier_id], "evidence": []}],
            "completeness": [{"field_key": "unit_price", "state": "known"},
                             {"field_key": "production_lead_time", "state": "known"}],
            "supplier_facts": {"evidence": []},
            "evaluation": {"results": [{"requirement_id": CERT, "status": cert},
                                       {"requirement_id": LEAD, "status": lead}]},
        }
    third = supplier(C, QC, "4.10", 30, "UNKNOWN", "MEETS")
    third["completeness"].append({"field_key": "shipping_cost", "state": "missing"})
    return ComparisonSnapshotResult(
        availability=EvaluationAvailability.CURRENT,
        snapshot_id=UUID("55555555-5555-5555-5555-555555555551"),
        brief_revision=1, quote_revision_snapshot={}, generated_at=datetime.now(UTC), stale=False,
        comparison_payload={"brief": {"quantity": 2000, "requirements": [
            {"id": CERT, "kind": "CERTIFICATION", "importance": "REQUIRED"},
            {"id": LEAD, "kind": "PRODUCTION_LEAD_TIME", "importance": "PREFERRED"}]},
            "suppliers": [supplier(A, QA, "4.50", 25, "MEETS", "CONFLICT", corrected=True),
                          supplier(B, QB, "3.90", 38, "DOES_NOT_MEET", "MEETS"), third]},
    )


def recorded_analysis(case: dict[str, Any]) -> TradeoffAnalysis:
    """Parse one version-controlled model-shaped result, including adversarial controls."""
    outputs = json.loads(OUTPUTS_PATH.read_text(encoding="utf-8"))
    return TradeoffAnalysis.model_validate(outputs[case["id"]])


def _assertion_clause(text: str, position: int) -> str:
    """Keep provenance cues on the assertion's side of clear clause boundaries."""
    start, end = 0, len(text)
    for boundary in PROVENANCE_CLAUSE.finditer(text):
        if boundary.end() <= position:
            start = boundary.end()
        elif boundary.start() >= position:
            end = boundary.start()
            break
    return text[start:end]


def _numeric_claims_grounded(point: Any, by_name: dict[str, dict[str, Any]],
                             requested_quantity: object) -> bool:
    """Check each bounded comparison number in its own supplier/field/source context."""
    text = point.text
    owners = list(re.finditer(r"\bSupplier ([ABC])\b", text, re.IGNORECASE))
    references = {(ref.quote_id, ref.field_key) for ref in point.quote_fields}
    for match in sorted((*PRICE.finditer(text), *QUANTITY.finditer(text)), key=lambda item: item.start()):
        owner = next((item.group(1).upper() for item in reversed(owners)
                      if item.start() < match.start()), None)
        quantity_label = match.group(1) if match.re is QUANTITY else None
        assertion = _assertion_clause(text, match.start()) if quantity_label is None else ""
        if quantity_label is not None and quantity_label.lower() == "requested quantity":
            if requested_quantity is None or str(requested_quantity) != match.group(2).replace(",", ""):
                return False
            continue
        if owner is None:
            return False
        supplier = by_name[owner]
        if quantity_label is not None:
            key = "quoted_quantity" if quantity_label.lower() == "quoted quantity" else "moq"
            value = match.group(2).replace(",", "")
        else:
            key = "shipping_cost" if "shipping" in assertion.lower() else "unit_price"
            value = match.group(1) or match.group(2)
        if (UUID(supplier["quote_id"]), key) not in references:
            return False
        field = next((item for item in supplier["quote_fields"]
                      if item["field_key"] == key), None)
        if field is None:
            return False
        if quantity_label is None:
            cues = {cue.group(1).lower() in {"pdf", "source", "evidence"}
                    for cue in PROVENANCE.finditer(assertion)}
            if len(cues) > 1:
                return False
            source_claim = True in cues
        else:
            source_claim = False
        if source_claim:
            sources = cast(list[dict[str, Any]], field["evidence"])
            if not any(str(source.get("value", source.get("evidence_value"))) == value
                       and UUID(source["id"]) in point.evidence_ids
                       for source in sources):
                return False
        elif str(field["current_value"]) != value:
            return False
    return True


def score_case(case: dict[str, Any], analysis: TradeoffAnalysis,
               snapshot: ComparisonSnapshotResult) -> bool:
    """Check each produced point against comparison states, values, and cited provenance."""
    try:
        validate_analysis(analysis, snapshot)
    except ValueError:
        return False
    payload = snapshot.comparison_payload
    if payload is None:
        return False
    suppliers = cast(list[dict[str, Any]], payload["suppliers"])
    brief = cast(dict[str, Any], payload["brief"])
    all_points = (analysis.supplier_summaries + analysis.key_tradeoffs
                  + analysis.important_unknowns + analysis.important_conflicts)
    by_name = {name: supplier for name, supplier in zip("ABC", suppliers, strict=True)}
    for point in all_points:
        names = re.findall(r"\bSupplier ([ABC])\b", point.text, re.IGNORECASE)
        names = [name.upper() for name in names]
        fields = {(ref.quote_id, ref.field_key) for ref in point.quote_fields}
        day_values = re.findall(r"\b(\d+)\s+days\b", point.text, re.IGNORECASE)
        if day_values and not names:
            return False
        if not _numeric_claims_grounded(point, by_name, brief.get("quantity")):
            return False
        if day_values:
            # The fixture's comparative sentence gives suppliers in price order,
            # then lead times in the same order after a colon.
            day_names = names[:len(day_values)] if len(day_values) > 1 else names[-1:]
            if len(day_names) != len(day_values):
                return False
            for name, days in zip(day_names, day_values, strict=True):
                supplier = by_name[name]
                if (UUID(supplier["quote_id"]), "production_lead_time") not in fields:
                    return False
                lead = next(item for item in supplier["quote_fields"]
                            if item["field_key"] == "production_lead_time")
                if str(lead["current_value"]) != days:
                    return False
        if re.search(r"\bPDF\b", point.text, re.IGNORECASE) and not point.evidence_ids:
            return False
        for name in re.findall(r"\bSupplier ([ABC])(?:'s)? shipping cost is unknown\b",
                               point.text, re.IGNORECASE):
            supplier = by_name[name.upper()]
            if not any(item["field_key"] == "shipping_cost" and item["state"] == "missing"
                       for item in supplier["completeness"]):
                return False
        cheaper = re.search(r"\bSupplier ([ABC]) is cheaper\b", point.text, re.IGNORECASE)
        if cheaper and len(names) >= 2:
            first, second = by_name[cheaper.group(1).upper()], by_name[names[1]]
            if float(first["quote_fields"][0]["current_value"]) >= float(
                second["quote_fields"][0]["current_value"]):
                return False
        if re.search(r"\blonger production lead time\b", point.text, re.IGNORECASE) and len(names) >= 2:
            first, second = by_name[names[0]], by_name[names[1]]
            if first["quote_fields"][1]["current_value"] <= second["quote_fields"][1]["current_value"]:
                return False
    focus = case["topic"]
    if focus in {"meaningful tradeoff"}:
        return any({UUID(A), UUID(B)} <= set(point.supplier_ids)
                   and {"unit_price", "production_lead_time"} <= {
                       ref.field_key for ref in point.quote_fields}
                   and re.search(r"\bcheaper\b", point.text, re.IGNORECASE)
                   and re.search(r"\blonger\b", point.text, re.IGNORECASE)
                   for point in analysis.key_tradeoffs)
    if focus in {"required failure", "omitted critical fact"}:
        return any(UUID(B) in point.supplier_ids and UUID(CERT) in point.requirement_ids
                   and re.search(r"\b(?:does not meet|fails|failure)\b", point.text, re.IGNORECASE)
                   for point in analysis.supplier_summaries + analysis.key_tradeoffs)
    if focus == "Unknown and Conflict":
        return (any(UUID(C) in point.supplier_ids and UUID(CERT) in point.requirement_ids
                    and re.search(r"\bunknown\b", point.text, re.IGNORECASE)
                    for point in analysis.important_unknowns)
                and any(UUID(A) in point.supplier_ids and UUID(LEAD) in point.requirement_ids
                        and re.search(r"\bconflict", point.text, re.IGNORECASE)
                        for point in analysis.important_conflicts))
    if focus in {"user correction", "unsupported source attribution"}:
        corrected = by_name["A"]["quote_fields"][0]
        source_value = corrected["evidence"][0]["evidence_value"]
        return any(UUID(A) in point.supplier_ids and UUID(PDF_PRICE) in point.evidence_ids
                   and str(corrected["current_value"]) in point.text
                   and str(source_value) in point.text
                   and re.search(r"\b(?:confirmed|corrected)\b", point.text, re.IGNORECASE)
                   and re.search(r"\bPDF\b", point.text, re.IGNORECASE)
                   for point in all_points)
    if focus in {"incomplete evidence", "unsupported claim"}:
        return any(UUID(C) in point.supplier_ids
                   and any(ref.quote_id == UUID(QC) and ref.field_key == "shipping_cost"
                           for ref in point.quote_fields)
                   and re.search(r"\b(?:unknown|missing)\b", point.text, re.IGNORECASE)
                   for point in all_points)
    raise ValueError(f"Unknown eval topic: {focus}")
