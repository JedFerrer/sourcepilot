"""Immutable run-local facts for combined advice; no persistence or model access."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any

from sourcepilot.comparison.evaluation import _day_bounds
from sourcepilot.quotes.domain import QUOTE_MONEY_FIELDS

BASELINE_FIELDS = (
    "unit_price", "quoted_quantity", "moq", "production_lead_time", "shipping_cost",
    "tooling_cost", "currency", "total_lead_time", "delivery_date",
)
PAIR_FIELDS = frozenset({"unit_price", "quoted_quantity", "moq", "production_lead_time",
                         "shipping_cost", "tooling_cost"})


@dataclass(frozen=True)
class AdviceFact:
    id: str
    supplier_id: str
    supplier_name: str
    requirement_id: str | None
    quote_id: str | None
    field_key: str | None
    state: str
    importance: str | None
    evidence_ids: tuple[str, ...]
    source_json: str

    @property
    def source(self) -> dict[str, Any]:
        """Return an isolated view; neither callers nor repair can mutate facts."""
        return json.loads(self.source_json)

    @property
    def value(self) -> Any:
        return self.source.get("current_value")


@dataclass(frozen=True)
class AdviceCatalogue:
    snapshot_id: str
    facts: Mapping[str, AdviceFact]
    supplier_ids: tuple[str, ...]
    payload_json: str

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self.payload_json)

    def quote(self, fact: AdviceFact, field: str) -> AdviceFact | None:
        return self.facts.get(f"Q:{fact.quote_id}:{field}")


def build_catalogue(snapshot_id: str, payload: dict[str, Any]) -> AdviceCatalogue:
    facts: dict[str, AdviceFact] = {}
    requirements = {r["id"]: r for r in payload["brief"]["requirements"]}
    owners: list[str] = []
    for supplier in payload["suppliers"]:
        sid, name, qid = (supplier["supplier_id"], supplier["supplier_name"],
                          supplier["quote_id"])
        if sid in owners:
            raise ValueError("Duplicate supplier in advice snapshot.")
        owners.append(sid)
        for result in supplier["evaluation"]["results"]:
            rid = result["requirement_id"]
            if rid is None:
                continue
            key = f"R:{sid}:{rid}"
            if key in facts or rid not in requirements:
                raise ValueError("Invalid requirement identity in advice snapshot.")
            facts[key] = AdviceFact(
                key, sid, name, rid, None, None, result["status"],
                requirements[rid]["importance"], tuple(result.get("evidence_ids", [])),
                json.dumps({"requirement": requirements[rid], "evaluation": result}),
            )
        fields = {f["field_key"]: f for f in supplier["quote_fields"]}
        completeness = {f["field_key"]: f for f in supplier["completeness"]}
        for field in sorted(fields.keys() | completeness.keys()):
            key = f"Q:{qid}:{field}"
            if key in facts:
                raise ValueError("Duplicate quote ownership in advice snapshot.")
            source = {**fields.get(field, {"field_key": field}),
                      "completeness": completeness.get(field),
                      "quote_revision": supplier.get("quote_revision")}
            state = {"known": "KNOWN", "missing": "UNKNOWN", "conflicting": "CONFLICT"}.get(
                completeness.get(field, {}).get("state"), "UNASSESSED")
            facts[key] = AdviceFact(
                key, sid, name, None, qid, field, state, None,
                tuple(e["id"] for e in source.get("evidence", [])), json.dumps(source),
            )
    return AdviceCatalogue(snapshot_id, MappingProxyType(facts), tuple(owners),
                           json.dumps(payload))


def catalogue_index(context: dict[str, Any]) -> dict[str, dict[str, int]]:
    """References into the lossless projection, never duplicate fact/evidence text."""
    index = {}
    for si, supplier in enumerate(context["comparison_payload"]["suppliers"]):
        for ri, result in enumerate(supplier["evaluation"]["results"]):
            if result["requirement_id"] is not None:
                key = f"R:{supplier['supplier_id']}:{result['requirement_id']}"
                index[key] = {"supplier_index": si, "result_index": ri}
        for fi, field in enumerate(supplier["quote_fields"]):
            index[f"Q:{supplier['quote_id']}:{field['field_key']}"] = {
                "supplier_index": si, "quote_field_index": fi,
            }
    return index


def numeric_value(fact: AdviceFact) -> Decimal | None:
    if fact.state != "KNOWN" or isinstance(fact.value, bool):
        return None
    try:
        value = Decimal(str(fact.value))
    except (InvalidOperation, ValueError):
        return None
    return value if value.is_finite() and value >= 0 else None


def comparable_money(catalogue: AdviceCatalogue, a: AdviceFact, b: AdviceFact) -> bool:
    ca, cb = catalogue.quote(a, "currency"), catalogue.quote(b, "currency")
    qa, qb = catalogue.quote(a, "quoted_quantity"), catalogue.quote(b, "quoted_quantity")
    return bool(ca and cb and qa and qb and ca.state == cb.state == "KNOWN"
                and isinstance(ca.value, str) and ca.value and ca.value == cb.value
                and numeric_value(qa) is not None and numeric_value(qa) == numeric_value(qb))


def valid_relationship(catalogue: AdviceCatalogue, kind: str, ids: list[str]) -> bool:
    if len(set(ids)) != len(ids) or any(key not in catalogue.facts for key in ids):
        return False
    facts = [catalogue.facts[key] for key in ids]
    if kind == "SAME_REQUIREMENT" and len(facts) == 2:
        a, b = facts
        return bool(a.requirement_id and a.requirement_id == b.requirement_id
                    and a.supplier_id != b.supplier_id)
    if kind == "SAME_QUOTE_FIELD" and len(facts) == 2:
        a, b = facts
        if (a.supplier_id == b.supplier_id or a.field_key != b.field_key
                or a.field_key not in PAIR_FIELDS or a.state != "KNOWN" or b.state != "KNOWN"):
            return False
        if a.field_key == "production_lead_time":
            return _day_bounds(a.value) is not None and _day_bounds(b.value) is not None
        return (numeric_value(a) is not None and numeric_value(b) is not None
                and (a.field_key not in QUOTE_MONEY_FIELDS or comparable_money(catalogue, a, b)))
    if kind == "PRICE_AND_PRODUCTION" and len(facts) == 4:
        a, at, b, bt = facts
        if (a.field_key != "unit_price" or b.field_key != "unit_price"
                or at.field_key != "production_lead_time" or bt.field_key != "production_lead_time"
                or a.supplier_id != at.supplier_id or b.supplier_id != bt.supplier_id
                or a.supplier_id == b.supplier_id or at.state != "KNOWN" or bt.state != "KNOWN"
                or not comparable_money(catalogue, a, b)):
            return False
        ap, bp, ad, bd = numeric_value(a), numeric_value(b), _day_bounds(at.value), _day_bounds(bt.value)
        return bool(ap is not None and bp is not None and ad and bd
                    and ((ap > bp and ad[1] < bd[0]) or (bp > ap and bd[1] < ad[0])))
    return False


def valid_verification(fact: AdviceFact, action: str) -> bool:
    return ((action == "CONFIRM_MISSING" and fact.state == "UNKNOWN")
            or (action == "RESOLVE_CONFLICT" and fact.state == "CONFLICT")
            or (action == "VERIFY_QUOTE" and fact.quote_id is not None and fact.state == "KNOWN")
            or (action == "CONFIRM_DELIVERY" and fact.state == "UNKNOWN"
                and fact.field_key in {"delivery_date", "total_lead_time"}))
