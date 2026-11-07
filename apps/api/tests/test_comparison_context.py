"""Fact-preserving model context and the actual comparison runtime, without a provider/DB."""

import json
from copy import deepcopy
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from sourcepilot.ai import comparison_advice as advice_module
from sourcepilot.ai import tradeoff_analysis as analysis_module
from sourcepilot.ai.analyst_tools import (
    AnalystToolContext,
    AnalystToolRuntime,
    ComparisonSnapshotResult,
    QuoteEvidenceResult,
)
from sourcepilot.ai.client import AnalystModelInvocation
from sourcepilot.ai.comparison_context import (
    CONTEXT_INSTRUCTIONS,
    comparison_context,
    context_json,
    quote_comparison_context,
)
from sourcepilot.ai.structured import structured_input_hash
from sourcepilot.ai.tradeoff_analysis_eval import fixture_snapshot
from sourcepilot.comparison.facts import (
    resolve_commercial_facts,
    resolve_delivery_commitment,
    resolve_quoted_quantity,
)
from sourcepilot.comparison.service import _completeness, _json_value, _quote_fields
from sourcepilot.comparison.validation import (
    ComparisonRejection,
    RejectionCode,
    comparison_repair_feedback,
)
from sourcepilot.persistence.models import (
    AIRun,
    DocumentBlock,
    Quote,
    QuoteFieldEvidence,
    QuoteValue,
    Supplier,
)
from sourcepilot.quotes.domain import QUOTE_FIELD_KEYS, QUOTE_MONEY_FIELDS
from tests.test_reference_binding_guidance import contract, reference_fixture
from tests.test_tradeoff_analysis import valid_output


def context_fixture(scenario: str = "manual") -> ComparisonSnapshotResult:
    """Transient ORM values through production snapshot field/source serializers."""
    snapshot = fixture_snapshot()
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    for index, row in enumerate(payload["suppliers"]):
        supplier = Supplier(id=UUID(row["supplier_id"]), general_moq=500,
                            general_lead_time_days=50, indicative_price_amount="3.20",
                            indicative_price_currency="CNY")
        quote = Quote(id=UUID(row["quote_id"]), supplier_id=supplier.id,
                      revision=2, status="CONFIRMED", entry_type="MANUAL")
        values: dict[str, Any] = {
            "unit_price": ["4.60", "4.45", "4.10"][index], "currency": "USD",
            "quoted_quantity": 2000, "moq": 1000, "production_lead_time": "32 days",
            "shipping_cost": ["600", None, "800"][index],
            "shipping_time": ["10 days", None, "12 days"][index],
            "tooling_cost": "150", "sample_cost": "25", "packaging_cost": "0",
        }
        if scenario == "missing" and index == 2:
            values["currency"] = None
        if scenario == "pdf" and index == 2:
            values["currency"] = None
            values["quoted_quantity"] = 5000
        quote.values = [QuoteValue(
            id=UUID(int=1000 + index * 100 + offset), quote_id=quote.id, field_key=key,
            current_value=values.get(key), current_origin="USER_ENTERED",
            ai_extracted_value=None, uncertainty=None,
        ) for offset, key in enumerate(sorted(QUOTE_FIELD_KEYS))]
        if scenario == "pdf":
            quote.entry_type = "PDF"
            for value in quote.values:
                if value.field_key not in {"unit_price", "currency"}:
                    continue
                value.current_origin = "USER_CORRECTED" if value.field_key == "unit_price" else "AI_EXTRACTED"
                value.ai_extracted_value = "4.22" if value.field_key == "unit_price" else "USD"
                value.uncertainty = "Original source retained; do not treat it as current verification."
                alternatives = [value.ai_extracted_value]
                if index == 2 and value.field_key == "currency":
                    alternatives.append("AUD")
                for position, alternative in enumerate(alternatives):
                    evidence_id = UUID(int=value.id.int * 10 + position)
                    block = DocumentBlock(id=UUID(int=evidence_id.int + 100000),
                                          quote_document_id=UUID(int=200000 + index),
                                          page_number=1, block_number=position + 1,
                                          text="Untrusted PDF fixture text")
                    value.evidence.append(QuoteFieldEvidence(
                        id=evidence_id, document_block_id=block.id, block=block,
                        evidence_value=alternative,
                    ))
        resolutions = {**resolve_commercial_facts(supplier, quote),
                       "quoted_quantity": resolve_quoted_quantity(quote),
                       "delivery_date": resolve_delivery_commitment(quote)}
        row.update(quote_revision=2, quote_fields=_quote_fields(quote),
                   completeness=_completeness(resolutions, quote),
                   resolved_facts=_json_value(resolutions))
        row["evaluation"]["warnings"] = [{"code": "QUANTITY_MISMATCH", "requirement_id": None}]
        row["supplier_facts"]["description"] = "Retain supplier wording, including Unicode: café."
    return snapshot


