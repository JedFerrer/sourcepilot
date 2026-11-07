"""Offline serialized-request measurements for the combined selection contract."""

import json
from copy import deepcopy

import pytest

from sourcepilot.ai.advice_selection import SELECTION_INSTRUCTIONS, AdviceSelectionTask
from sourcepilot.ai.comparison_context import comparison_context, context_json
from sourcepilot.ai.tradeoff_analysis import TOOLS
from sourcepilot.comparison.validation import ComparisonRejection
from tests.test_advice_selection import valid_selection
from tests.test_comparison_context import context_fixture


def payload_measurements():
    measurements = {}
    for scenario in ("manual", "missing", "pdf"):
        snapshot = context_fixture(scenario)
        task = AdviceSelectionTask(snapshot)
        rejected = valid_selection(task)
        rejected["tradeoffs"] = [{"relation": "SAME_REQUIREMENT", "fact_ids": ["foreign", "foreign2"]}]
        rejected_text = context_json(rejected)
        with pytest.raises(ComparisonRejection):
            task.accept(rejected_text)
        tool = {**snapshot.model_dump(mode="json"), **comparison_context(snapshot)}
        indexed_tool = task.tool_context("get_comparison_snapshot", tool)
        phases = {}
        for version in ("projection_only", "indexed", "duplicated_facts"):
            initial = deepcopy(task.initial)
            reply = deepcopy(indexed_tool)
            if version == "projection_only":
                initial.pop("fact_catalogue")
                reply.pop("fact_catalogue")
            elif version == "duplicated_facts":
                duplicate = {key: {"supplier_id": fact.supplier_id, "requirement_id": fact.requirement_id,
                                  "quote_id": fact.quote_id, "field_key": fact.field_key,
                                  "state": fact.state, "evidence_ids": fact.evidence_ids, "source": fact.source}
                             for key, fact in task.catalogue.facts.items()}
                initial["fact_catalogue"] = duplicate
                reply["fact_catalogue"] = duplicate
            items = [{"role": "user", "content": context_json(initial)}]
            task.patch_mode = False
            for phase in ("initial", "follow_up", "repair"):
                instructions = SELECTION_INSTRUCTIONS
                if phase == "follow_up":
                    items.extend([
                        {"type": "function_call", "name": "get_comparison_snapshot", "call_id": "snapshot", "arguments": "{}"},
                        {"type": "function_call_output", "call_id": "snapshot", "output": context_json(reply)},
                    ])
                if phase == "repair":
                    items.append({"role": "assistant", "content": rejected_text})
                    instructions += "\n" + task.repair_feedback()
                request = {"model": "fixed-model", "instructions": instructions, "input": items,
                           "tools": TOOLS, "store": False,
                           "text": {"format": {"type": "json_schema", "name": task.schema_name,
                                               "strict": True, "schema": task.schema()}}}
                phases.setdefault(phase, {})[version] = len(context_json(request).encode("utf-8"))
        measurements[scenario] = phases
    return measurements


def test_index_cost_is_bounded_and_avoids_fact_duplication():
    results = payload_measurements()
    assert set(results) == {"manual", "missing", "pdf"}
    for phases in results.values():
        for sizes in phases.values():
            assert sizes["projection_only"] < sizes["indexed"] < sizes["duplicated_facts"]
        assert phases["initial"]["indexed"] < phases["follow_up"]["indexed"] < phases["repair"]["indexed"]


if __name__ == "__main__":
    print(json.dumps(payload_measurements(), indent=2))
