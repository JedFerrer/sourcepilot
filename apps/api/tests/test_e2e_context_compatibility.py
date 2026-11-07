"""The browser fake consumes projected context; real validators use the original."""

import json
from copy import deepcopy

import pytest

from sourcepilot.ai.advice_selection import AdviceSelectionTask
from sourcepilot.ai.comparison_advice import ComparisonAdvice, validate_advice
from sourcepilot.ai.comparison_context import comparison_context
from tests.e2e_support.model import comparison_output, comparison_selection
from tests.test_comparison_context import context_fixture


@pytest.mark.parametrize("suggest", [False, True])
def test_browser_fixture_accepts_projected_completeness(suggest: bool) -> None:
    snapshot = context_fixture()
    before = deepcopy(snapshot)
    projected = comparison_context(snapshot)["comparison_payload"]
    assert all("completeness" not in row for row in projected["suppliers"])
    first = comparison_output(projected, suggest=suggest)
    assert first == comparison_output(projected, suggest=suggest)
    assert (first["suggestion"]["supplier_id"] is not None) is suggest
    validate_advice(ComparisonAdvice.model_validate(first), snapshot)
    expected = {(row["quote_id"], field["field_key"])
                for row in projected["suppliers"] for field in row["quote_fields"]
                if field.get("completeness", {}).get("state") in {"missing", "conflicting"}}
    actual = {(ref["quote_id"], ref["field_key"])
              for section in ("important_unknowns", "important_conflicts")
              for point in first["analysis"][section] for ref in point["quote_fields"]}
    assert actual == expected
    assert snapshot == before


@pytest.mark.parametrize("suggest", [False, True])
@pytest.mark.parametrize("scenario", ["manual", "missing", "pdf"])
def test_browser_selection_fixture_passes_combined_assembly(suggest: bool, scenario: str) -> None:
    snapshot = context_fixture(scenario)
    task = AdviceSelectionTask(snapshot)
    output = task.accept(json.dumps(comparison_selection(task.initial, suggest=suggest)))
    validate_advice(ComparisonAdvice.model_validate(output), snapshot)
    assert (output["suggestion"]["supplier_id"] is not None) is suggest