@pytest.mark.parametrize("scenario", ["manual", "missing", "pdf"])
def test_projection_preserves_every_original_fact_and_ownership(scenario: str) -> None:
    snapshot = context_fixture(scenario)
    before = deepcopy(snapshot)
    projected = comparison_context(snapshot)
    assert snapshot == before
    assert projected["quote_revision_snapshot"] == snapshot.quote_revision_snapshot
    original = cast(dict[str, Any], snapshot.comparison_payload)
    assert projected["comparison_payload"]["brief"] == original["brief"]
    for old, new in zip(original["suppliers"], projected["comparison_payload"]["suppliers"], strict=True):
        for key in old.keys() - {"quote_fields", "completeness", "resolved_facts"}:
            assert new[key] == old[key]
        fields = {field["field_key"]: field for field in new["quote_fields"]}
        for field in old["quote_fields"]:
            actual = deepcopy(fields[field["field_key"]])
            actual.pop("completeness", None)
            actual.pop("currency_context", None)
            assert actual == field  # Every origin, correction, evidence value/role/coordinate.
        for item in old["completeness"]:
            assert {"field_key": item["field_key"], **fields[item["field_key"]]["completeness"]} == item
        for key, resolution in old["resolved_facts"].items():
            current = new["resolved_facts"][key]
            assert current["selected"] == resolution["selected"]
            assert current["status"] == resolution["status"]
            for collection in ("project", "general"):
                alternatives = current[f"{collection}_alternatives"]
                assert alternatives == [fact for fact in resolution[f"{collection}_facts"]
                                        if fact != resolution["selected"]]
                assert all(fact == current["selected"] or fact in alternatives
                           for fact in resolution[f"{collection}_facts"])
        for key in QUOTE_MONEY_FIELDS:
            assert fields[key]["currency_context"] == {
                "quote_id": old["quote_id"], "field_key": "currency",
                "current_value": fields["currency"]["current_value"],
                "completeness": {"state": fields["currency"]["completeness"]["state"]},
            }
    projected["comparison_payload"]["suppliers"][0]["quote_fields"].clear()
    assert snapshot == before  # No shared mutable references back into validation input.


@pytest.mark.parametrize("state", ["known", "missing", "conflicting"])
def test_currency_is_local_and_completeness_is_not_recomputed(state: str) -> None:
    snapshot = context_fixture()
    row = cast(dict[str, Any], snapshot.comparison_payload)["suppliers"][2]
    currency = next(field for field in row["quote_fields"] if field["field_key"] == "currency")
    currency["current_value"] = "AUD" if state == "known" else None
    next(field for field in row["completeness"] if field["field_key"] == "currency")["state"] = state
    projected = comparison_context(snapshot)["comparison_payload"]["suppliers"][2]
    shipping = next(field for field in projected["quote_fields"] if field["field_key"] == "shipping_cost")
    assert shipping["current_value"] == "800"
    assert shipping["completeness"]["state"] == "known"
    assert shipping["currency_context"]["current_value"] == currency["current_value"]
    assert shipping["currency_context"]["completeness"]["state"] == state
    assert shipping["currency_context"]["quote_id"] == row["quote_id"]
    assert "USD" not in context_json(shipping)  # Other quotes cannot supply the currency.


def test_completeness_only_fields_and_unknown_metadata_are_preserved() -> None:
    snapshot = fixture_snapshot()
    row = cast(dict[str, Any], snapshot.comparison_payload)["suppliers"][2]
    row["additional_metadata"] = {"unrecognized": "preserve"}
    fields = comparison_context(snapshot)["comparison_payload"]["suppliers"][2]
    shipping = next(field for field in fields["quote_fields"] if field["field_key"] == "shipping_cost")
    assert shipping == {"field_key": "shipping_cost", "completeness": {"state": "missing"}}
    assert fields["additional_metadata"] == row["additional_metadata"]
    assert all("currency_context" not in field for field in fields["quote_fields"])


