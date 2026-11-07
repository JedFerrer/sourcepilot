"""Run-local presentation of comparison facts; never an authorization/validation source."""

import json
from copy import deepcopy
from typing import Any, cast

from sourcepilot.ai.analyst_tools import ComparisonSnapshotResult, QuoteEvidenceResult
from sourcepilot.quotes.domain import QUOTE_MONEY_FIELDS

CONTEXT_INSTRUCTIONS = """\nModel context layout: each quote_fields entry keeps its exact field_key and nests
its supplied completeness record. Entries with completeness only have no saved
value; do not invent one. The enclosing supplier supplies the exact supplier_id
and quote_id for every field. Monetary entries include currency_context copied
only from that same quote: field_key="currency", value and completeness state.
The full currency field retains its origin, uncertainty and provenance; follow
that exact quote/field reference for these details. Cite both fields for monetary
currency claims.
Resolved facts retain selected in full; project_alternatives and general_alternatives
contain all remaining source facts except exact copies of selected. Selected's
context still distinguishes PROJECT_QUOTE from GENERAL_SUPPLIER. No state was
recomputed. Monetary evidence replies add comparison_context from the bound
snapshot, including the full currency_field, separately from the requested field's
PDF evidence. Its currency record is comparison data, not evidence that the amount's PDF verifies currency.
"""


def context_json(value: object) -> str:
    """Stable compact JSON for model input, tool replies and the input hash."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _fields(supplier: dict[str, Any]) -> list[dict[str, Any]]:
    fields = deepcopy(supplier["quote_fields"])
    by_key = {field["field_key"]: field for field in fields}
    for completeness in supplier.get("completeness", []):
        key = completeness["field_key"]
        if key not in by_key:
            by_key[key] = {"field_key": key}
            fields.append(by_key[key])
        by_key[key]["completeness"] = {
            name: deepcopy(value) for name, value in completeness.items() if name != "field_key"
        }
    currency = by_key.get("currency")
    for field in fields:
        if field["field_key"] in QUOTE_MONEY_FIELDS and currency is not None:
            # Local value/state plus the exact reference to the full currency field.
            # Do not repeat its PDF provenance for every monetary amount.
            currency_context = {"quote_id": supplier["quote_id"], "field_key": "currency"}
            if "current_value" in currency:
                currency_context["current_value"] = deepcopy(currency["current_value"])
            if "completeness" in currency:
                currency_context["completeness"] = {"state": currency["completeness"]["state"]}
            field["currency_context"] = currency_context
    return fields


def comparison_context(snapshot: ComparisonSnapshotResult) -> dict[str, Any]:
    """Preserve facts while joining field completeness and removing exact duplicates."""
    payload = deepcopy(cast(dict[str, Any], snapshot.comparison_payload))
    if payload is None:
        raise ValueError("Comparison context requires a current payload.")
    for supplier in payload["suppliers"]:
        supplier["quote_fields"] = _fields(supplier)
        supplier.pop("completeness", None)
        for resolution in supplier.get("resolved_facts", {}).values():
            # SourceResolution stores selected in full and repeats it in one of
            # these collections. Keep selected intact, including every attribution.
            for collection in ("project_facts", "general_facts"):
                if collection in resolution:
                    resolution[collection.replace("facts", "alternatives")] = [
                        fact for fact in resolution.pop(collection)
                        if fact != resolution.get("selected")
                    ]
    return {
        "snapshot_id": str(snapshot.snapshot_id),
        "brief_revision": snapshot.brief_revision,
        "quote_revision_snapshot": deepcopy(snapshot.quote_revision_snapshot),
        "comparison_payload": payload,
    }


def quote_comparison_context(
    snapshot: ComparisonSnapshotResult, evidence: QuoteEvidenceResult,
) -> dict[str, Any]:
    """Keep bound snapshot facts separate from the field-specific evidence result."""
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    supplier = next(row for row in payload["suppliers"]
                    if row["quote_id"] == str(evidence.quote_id)
                    and row["supplier_id"] == str(evidence.supplier_id))
    fields = _fields(supplier)
    field = next(item for item in fields if item["field_key"] == evidence.field_key)
    currency = next((item for item in fields if item["field_key"] == "currency"), None)
    return {"snapshot_id": str(snapshot.snapshot_id), "supplier_id": supplier["supplier_id"],
            "quote_id": supplier["quote_id"], "quote_revision": supplier.get("quote_revision"),
            "field": field, "currency_field": currency}
