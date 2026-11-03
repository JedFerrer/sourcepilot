"""Version-controlled offline contract and bounded narrative checks for M2-U6."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any
from uuid import UUID

from sourcepilot.ai.analyst_tools import (
    EvaluationAvailability,
    SupplierRequirementFinding,
    SupplierSnapshot,
)
from sourcepilot.ai.supplier_explanation import (
    ModelSupplierExplanation,
    _render_explanation,
    _validate_explanation,
)
from sourcepilot.briefs.domain import validate_requirement_expected_value

CASES_PATH = Path(__file__).resolve().parents[2] / "evals" / "supplier_explanation" / "cases.json"
# Bounded documented equivalences: these words denote the same making action.
# Action remains substantive; a material finding alone does not prove it.
MAKING_ALIASES = {
    "make", "makes", "making", "manufacture", "manufactures", "manufacturing",
    "fabricate", "fabricates", "fabricating", "produce", "produces", "producing",
    "build", "builds", "building",
}
STATUS_TERMS = {"MEETS": "meets", "DOES_NOT_MEET": "notmeet",
                "UNKNOWN": "unknown", "CONFLICT": "conflict"}
NEGATED_TERMS = {"not", "notmeet", "cannot", "no"}
BOILERPLATE = {
    "a", "an", "and", "are", "can", "catalog", "company", "factory", "firm",
    "for", "has", "have", "in", "is", "its", "of", "our", "supplier", "the",
    "their", "these", "this", "those", "to", "with", "s", "product", "products",
    "capability", "capabilities", "capable", "supports", "support", "offers",
    "offer", "provides", "provide", "supply", "supplies", "facility", "plant",
    "requirement", "requirements", "does",
    # Supplier actors add no capability: the action and object still need support.
    "workshop", "workshops", "manufacturer", "manufacturers",
}


def _substantive_terms(text: str) -> set[str]:
    terms = set()
    text = re.sub(r"\bdoes\s+not\s+meet\b", "notmeet", text, flags=re.IGNORECASE)
    for word in re.findall(r"[a-z0-9]+", text.casefold()):
        if word in BOILERPLATE:
            continue
        if word in MAKING_ALIASES:
            terms.add("make")
        elif word in {"meets", "satisfies"}:
            terms.add("meets")
        elif word in {"fails", "failure"}:
            terms.add("notmeet")
        elif word in {"conflicts", "conflicting"}:
            terms.add("conflict")
        elif word in {"unverified", "uncertain"}:
            terms.add("unknown")
        else:
            terms.add(word[:-1] if word.endswith("s") and len(word) > 4 else word)
    return terms


def _fact_texts(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [text for item in value.values() for text in _fact_texts(item)]
    if isinstance(value, list):
        return [text for item in value for text in _fact_texts(item)]
    return [str(value)] if value is not None else []


def _claim_supported(case: dict[str, Any], text: str, evidence_ids: list[str]) -> bool:
    """Bounded lexical support probe; a match is not semantic entailment."""
    if not text.strip():
        return True  # A requirement-bound point has no model-authored narrative.
    claim = _substantive_terms(text)
    if not claim:
        return False
    # A generic review instruction asserts no supplier property.
    if claim <= {"indicative", "pricing", "need", "review"}:
        return True
    facts: list[tuple[str, str | None]] = []
    for finding in case["findings"]:
        for value in _fact_texts(finding["expected_value"]):
            status = STATUS_TERMS[finding["status"]]
            required = status if finding["status"] != "MEETS" else None
            facts.append((f"{finding['kind']} {value} {status}", required))
            if finding["status"] == "MEETS":
                facts.append((value, None))
    facts.extend((value, None) for value in _fact_texts(case.get("supplier_facts", {})))
    available = set(case["fetched_evidence_ids"]) & set(evidence_ids)
    facts.extend((case.get("evidence_texts", {}).get(evidence_id, ""), None)
                 for evidence_id in available)
    for fact, required in facts:
        terms = _substantive_terms(fact)
        if required is not None and required not in claim:
            continue
        if (terms & NEGATED_TERMS) - claim:
            continue
        if claim <= terms:
            return True
    return False


ACTION_CLAIM = re.compile(
    r"\b(?:mak(?:e|es|ing)|manufactur\w*|fabricat\w*|produc\w*|build\w*|"
    r"design\w*|assembl\w*|mold\w*|develop\w*|process\w*|operat\w*|"
    r"specializ\w*|suppl\w*|provid\w*|support\w*|capabilit\w*)\b",
    re.IGNORECASE,
)


def free_text_signals(case: dict[str, Any], output: dict[str, Any]) -> list[str]:
    """Flag recognizable unsupported capability claims, not arbitrary prose."""
    signals = []
    for section in ("strengths", "required_failures", "preferred_findings",
                    "unknowns", "conflicts", "concerns"):
        for index, point in enumerate(output[section]):
            text = point.get("text") or ""
            if (point["requirement_id"] is None and ACTION_CLAIM.search(text)
                    and not _claim_supported(case, text, point["evidence_ids"])):
                signals.append(f"{section}[{index}]: {text}")
    return signals


def load_cases() -> list[dict[str, Any]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def score_case(case: dict[str, Any], *, check_narrative: bool = True) -> bool:
    if check_narrative and free_text_signals(case, case["output"]):
        return False
    supplier_id = UUID("11111111-1111-1111-1111-111111111111")
    snapshot = SupplierSnapshot(
        supplier_id=supplier_id,
        name="Synthetic supplier",
        country="Demo",
        description="Fixture",
        capabilities=[],
        general_moq=None,
        general_lead_time_days=None,
        indicative_price_amount=None,
        indicative_price_currency=None,
        evaluation_availability=EvaluationAvailability.CURRENT,
        evaluated_against_brief_revision=1,
        current_brief_revision=1,
        evaluations=[
            SupplierRequirementFinding.model_validate(value) for value in case["findings"]
        ],
    )
    try:
        explanation = ModelSupplierExplanation.model_validate(case["output"])
        _validate_explanation(
            explanation,
            supplier_id=supplier_id,
            snapshot=snapshot,
            fetched_evidence_ids={UUID(value) for value in case["fetched_evidence_ids"]},
        )
        _render_explanation(explanation, snapshot)
    except ValueError:
        return False
    return True


def score_rendered(case: dict[str, Any], output: dict[str, Any],
                   *, check_narrative: bool = True) -> bool:
    """Validate actual rendered results separately from raw model contracts.

    Requirement text is application-rendered; compare it exactly before removing
    it for the raw-contract validator. Evidence-only concern text stays untouched.
    """
    raw = deepcopy(output)
    findings = {item["requirement_id"]: item for item in case["findings"]}
    for section in (
        "strengths",
        "required_failures",
        "preferred_findings",
        "unknowns",
        "conflicts",
        "concerns",
    ):
        for point in raw[section]:
            if (check_narrative and point["requirement_id"] is None
                    and ACTION_CLAIM.search(point["text"] or "")
                    and not _claim_supported(case, point["text"] or "", point["evidence_ids"])):
                return False
            if point["requirement_id"] is not None:
                finding = findings.get(point["requirement_id"])
                if finding is None:
                    return False
                normalized = validate_requirement_expected_value(
                    finding["kind"], finding["expected_value"]
                )
                expected = ", ".join(str(value) for value in normalized.values())
                label = finding["kind"].replace("_", " ").title()
                state = finding["status"].replace("_", " ").title()
                text = f"{label} ({expected}): {state}." if expected else f"{label}: {state}."
                if point["text"] != text:
                    return False
                point["text"] = None
    return score_case({**case, "output": raw}, check_narrative=check_narrative)