def test_equal_value_with_different_provenance_is_not_removed() -> None:
    snapshot = context_fixture("pdf")
    row = cast(dict[str, Any], snapshot.comparison_payload)["suppliers"][0]
    resolution = row["resolved_facts"]["unit_price"]
    other = deepcopy(resolution["selected"])
    other["source_reference"] = "different-quote-value"
    resolution["project_facts"].append(other)
    projected = comparison_context(snapshot)["comparison_payload"]["suppliers"][0]
    assert projected["resolved_facts"]["unit_price"]["project_alternatives"] == [other]
    assert projected["resolved_facts"]["unit_price"]["selected"] == resolution["selected"]


def evidence_fixture(snapshot: ComparisonSnapshotResult, *, revision: int = 2) -> QuoteEvidenceResult:
    row = cast(dict[str, Any], snapshot.comparison_payload)["suppliers"][2]
    return QuoteEvidenceResult(quote_id=row["quote_id"], supplier_id=row["supplier_id"],
                               quote_revision=revision, field_key="shipping_cost", current_value="800",
                               current_origin="USER_ENTERED", ai_extracted_value=None,
                               uncertainty=None, evidence=[])


@pytest.mark.parametrize("mode", ["allowed", "denied", "changed"])
def test_adapter_preserves_tool_scope_budget_and_separates_currency_from_evidence(monkeypatch, mode):
    snapshot = context_fixture("pdf")
    evidence = evidence_fixture(snapshot, revision=3 if mode == "changed" else 2)
    original = evidence.model_dump(mode="json")
    runtime = AnalystToolRuntime(AnalystToolContext(
        demo_session_id=uuid4(), project_id=uuid4(),
        permitted_supplier_ids=frozenset({evidence.supplier_id}),
        permitted_quote_ids=frozenset({evidence.quote_id}) if mode != "denied" else frozenset(),
    ))
    calls = []

    def read(session, tool_runtime, quote_id, field_key):
        calls.append((quote_id, field_key))
        tool_runtime.check_budget()
        tool_runtime.record("get_quote_evidence", None, None, "SUCCESS", quote_id=quote_id, field_key=field_key)
        return evidence

    monkeypatch.setattr(analysis_module, "get_quote_evidence", read)
    args = (cast(Session, None), runtime, "get_quote_evidence",
            {"quote_id": str(evidence.quote_id), "field_key": evidence.field_key}, snapshot)
    if mode == "denied":
        with pytest.raises(ValueError, match="outside"):
            analysis_module._tool_output(*args)
        assert not calls and runtime.successful_call_count == 0
    elif mode == "changed":
        with pytest.raises(analysis_module.TradeoffNotReadyError):
            analysis_module._tool_output(*args)
        assert runtime.successful_call_count == 1
    else:
        output = analysis_module._tool_output(*args)
        context = output.pop("comparison_context")
        assert output == original
        assert context["field"]["currency_context"]["completeness"]["state"] == "conflicting"
        currency = next(field for field in cast(dict[str, Any], snapshot.comparison_payload)["suppliers"][2]["quote_fields"]
                        if field["field_key"] == "currency")
        assert context["currency_field"]["evidence"] == currency["evidence"]
        assert output["evidence"] == []  # Currency citations are not amount PDF citations.
        assert runtime.successful_call_count == 1 and len(calls) == 1
    assert evidence.model_dump(mode="json") == original


