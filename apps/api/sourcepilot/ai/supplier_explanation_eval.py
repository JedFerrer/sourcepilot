"""Version-controlled offline groundedness cases for M2-U6."""

from __future__ import annotations

import json
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

CASES_PATH = Path(__file__).resolve().parents[2] / "evals" / "supplier_explanation" / "cases.json"


def load_cases() -> list[dict[str, Any]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def score_case(case: dict[str, Any]) -> bool:
    supplier_id = UUID("11111111-1111-1111-1111-111111111111")
    snapshot = SupplierSnapshot(
        supplier_id=supplier_id, name="Synthetic supplier", country="Demo",
        description="Fixture", capabilities=[], general_moq=None,
        general_lead_time_days=None, indicative_price_amount=None,
        indicative_price_currency=None,
        evaluation_availability=EvaluationAvailability.CURRENT,
        evaluated_against_brief_revision=1, current_brief_revision=1,
        evaluations=[SupplierRequirementFinding.model_validate(value) for value in case["findings"]],
    )
    try:
        explanation = ModelSupplierExplanation.model_validate(case["output"])
        _validate_explanation(
            explanation,
            supplier_id=supplier_id, snapshot=snapshot,
            fetched_evidence_ids={UUID(value) for value in case["fetched_evidence_ids"]},
        )
        _render_explanation(explanation, snapshot)
    except ValueError:
        return False
    return True
