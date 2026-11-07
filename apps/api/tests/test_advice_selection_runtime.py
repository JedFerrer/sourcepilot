"""Exercise combined selection integration without provider or database access."""

import json
from copy import deepcopy
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from sourcepilot.ai import comparison_advice as advice
from sourcepilot.ai import tradeoff_analysis as runtime
from sourcepilot.ai.advice_selection import AdviceSelectionTask, selection_context
from sourcepilot.ai.client import AnalystModelInvocation
from sourcepilot.ai.comparison_context import context_json
from sourcepilot.ai.structured import structured_input_hash
from sourcepilot.persistence.models import AIRun
from tests.test_advice_facts import retained_snapshot
from tests.test_advice_selection import valid_selection


@pytest.mark.parametrize("mode", ["direct", "tool-repair", "bad-repair", "limit", "stale", "assembly"])
def test_combined_selection_runtime(monkeypatch, mode):
    snapshot = retained_snapshot()
    before = snapshot.model_dump_json()
    task = AdviceSelectionTask(snapshot)
    good = valid_selection(task)
    bad = deepcopy(good)
    bad["tradeoffs"] = [{"relation": "SAME_REQUIREMENT", "fact_ids": ["foreign", "foreign2"]}]
    requests: list[dict[str, Any]] = []
    stored: list[Any] = []

    class MemorySession:
        def add(self, item):
            if isinstance(item, AIRun):
                item.id = uuid4()
            stored.append(item)

        def commit(self):
            pass

    class Model:
        model = "provider-free-selection"

        def invoke_with_tools(self, **kwargs):
            requests.append(deepcopy(kwargs))
            if mode == "tool-repair" and len(requests) == 1:
                return AnalystModelInvocation("", ({"type": "function_call", "name": "get_comparison_snapshot",
                    "call_id": "snapshot", "arguments": "{}"},), 1, 1)
            if kwargs["schema_name"] == "SelectionRepairV1":
                output = {"version": "comparison-selection-repair-v1", "snapshot_id": str(snapshot.snapshot_id),
                          "replacements": [{"slot_id": "tradeoffs[0]", "op": "remove", "value": None}]}
                if mode == "bad-repair":
                    output["replacements"][0]["slot_id"] = "highlights[0]"
            else:
                assert kwargs["schema_name"] == "ComparisonSelectionV1"
                output = bad if mode in {"tool-repair", "bad-repair", "limit"} else good
            return AnalystModelInvocation(json.dumps(output), (), 2, 1)

    def current(*args, **kwargs):
        if mode == "stale" and requests:
            raise runtime.TradeoffNotReadyError("COMPARISON_STALE", "Changed snapshot.")
        return snapshot

    def validate(value, bound):
        assert bound is snapshot
        if mode == "assembly":
            raise ValueError("Local assembly defect")
        advice.validate_advice(value, bound)

    monkeypatch.setenv("SOURCEPILOT_LANGFUSE_ENABLED", "false")
    monkeypatch.setattr(runtime, "_current_snapshot", current)
    def read_snapshot(session, tool_runtime):
        tool_runtime.check_budget()
        tool_runtime.record("get_comparison_snapshot", None, None, "SUCCESS")
        return snapshot

    monkeypatch.setattr(runtime, "get_comparison_snapshot", read_snapshot)
    arguments = {
        "session": cast(Session, MemorySession()), "demo_session_id": uuid4(), "project_id": uuid4(),
        "client_factory": Model, "operation": "comparison_advice", "prompt_version": advice.PROMPT_VERSION,
        "base_instructions": advice.INSTRUCTIONS, "result_type": advice.ComparisonAdvice,
        "validate": validate, "selection_factory": AdviceSelectionTask,
        "max_model_turns": 1 if mode == "limit" else 4,
    }
    if mode in {"direct", "tool-repair"}:
        _, _, result = runtime.run_comparison_analyst(**arguments)
        advice.validate_advice(result, snapshot)
        assert result.suggestion.supplier_id is None
    else:
        expected = runtime.TradeoffNotReadyError if mode == "stale" else runtime.TradeoffUnavailableError
        with pytest.raises(expected):
            runtime.run_comparison_analyst(**arguments)
    run = next(item for item in stored if isinstance(item, AIRun))
    assert run.status == {"direct": "COMPLETED", "tool-repair": "COMPLETED", "bad-repair": "VALIDATION_FAILED",
                          "limit": "FAILED_LIMIT_REACHED", "stale": "FAILED", "assembly": "FAILED"}[mode]
    assert len(requests) == {"direct": 1, "tool-repair": 3, "bad-repair": 2,
                             "limit": 1, "stale": 1, "assembly": 1}[mode]
    initial = requests[0]["input_items"][0]["content"]
    assert initial == context_json(selection_context(snapshot))
    assert run.input_hash == structured_input_hash(instructions=advice.INSTRUCTIONS, input_text=initial)
    if mode == "tool-repair":
        tool = json.loads(requests[1]["input_items"][-1]["output"])
        assert tool["fact_catalogue"] == task.initial["fact_catalogue"]
        assert requests[2]["input_items"][:-1] == requests[1]["input_items"]
        assert json.loads(requests[2]["input_items"][-1]["content"]) == bad
        assert "tradeoffs[0]" in requests[2]["instructions"]
        assert "frozen" in requests[2]["instructions"]
        assert run.validation_status == "REPAIRED"
        assert run.tool_call_count == 1
    assert snapshot.model_dump_json() == before
