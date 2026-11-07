"""Synthetic selections only; real backend, validators, renderer and persistence."""

import json
import os
from pathlib import Path

from tests.e2e_support import model as fixture
from tests.e2e_support.server import main

directory = Path(os.environ["SOURCEPILOT_QA_OUTPUT_DIR"]).resolve()
archive_root = Path(__file__).resolve().parents[5] / ".local-investigation-artifacts"
if not directory.is_relative_to(archive_root) or directory == archive_root:
    raise RuntimeError("QA output must be inside the ignored investigation archive.")
base_selection = fixture.comparison_selection
fixture.SCENARIO["brief"]["requirements"].extend(
    [
        {"kind": "CERTIFICATION", "importance": "PREFERRED", "expected_value": {"value": name}}
        for name in ("BSCI", "ISO 9001")
    ]
)


def selection(initial):
    mode = (directory / "mode.txt").read_text().strip()
    result = base_selection(initial, suggest=mode == "pdf")
    suppliers = initial["comparison_payload"]["suppliers"]
    actions = []

    def add(action, key):
        actions.append({"action": action, "fact_id": key})

    if mode == "delivery":
        for s in suppliers:
            for field in ("delivery_date", "total_lead_time"):
                add("CONFIRM_DELIVERY", f"Q:{s['quote_id']}:{field}")
    elif mode == "mixed":
        for s in suppliers:
            for r in s["evaluation"]["results"]:
                if r["requirement_id"] and r["status"] == "CONFLICT":
                    add("RESOLVE_CONFLICT", f"R:{s['supplier_id']}:{r['requirement_id']}")
        s = next(s for s in suppliers if s["supplier_name"] == "Harbor Pouch Works")
        requested = {
            r["id"]
            for r in initial["comparison_payload"]["brief"]["requirements"]
            if r["expected_value"].get("value") in ("bsci", "iso 9001")
        }
        for r in s["evaluation"]["results"]:
            if r["requirement_id"] in requested and r["status"] == "UNKNOWN":
                add("CONFIRM_MISSING", f"R:{s['supplier_id']}:{r['requirement_id']}")
        add("CONFIRM_MISSING", f"Q:{s['quote_id']}:shipping_cost")
        add("VERIFY_QUOTE", f"Q:{s['quote_id']}:packaging_cost")
        add("CONFIRM_DELIVERY", f"Q:{s['quote_id']}:delivery_date")
    elif mode == "pdf":
        for s in suppliers:
            for field in ("unit_price", "packaging_cost"):
                add("VERIFY_QUOTE", f"Q:{s['quote_id']}:{field}")
    else:
        raise AssertionError("Unknown focused QA mode")
    assert 1 <= len(actions) <= 6
    result["verification_actions"] = actions
    with (directory / "selections.jsonl").open("a") as log:
        log.write(json.dumps({"mode": mode, "selection": result}) + "\n")
    return result


fixture.comparison_selection = selection
original = fixture.DeterministicModel.invoke_with_tools


def counted(self, **kwargs):
    with (directory / "model-counts.jsonl").open("a") as log:
        log.write(json.dumps({"schema": kwargs["schema_name"]}) + "\n")
    return original(self, **kwargs)


fixture.DeterministicModel.invoke_with_tools = counted

if __name__ == "__main__":
    main()
