"""Finite factual wording for combined advice. No model text is rendered."""

from __future__ import annotations

import re
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from sourcepilot.comparison.advice_facts import (
    BASELINE_FIELDS,
    AdviceCatalogue,
    AdviceFact,
    numeric_value,
    valid_relationship,
    valid_verification,
)
from sourcepilot.comparison.evaluation import _day_bounds
from sourcepilot.quotes.domain import QUOTE_MONEY_FIELDS

REQUIREMENT_LABELS = {
    "MATERIAL": "material", "CERTIFICATION": "certification", "CAPABILITY": "capability",
    "MOQ": "MOQ", "QUANTITY": "quantity", "UNIT_PRICE": "unit price",
    "PRODUCTION_LEAD_TIME": "production lead time", "DELIVERY": "delivery",
}


def _point(text: str, facts: Sequence[AdviceFact]) -> dict[str, Any]:
    return {
        "text": text,
        "supplier_ids": list(dict.fromkeys(f.supplier_id for f in facts)),
        "requirement_ids": list(dict.fromkeys(f.requirement_id for f in facts if f.requirement_id)),
        "quote_fields": [{"quote_id": qid, "field_key": field} for qid, field in
                         dict.fromkeys((f.quote_id, f.field_key) for f in facts if f.quote_id)],
        "evidence_ids": list(dict.fromkeys(e for f in facts for e in f.evidence_ids)),
    }


def render_fact(catalogue: AdviceCatalogue, fact: AdviceFact) -> dict[str, Any]:
    name = fact.supplier_name
    if fact.requirement_id:
        requirement = fact.source["requirement"]
        kind = requirement["kind"]
        count = sum(r["kind"] == kind for r in catalogue.payload["brief"]["requirements"])
        label = REQUIREMENT_LABELS.get(kind, "requirement") if count == 1 else "requirement"
        return _point(f"{name} {label} is {fact.state}.", [fact])
    label = str(fact.field_key).replace("_", " ")
    if fact.state in {"UNKNOWN", "CONFLICT"}:
        # A saved correction remains inspectable even when the composite price
        # cannot be resolved. This display-only branch does not make it numeric
        # evidence for relationships or an eligible suggestion reason.
        currency = catalogue.quote(fact, "currency")
        if (fact.state == "CONFLICT" and fact.field_key == "unit_price"
                and fact.source.get("origin") == "USER_CORRECTED"
                and currency and currency.state == "CONFLICT"
                and not isinstance(fact.value, bool)):
            try:
                amount = Decimal(str(fact.value))
            except InvalidOperation:
                amount = Decimal("NaN")
            if amount.is_finite() and amount >= 0:
                return _point(
                    f"{name} {label} is CONFLICT. "
                    f"Current user-corrected amount: {amount:f} (no currency assigned). "
                    f"{name} currency is CONFLICT. Original extraction is provenance only; "
                    "it does not verify the correction.", [fact, currency],
                )
        return _point(f"{name} {label} is {fact.state}.", [fact])
    references = [fact]
    number = numeric_value(fact)
    if fact.field_key in QUOTE_MONEY_FIELDS and number is not None:
        currency = catalogue.quote(fact, "currency")
        if currency:
            references.append(currency)
        if (currency and currency.state == "KNOWN" and isinstance(currency.value, str)
                and re.fullmatch(r"[A-Z]{3}", currency.value)):
            value = f"{currency.value} {number:f}"
        else:
            value = f"{number:f} (currency requires verification)"
    elif fact.field_key in {"quoted_quantity", "moq"} and number is not None:
        value = f"{number:f}"
    elif fact.field_key in {"production_lead_time", "total_lead_time", "shipping_time"} and (
        bounds := _day_bounds(fact.value)
    ):
        value = f"{bounds[0]} days" if bounds[0] == bounds[1] else f"{bounds[0]}–{bounds[1]} days"
    elif (fact.field_key == "currency" and isinstance(fact.value, str)
          and re.fullmatch(r"[A-Z]{3}", fact.value)):
        value = fact.value
    else:
        # Arbitrary saved prose stays inspectable in SourceDetails, never in a
        # state-sensitive generated sentence. Do not manufacture a known state.
        if fact.state == "KNOWN":
            return _point(f"{name} {label} is KNOWN.", references)
        return _point("Review the cited saved value and its source details.", references)
    origin = fact.source.get("origin")
    provenance = (" Current user-corrected value; original extraction is provenance."
                  if origin == "USER_CORRECTED" else " Current user-entered quote value."
                  if origin == "USER_ENTERED" else " Current confirmed quote value.")
    return _point(f"{name} {label}: {value}.{provenance}", references)


