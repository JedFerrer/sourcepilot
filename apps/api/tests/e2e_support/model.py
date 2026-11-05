"""Deterministic contract fixtures at the model boundary, with no provider fallback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sourcepilot.ai.brief_interpreter import ExtractedBrief
from sourcepilot.ai.clarification import ClarificationSet
from sourcepilot.ai.client import AnalystModelInvocation, ModelInvocation
from sourcepilot.ai.comparison_advice import ComparisonAdvice
from sourcepilot.ai.quote_extractor import QuoteExtraction
from sourcepilot.ai.supplier_explanation import ModelSupplierExplanation
from sourcepilot.ai.tradeoff_analysis import TradeoffAnalysis

SUPPORT = Path(__file__).parent
SCENARIO = json.loads((SUPPORT / "scenario.json").read_text(encoding="utf-8"))
API = SUPPORT.parents[1]
PDFS = API / "tests" / "fixtures" / "quote_pdfs"
SCHEMAS = {model.__name__: model for model in (
    ExtractedBrief, ClarificationSet, QuoteExtraction, ModelSupplierExplanation,
    ComparisonAdvice, TradeoffAnalysis,
)}


def check_schema(name: str, schema: dict[str, Any], allowed: set[str]) -> None:
    if name not in allowed or name not in SCHEMAS:
        raise AssertionError(f"Unsupported E2E model operation: {name}")
    if schema != SCHEMAS[name].model_json_schema():
        raise AssertionError(f"Unexpected E2E schema: {name}")


def point(text: str, supplier: dict[str, Any], requirements: list[str] | None = None,
          field: str | None = None) -> dict[str, Any]:
    return {"text": text, "supplier_ids": [supplier["supplier_id"]],
            "requirement_ids": requirements or [], "evidence_ids": [],
            "quote_fields": [{"quote_id": supplier["quote_id"], "field_key": field}] if field else []}


def comparison_output(payload: dict[str, Any]) -> dict[str, Any]:
    """Reference real facts without inventing supplier fitness or an overall score."""
    analysis: dict[str, Any] = {"supplier_summaries": [], "key_tradeoffs": [],
                                "important_unknowns": [], "important_conflicts": []}
    requirements = {item["id"]: item for item in payload["brief"]["requirements"]}
    for supplier in payload["suppliers"]:
        fields = {item["field_key"]: item for item in supplier["quote_fields"]}
        price = fields["unit_price"]["current_value"]
        currency = fields["currency"]["current_value"]
        failures = [item["requirement_id"] for item in supplier["evaluation"]["results"]
                    if item["requirement_id"] is not None and item["status"] == "DOES_NOT_MEET"
                    and requirements[item["requirement_id"]]["importance"] == "REQUIRED"]
        analysis["supplier_summaries"].append(point(
            f"{supplier['supplier_name']} quotes {price} {currency} per unit. Review its requirement findings.",
            supplier, failures, "unit_price"))
        analysis["key_tradeoffs"].append(point(
            f"{supplier['supplier_name']}: compare the stated production lead time with the other quotations.",
            supplier, field="production_lead_time"))
        for finding in supplier["evaluation"]["results"]:
            if finding["requirement_id"] is None or finding["status"] not in {"UNKNOWN", "CONFLICT"}:
                continue
            section = "important_unknowns" if finding["status"] == "UNKNOWN" else "important_conflicts"
            analysis[section].append(point(
                f"The requirement state is {finding['status']}.", supplier, [finding["requirement_id"]]))
        for missing in supplier["completeness"]:
            if missing["state"] not in {"missing", "conflicting"}:
                continue
            section = "important_unknowns" if missing["state"] == "missing" else "important_conflicts"
            label = missing["field_key"].replace("_", " ")
            analysis[section].append(point(
                f"{label} is {'unknown' if missing['state'] == 'missing' else 'conflicting'}.",
                supplier, field=missing["field_key"]))
    advisory = SCENARIO["advisory"]
    return {"analysis": analysis, "suggestion": {
        "supplier_id": advisory["supplier_id"], "supporting_reasons": advisory["supporting_reasons"],
        "tradeoffs": advisory["tradeoffs"], "evidence_ids": [],
        "uncertainties": [point(advisory["uncertainty"], payload["suppliers"][0])],
    }}


def supplier_output(snapshot: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {"supplier_id": snapshot["supplier_id"], "strengths": [],
                              "required_failures": [], "preferred_findings": [], "unknowns": [],
                              "conflicts": [], "concerns": [], "evidence_ids": []}
    available = {item["id"] for item in evidence["evidence"]}
    cited: set[str] = set()
    for finding in snapshot["evaluations"]:
        state = finding["status"]
        section = ("unknowns" if state == "UNKNOWN" else "conflicts" if state == "CONFLICT"
                   else "required_failures" if state == "DOES_NOT_MEET" and finding["importance"] == "REQUIRED"
                   else "preferred_findings" if finding["importance"] == "PREFERRED"
                   else "strengths" if state == "MEETS" else "concerns")
        ids = finding["evidence_ids"]
        if not set(ids) <= available:
            raise AssertionError("E2E explanation evidence was not fetched.")
        cited.update(ids)
        output[section].append({"text": None, "requirement_id": finding["requirement_id"], "evidence_ids": ids})
    output["evidence_ids"] = sorted(cited)
    return output


class DeterministicModel:
    model = "e2e-deterministic-v1"

    def invoke(self, *, instructions: str, input_text: str, schema_name: str,
               schema: dict[str, Any]) -> ModelInvocation:
        check_schema(schema_name, schema, {"ExtractedBrief", "ClarificationSet", "QuoteExtraction"})
        if schema_name == "ExtractedBrief":
            if input_text != SCENARIO["request"]:
                raise AssertionError("Unsupported E2E sourcing request.")
            output = SCENARIO["brief"]
        elif schema_name == "ClarificationSet":
            data = json.loads(input_text)
            if [item["field_key"] for item in data["unresolved_fields"]] != ["delivery_target"]:
                raise AssertionError("Unexpected E2E clarification fields.")
            output = {"questions": [{"field_key": "delivery_target",
                      "question": "When should these bags be delivered?", "reason": "Delivery timing is unstated."}]}
        else:
            data = json.loads(input_text)
            blocks = data["document_blocks"]
            expected = json.loads((PDFS / "expected_blocks.json").read_text(encoding="utf-8"))
            cases = {"harbor_primary.pdf": "harbor-primary", "willow_primary.pdf": "willow-primary",
                     "moss_primary.pdf": "moss-primary"}
            matched = [case for filename, case in cases.items()
                       if blocks == [{"id": ref, "text": content} for ref, content in expected[filename]["blocks"]]]
            if len(matched) != 1:
                raise AssertionError("Unsupported E2E PDF document blocks.")
            outputs = json.loads((API / "evals/quote_extraction/model_outputs.json").read_text(encoding="utf-8"))
            output = outputs[matched[0]]
        SCHEMAS[schema_name].model_validate(output)
        return ModelInvocation(json.dumps(output), 1, 1)

    def invoke_with_tools(self, *, instructions: str, input_items: list[dict[str, Any]],
                          tools: list[dict[str, Any]], schema_name: str,
                          schema: dict[str, Any]) -> AnalystModelInvocation:
        check_schema(schema_name, schema, {"ModelSupplierExplanation", ComparisonAdvice.__name__, "TradeoffAnalysis"})
        initial = json.loads(input_items[0]["content"])
        supplier_task = schema_name == "ModelSupplierExplanation"
        if supplier_task:
            calls = [("get_supplier_snapshot", {"supplier_id": initial["supplier_id"]}),
                     ("get_supplier_evidence", {"supplier_id": initial["supplier_id"], "claim_keys": None})]
        else:
            first = initial["comparison_payload"]["suppliers"][0]
            calls = [("get_comparison_snapshot", {}),
                     ("get_quote_evidence", {"quote_id": first["quote_id"], "field_key": "unit_price"})]
        available = {item["name"] for item in tools}
        if not {name for name, _ in calls} <= available:
            raise AssertionError("Expected E2E analyst tools are unavailable.")
        if len(input_items) == 1:
            return AnalystModelInvocation("", tuple({"type": "function_call", "name": name,
                "call_id": f"e2e-{index}", "arguments": json.dumps(arguments)}
                for index, (name, arguments) in enumerate(calls)), 1, 1)
        if len(input_items) != 5:
            raise AssertionError("Unexpected E2E analyst turn sequence.")
        for index, (name, arguments) in enumerate(calls):
            call, result = input_items[index + 1], input_items[index + 3]
            if (call.get("name") != name or json.loads(call["arguments"]) != arguments
                    or result.get("type") != "function_call_output"
                    or result.get("call_id") != f"e2e-{index}"):
                raise AssertionError("Unexpected E2E analyst tool result sequence.")
        results = [json.loads(item["output"]) for item in input_items[3:]]
        if supplier_task:
            output = supplier_output(results[0], results[1])
        else:
            snapshot = results[0]
            if snapshot["availability"] != "CURRENT" or snapshot["snapshot_id"] != initial["snapshot_id"]:
                raise AssertionError("E2E analyst requires a current matching snapshot.")
            if results[1]["quote_id"] != initial["comparison_payload"]["suppliers"][0]["quote_id"]:
                raise AssertionError("Unexpected E2E quote evidence owner.")
            output = comparison_output(snapshot["comparison_payload"])
            if schema_name == "TradeoffAnalysis":
                output = output["analysis"]
        SCHEMAS[schema_name].model_validate(output)
        return AnalystModelInvocation(json.dumps(output), (), 1, 1)


class BlockedOpenAI:
    def __init__(self, *args: object, **kwargs: object) -> None:
        raise AssertionError("Live OpenAI construction is forbidden in browser E2E.")


def install_model_boundary() -> None:
    from unittest.mock import patch

    patch("sourcepilot.ai.client.OpenAI", BlockedOpenAI).start()
    patch("sourcepilot.ai.client.AsyncOpenAI", BlockedOpenAI).start()
    patch("sourcepilot.ai.client.OpenAIResponsesClient.from_environment", DeterministicModel).start()