@pytest.mark.parametrize("combined", [False, True])
@pytest.mark.parametrize("kind", ["numeric", "boolean"])
def test_real_runtime_uses_projection_for_initial_tools_repair_and_original_validation(monkeypatch, combined, kind):
    snapshot, base, _, _ = reference_fixture(kind)
    original = deepcopy(snapshot)
    stored: list[Any] = []
    requests: list[dict[str, Any]] = []
    validations = []

    class MemorySession:
        def add(self, item):
            if isinstance(item, AIRun):
                item.id = uuid4()
            stored.append(item)

        def commit(self):
            pass

    class Model:
        model = "provider-free-context"

        def invoke(self, **kwargs):
            raise AssertionError("Comparison must use the tool-capable boundary.")

        def invoke_with_tools(self, **kwargs):
            requests.append(deepcopy(kwargs))
            if len(requests) == 1:
                return AnalystModelInvocation("", ({"type": "function_call", "name": "get_comparison_snapshot",
                                                    "call_id": "read", "arguments": "{}"},), 1, 1)
            assert json.loads(kwargs["input_items"][2]["output"])["comparison_payload"] == comparison_context(snapshot)["comparison_payload"]
            output = deepcopy(base)
            if len(requests) == 2:
                output["supplier_summaries"][0]["quote_fields"][0]["field_key"] = "not_a_field"
            return AnalystModelInvocation(contract(combined, output, snapshot).model_dump_json(), (), 1, 1)

    module = advice_module if combined else analysis_module
    validator = advice_module.validate_advice if combined else analysis_module.validate_analysis

    def validate(value, bound):
        assert bound is snapshot and bound == original
        validations.append(bound)
        validator(value, bound)

    monkeypatch.setenv("SOURCEPILOT_LANGFUSE_ENABLED", "false")
    monkeypatch.setattr(analysis_module, "_current_snapshot", lambda *args, **kwargs: snapshot)
    monkeypatch.setattr(analysis_module, "get_comparison_snapshot", lambda *args: snapshot)
    analysis_module.run_comparison_analyst(
        cast(Session, MemorySession()), demo_session_id=uuid4(), project_id=uuid4(),
        client_factory=Model, operation="comparison_advice" if combined else "tradeoff_analysis",
        prompt_version=module.PROMPT_VERSION, base_instructions=module.INSTRUCTIONS,
        result_type=advice_module.ComparisonAdvice if combined else analysis_module.TradeoffAnalysis,
        validate=validate,
    )
    assert len(requests) == 3 and len(validations) == 2
    initial_text = requests[0]["input_items"][0]["content"]
    assert initial_text == context_json(comparison_context(snapshot))
    assert requests[2]["input_items"][:-1] == requests[1]["input_items"]
    assert "not_a_field" in requests[2]["input_items"][-1]["content"]
    run = next(item for item in stored if isinstance(item, AIRun))
    assert run.input_hash == structured_input_hash(instructions=module.INSTRUCTIONS, input_text=initial_text)
    assert run.status == "COMPLETED" and run.validation_status == "REPAIRED"
    assert run.attempts == 3 and snapshot == original


@pytest.mark.parametrize("combined", [False, True])
@pytest.mark.parametrize("scenario,state", [("manual", "known"), ("missing", "missing"), ("pdf", "conflicting")])
def test_runtime_model_receives_local_currency_after_monetary_lookup(monkeypatch, combined, scenario, state):
    snapshot = context_fixture(scenario)
    before = deepcopy(snapshot)
    result = evidence_fixture(snapshot)
    calls = []
    payload = cast(dict[str, Any], snapshot.comparison_payload)

    class MemorySession:
        def add(self, item):
            if isinstance(item, AIRun):
                item.id = uuid4()

        def commit(self):
            pass

    class Model:
        model = "provider-free-currency"

        def invoke(self, **kwargs):
            raise AssertionError("Comparison must use the tool-capable boundary.")

        def invoke_with_tools(self, **kwargs):
            calls.append(deepcopy(kwargs))
            if len(calls) == 1:
                return AnalystModelInvocation("", ({"type": "function_call", "name": "get_quote_evidence",
                    "call_id": "shipping", "arguments": json.dumps({"quote_id": str(result.quote_id),
                                                                      "field_key": "shipping_cost"})},), 1, 1)
            tool = json.loads(kwargs["input_items"][-1]["output"])
            field = tool["comparison_context"]["field"]
            assert field["currency_context"]["quote_id"] == str(result.quote_id)
            assert field["currency_context"]["completeness"]["state"] == state
            assert field["current_value"] == "800" and tool["evidence"] == []
            output = valid_output(payload)
            # A request-aware fake derives its claim from received facts, not prompt wording.
            currency = field["currency_context"]["current_value"]
            section = {"known": "key_tradeoffs", "missing": "important_unknowns",
                       "conflicting": "important_conflicts"}[state]
            text = f"Supplier C shipping cost is {currency} 800." if state == "known" else (
                "Supplier C currency is UNKNOWN." if state == "missing" else "Supplier C currency is CONFLICT.")
            keys = ["shipping_cost", "currency"] if state == "known" else ["currency"]
            output[section].append({"text": text, "supplier_ids": [str(result.supplier_id)],
                "requirement_ids": [], "evidence_ids": [],
                "quote_fields": [{"quote_id": str(result.quote_id), "field_key": key} for key in keys]})
            return AnalystModelInvocation(contract(combined, output, snapshot).model_dump_json(), (), 1, 1)

    def read(session, runtime, quote_id, field_key):
        runtime.check_budget()
        runtime.record("get_quote_evidence", None, None, "SUCCESS", quote_id=quote_id, field_key=field_key)
        return result

    monkeypatch.setenv("SOURCEPILOT_LANGFUSE_ENABLED", "false")
    monkeypatch.setattr(analysis_module, "_current_snapshot", lambda *args, **kwargs: snapshot)
    monkeypatch.setattr(analysis_module, "get_quote_evidence", read)
    module = advice_module if combined else analysis_module
    analysis_module.run_comparison_analyst(
        cast(Session, MemorySession()), demo_session_id=uuid4(), project_id=uuid4(), client_factory=Model,
        operation="comparison_advice" if combined else "tradeoff_analysis",
        prompt_version=module.PROMPT_VERSION, base_instructions=module.INSTRUCTIONS,
        result_type=advice_module.ComparisonAdvice if combined else analysis_module.TradeoffAnalysis,
        validate=lambda value, bound: (
            advice_module.validate_advice(cast(advice_module.ComparisonAdvice, value), bound) if combined
            else analysis_module.validate_analysis(cast(analysis_module.TradeoffAnalysis, value), bound)
        ),
    )
    assert len(calls) == 2 and snapshot == before