def _expected_identity(value: Any) -> str:
    """Readable requirement identity without dropping zero or false values."""
    if value is None:
        return "not specified"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, dict):
        return "; ".join(
            f"{key.replace('_', ' ')}: "
            + (item.lower().replace("_", " ")
               if key in {"capability_key", "subject"} and isinstance(item, str)
               else _expected_identity(item))
            for key, item in value.items()
        )
    if isinstance(value, list):
        return ", ".join(_expected_identity(item) for item in value)
    return str(value)


def _render_verification(
    catalogue: AdviceCatalogue, action: str, fact: AdviceFact,
) -> dict[str, Any]:
    if not valid_verification(fact, action):
        raise ValueError("Unvalidated verification reached advice renderer.")
    if fact.requirement_id:
        requirement = fact.source["requirement"]
        label = REQUIREMENT_LABELS.get(
            requirement["kind"], requirement["kind"].lower().replace("_", " "),
        )
        target = (f"{requirement['importance'].lower()} {label} requirement "
                  f"(expected {_expected_identity(requirement['expected_value'])})")
    else:
        target = str(fact.field_key).replace("_", " ")
    name = fact.supplier_name
    text = {
        "CONFIRM_MISSING": (
            f"Ask {name} to provide missing information for {target} before choosing."
        ),
        "RESOLVE_CONFLICT": (
            f"Reconcile the source records for {name}'s {target} before proceeding."
        ),
        "VERIFY_QUOTE": (
            f"Verify {name}'s current quoted {target} with the supplier before choosing."
        ),
        "CONFIRM_DELIVERY": (
            f"Ask {name} to confirm {target} with an explicit delivery commitment "
            "covering production and transit."
        ),
    }[action]
    if action == "RESOLVE_CONFLICT":
        point = render_fact(catalogue, fact)
        point["text"] = f"{point['text']} {text}"
        return point
    if action == "VERIFY_QUOTE":
        # Reuse current-value/currency/provenance rendering and its exact references.
        point = render_fact(catalogue, fact)
        point["text"] = f"{text} {point['text']}"
        return point
    return _point(text, [fact])


