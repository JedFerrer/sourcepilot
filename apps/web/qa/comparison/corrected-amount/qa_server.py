"""Isolated equivalent fixture; deterministic model boundary, real application."""

import json
import os
from pathlib import Path

from tests.e2e_support import model as fixture
from tests.e2e_support.server import main

directory = Path(os.environ["SOURCEPILOT_QA_OUTPUT_DIR"]).resolve()
archive_root = Path(__file__).resolve().parents[5] / ".local-investigation-artifacts"
if not directory.is_relative_to(archive_root) or directory == archive_root:
    raise RuntimeError("QA output must be inside the ignored investigation archive.")
retained = Path(__file__).resolve().parents[5] / "apps/api/tests/fixtures/comparison_advice"
original = fixture.DeterministicModel.invoke
base_selection = fixture.comparison_selection


def invoke(self, **kwargs):
    if kwargs["schema_name"] != "QuoteExtraction":
        return original(self, **kwargs)
    saved = json.loads((retained / "pdf-extracted-before-correction.json").read_bytes())
    blocks = {b["id"]: b["text"] for b in json.loads(kwargs["input_text"])["document_blocks"]}
    fields = {}
    for key, field in saved["values"].items():
        for evidence in field["evidence"]:
            assert blocks[evidence["block_id"]] == evidence["block_text"]
        fields[key] = {
            "state": field["review_state"],
            "extracted_value": field["ai_extracted_value"],
            "source_block_ids": [e["block_id"] for e in field["evidence"]],
            "uncertainty": field["uncertainty"],
            "conflicting_values": [
                {"value": a["value"], "source_block_ids": [e["block_id"] for e in a["evidence"]]}
                for a in field["conflicting_values"]
            ],
        }
    result = {"fields": fields}
    fixture.QuoteExtraction.model_validate(result)
    return fixture.ModelInvocation(json.dumps(result), 1, 1)


def selection(initial):
    result = base_selection(initial)
    harbor = next(
        s
        for s in initial["comparison_payload"]["suppliers"]
        if s["supplier_name"] == "Harbor Pouch Works"
    )
    reason = next(
        r for r in harbor["evaluation"]["results"] if r["requirement_id"] and r["status"] == "MEETS"
    )
    result["highlights"] = [f"Q:{harbor['quote_id']}:unit_price"]
    result["verification_actions"] = [
        {"action": "RESOLVE_CONFLICT", "fact_id": f"Q:{harbor['quote_id']}:unit_price"}
    ]
    if (directory / "mode.txt").read_text().strip() == "suggestion":
        result["suggestion"] = {
            "supplier_id": harbor["supplier_id"],
            "reason_fact_ids": [f"R:{harbor['supplier_id']}:{reason['requirement_id']}"],
            "no_suggestion_reason": None,
        }
    else:
        result["suggestion"] = {
            "supplier_id": None,
            "reason_fact_ids": [],
            "no_suggestion_reason": "VERIFY_BEFORE_CHOOSING",
        }
    with (directory / "selections.jsonl").open("a") as output:
        output.write(json.dumps(result) + "\n")
    return result


fixture.DeterministicModel.invoke = invoke
fixture.comparison_selection = selection
if __name__ == "__main__":
    main()