def payload_measurements() -> dict[str, Any]:
    """Reproducible request-envelope byte counts; no SDK, network, tokenizer or database."""
    measurements = {}
    for scenario in ("manual", "missing", "pdf"):
        snapshot = context_fixture(scenario)
        initial = {key: snapshot.model_dump(mode="json")[key] for key in (
            "snapshot_id", "brief_revision", "quote_revision_snapshot", "comparison_payload")}
        evidence = evidence_fixture(snapshot)
        before_tool = snapshot.model_dump(mode="json")
        after_tool = {**before_tool, **comparison_context(snapshot)}
        before_evidence = evidence.model_dump(mode="json")
        after_evidence = {**before_evidence, "comparison_context": quote_comparison_context(snapshot, evidence)}
        output = contract(True, valid_output(cast(dict[str, Any], snapshot.comparison_payload)), snapshot)
        # The repair phase contains an actual reference-invalid final of fixed size.
        invalid = output.model_dump(mode="json")
        invalid["analysis"]["supplier_summaries"][0]["quote_fields"] = [
            {"quote_id": str(evidence.quote_id), "field_key": "not_a_field"},
        ]
        output = advice_module.ComparisonAdvice.model_validate(invalid)
        with pytest.raises(ComparisonRejection) as failure:
            advice_module.validate_advice(output, snapshot)
        assert failure.value.code is RejectionCode.QUOTE_REFERENCE
        rejected = output.model_dump_json()
        feedback = comparison_repair_feedback(ComparisonRejection(RejectionCode.QUOTE_REFERENCE, "fixture"))
        phases = {}
        for version in ("before", "after"):
            encode = (lambda value: json.dumps(value, sort_keys=True)) if version == "before" else context_json
            instructions = advice_module.INSTRUCTIONS.removesuffix(CONTEXT_INSTRUCTIONS) if version == "before" else advice_module.INSTRUCTIONS
            items: list[dict[str, Any]] = [{"role": "user", "content": encode(initial if version == "before" else comparison_context(snapshot))}]
            for phase in ("initial", "follow_up", "repair"):
                if phase == "follow_up":
                    for name, call_id, arguments, reply in (
                        ("get_comparison_snapshot", "snapshot", {}, before_tool if version == "before" else after_tool),
                        ("get_quote_evidence", "shipping", {"quote_id": str(evidence.quote_id), "field_key": "shipping_cost"},
                         before_evidence if version == "before" else after_evidence),
                    ):
                        items.extend([{"type": "function_call", "name": name, "call_id": call_id,
                                       "arguments": json.dumps(arguments)},
                                      {"type": "function_call_output", "call_id": call_id, "output": encode(reply)}])
                if phase == "repair":
                    items.append({"role": "assistant", "content": rejected})
                request = {"model": "fixed-model", "instructions": instructions + ("\n" + feedback if phase == "repair" else ""),
                           "input": items, "tools": analysis_module.TOOLS, "store": False,
                           "text": {"format": {"type": "json_schema", "name": "ComparisonAdviceV1", "strict": True,
                                               "schema": advice_module.ComparisonAdvice.model_json_schema()}}}
                phases.setdefault(phase, {})[version] = len(context_json(request).encode("utf-8"))
        measurements[scenario] = phases
    return measurements


def test_payload_measurements_cover_distinct_request_phases() -> None:
    for phases in payload_measurements().values():
        assert set(phases) == {"initial", "follow_up", "repair"}
        for version in ("before", "after"):
            assert phases["initial"][version] < phases["follow_up"][version] < phases["repair"][version]