def render_advice(
    catalogue: AdviceCatalogue, *, highlights: Sequence[str] = (),
    tradeoffs: Sequence[tuple[str, list[str]]] = (),
    verification_actions: Sequence[tuple[str, str]] = (),
    suggestion_id: str | None = None, reason_fact_ids: Sequence[str] = (),
    null_reason: str | None = "NO_CLEAR_PREFERENCE",
) -> dict[str, Any]:
    """Assemble public content; callers validate typed selections before entry."""
    analysis: dict[str, list[dict[str, Any]]] = {key: [] for key in (
        "supplier_summaries", "key_tradeoffs", "important_unknowns", "important_conflicts",
    )}
    included = [f.id for f in catalogue.facts.values()
                if f.requirement_id or f.field_key in BASELINE_FIELDS or f.id in highlights]
    ordering = list(dict.fromkeys([*highlights, *included]))
    for key in ordering:
        fact = catalogue.facts[key]
        section = ("important_unknowns" if fact.state == "UNKNOWN" else "important_conflicts"
                   if fact.state == "CONFLICT" else "key_tradeoffs" if fact.state == "DOES_NOT_MEET"
                   else "supplier_summaries")
        analysis[section].append(render_fact(catalogue, fact))
    for kind, ids in tradeoffs:
        if not valid_relationship(catalogue, kind, ids):
            raise ValueError("Unvalidated tradeoff reached advice renderer.")
        facts = [catalogue.facts[key] for key in ids]
        if kind == "SAME_REQUIREMENT":
            # Each sentence has an explicit supplier and the same requirement.
            # Never combine different requirements into an ambiguous state list.
            text = " ".join(render_fact(catalogue, fact)["text"] for fact in facts)
            importance = str(facts[0].importance or "INFORMATIONAL").lower()
            text += f" Consider this {importance} criterion alongside the other quoted terms."
        elif kind == "SAME_QUOTE_FIELD":
            text = " ".join(render_fact(catalogue, fact)["text"] for fact in facts)
        else:
            a, _, b, _ = facts
            ap, bp = numeric_value(a), numeric_value(b)
            assert ap is not None and bp is not None
            higher, lower = (a, b) if ap > bp else (b, a)
            text = (f"{higher.supplier_name} lists a higher unit price and a shorter production "
                    f"lead time than {lower.supplier_name}. Production time is not a delivery commitment.")
        # Comparability depends on each quote's currency and quantity. Include
        # those exact supporting references, not only the operands being compared.
        for fact in list(facts):
            if fact.field_key in QUOTE_MONEY_FIELDS:
                facts.extend(dependency for field in ("currency", "quoted_quantity")
                             if (dependency := catalogue.quote(fact, field)) is not None)
        analysis["key_tradeoffs"].append(_point(text, facts))
    for action, key in verification_actions:
        fact = catalogue.facts[key]
        analysis["key_tradeoffs"].append(_render_verification(catalogue, action, fact))
    # Price comparability warnings are application-owned and cannot be suppressed.
    currencies = [f for f in catalogue.facts.values() if f.field_key == "currency"]
    quantities = [f for f in catalogue.facts.values() if f.field_key == "quoted_quantity"]
    if currencies and (any(f.state != "KNOWN" for f in currencies)
                       or len({str(f.value) for f in currencies}) > 1):
        analysis["key_tradeoffs"].append(_point(
                "Do not directly compare prices: quote currencies differ or require verification. "
                "No currency conversion has been performed.", currencies))
    if quantities and (any(numeric_value(f) is None for f in quantities)
                       or len({numeric_value(f) for f in quantities}) > 1):
        analysis["key_tradeoffs"].append(_point(
                "Do not treat these prices as equivalent quantities; verify the cited quantities.", quantities))
    delivery = [f for f in catalogue.facts.values()
                if f.field_key in {"delivery_date", "total_lead_time"} and f.state != "KNOWN"]
    if delivery:
        analysis["key_tradeoffs"].append(_point(
            "Production lead time alone does not establish delivery timing. "
            "Obtain an explicit delivery commitment before deciding.", delivery))
    suggestion: dict[str, Any] = {
        "supplier_id": suggestion_id, "supporting_reasons": [], "tradeoffs": [],
        "uncertainties": [], "evidence_ids": [],
    }
    if suggestion_id is None:
        explanation_ids = ([key for _, key in verification_actions]
                           if null_reason == "VERIFY_BEFORE_CHOOSING" else list(highlights))
        facts = [catalogue.facts[key] for key in dict.fromkeys(explanation_ids)] or list(catalogue.facts.values())[:1]
        text = ("No supplier selected; verify the cited information before choosing."
                if null_reason == "VERIFY_BEFORE_CHOOSING"
                else "No single supplier is suggested; review the cited tradeoffs before choosing.")
        suggestion["uncertainties"].append(_point(text, facts))
    else:
        suggestion["supporting_reasons"] = [render_fact(catalogue, catalogue.facts[key])
                                             for key in reason_fact_ids]
        for fact in catalogue.facts.values():
            if fact.supplier_id != suggestion_id:
                continue
            if fact.state == "DOES_NOT_MEET" and fact.requirement_id:
                suggestion["tradeoffs"].append(render_fact(catalogue, fact))
            elif fact.state in {"UNKNOWN", "CONFLICT"} and (
                fact.requirement_id or fact.field_key in BASELINE_FIELDS
            ):
                suggestion["uncertainties"].append(render_fact(catalogue, fact))
        suggestion["tradeoffs"].extend(p for p in analysis["key_tradeoffs"]
                                       if suggestion_id in p["supplier_ids"] and p not in suggestion["tradeoffs"])
    suggestion["evidence_ids"] = list(dict.fromkeys(
        e for section in ("supporting_reasons", "tradeoffs", "uncertainties")
        for point in suggestion[section] for e in point["evidence_ids"]
    ))
    return {"analysis": analysis, "suggestion": suggestion}
