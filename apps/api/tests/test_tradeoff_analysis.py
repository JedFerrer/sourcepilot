"""M4-U6 tradeoff contracts, bounded loop, stale input, and API isolation."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from sourcepilot.ai.analyst_tools import ComparisonSnapshotResult, EvaluationAvailability
from sourcepilot.ai.client import AnalystModelInvocation, ModelInvocation, ModelProviderError
from sourcepilot.ai.comparison_context import context_json
from sourcepilot.ai.structured import structured_input_hash
from sourcepilot.ai.tradeoff_analysis import (
    INSTRUCTIONS,
    PROMPT_VERSION,
    TradeoffAnalysis,
    TradeoffNotReadyError,
    TradeoffUnavailableError,
    _quote_field_labels,
    analyze_tradeoffs,
    validate_analysis,
)
from sourcepilot.main import app
from sourcepilot.persistence.database import get_database_session
from sourcepilot.persistence.models import (
    AIRun,
    Comparison,
    Project,
    Quote,
    SupplierExplanationRunStep,
)
from sourcepilot.suppliers.seed import seed_suppliers
from tests.database_test_support import (
    create_test_engine,
    persistence_test_database_url_from_environment,
    reset_test_database,
)
from tests.test_comparison_snapshot import confirm_manual, setup_project


@pytest.mark.parametrize("text,expected", [
    ("shipping time", {"shipping_time"}),
    ("shipping cost", {"shipping_cost"}),
    ("sample lead time", {"sample_lead_time"}),
    ("production lead time", {"production_lead_time"}),
    ("total lead time", {"total_lead_time"}),
    ("shipping cost and shipping time", {"shipping_cost", "shipping_time"}),
    ("sample lead time and total lead time", {"sample_lead_time", "total_lead_time"}),
    ("shipping", set()),
    ("lead time", set()),
])
@pytest.mark.parametrize("separator", [" ", "_", "-"])
def test_quote_field_labels_resolve_explicit_fields(
    text: str, expected: set[str], separator: str,
) -> None:
    text = " and ".join(label.replace(" ", separator) for label in text.split(" and "))
    assert _quote_field_labels(text.upper()) == expected


@pytest.fixture(scope="module")
def database_url() -> str:
    return persistence_test_database_url_from_environment()


@pytest.fixture(scope="module")
def engine(database_url: str) -> Iterator[Engine]:
    value = create_test_engine(database_url)
    yield value
    value.dispose()


@pytest.fixture
def client(engine: Engine, database_url: str) -> Iterator[TestClient]:
    reset_test_database(database_url)
    with Session(engine) as session:
        seed_suppliers(session)
        session.commit()
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_database_session] = override
    with TestClient(app, raise_server_exceptions=False) as value:
        assert value.post("/demo-session").status_code == 204
        yield value
    app.dependency_overrides.clear()
    reset_test_database(database_url)


def ready(client: TestClient) -> tuple[str, list[str], list[str]]:
    project_id, supplier_ids = setup_project(client)
    quote_ids = [confirm_manual(client, project_id, supplier_id) for supplier_id in supplier_ids[:2]]
    assert client.post(f"/projects/{project_id}/comparison/generate").status_code == 201
    return project_id, supplier_ids, quote_ids


def valid_output(payload: dict[str, Any]) -> dict[str, Any]:
    suppliers = payload["suppliers"]
    requirements = {item["id"]: item for item in payload["brief"]["requirements"]}
    summaries: list[dict[str, object]] = []
    unknowns: list[dict[str, object]] = []
    conflicts: list[dict[str, object]] = []
    for supplier in suppliers:
        supplier_id = supplier["supplier_id"]
        findings = supplier["evaluation"]["results"]
        failures = [item["requirement_id"] for item in findings
                    if item["status"] == "DOES_NOT_MEET"
                    and item["requirement_id"] is not None
                    and requirements[item["requirement_id"]]["importance"] == "REQUIRED"]
        summaries.append({"text": "Confirmed comparison facts summarized.",
                          "supplier_ids": [supplier_id], "requirement_ids": failures,
                          "quote_fields": [], "evidence_ids": []})
        for item in findings:
            if item["status"] not in {"UNKNOWN", "CONFLICT"} or item["requirement_id"] is None:
                continue
            point = {"text": f"{item['status']} in the deterministic comparison.",
                     "supplier_ids": [supplier_id],
                     "requirement_ids": [item["requirement_id"]],
                     "quote_fields": [], "evidence_ids": []}
            (unknowns if item["status"] == "UNKNOWN" else conflicts).append(point)
    return {"supplier_summaries": summaries, "key_tradeoffs": [],
            "important_unknowns": unknowns, "important_conflicts": conflicts}


class FakeModel:
    model = "test-model"

    def __init__(self, *, actions: list[str] | None = None,
                 on_final: Callable[[], None] | None = None,
                 on_invoke: Callable[[int], None] | None = None,
                 excluded_supplier_id: str | None = None) -> None:
        self.actions = actions or []
        self.on_final = on_final
        self.on_invoke = on_invoke
        self.excluded_supplier_id = excluded_supplier_id
        self.calls = 0
        self.inputs: list[dict[str, Any]] = []

    def invoke(self, **kwargs: object) -> ModelInvocation:
        raise AssertionError("Analyst must use tool-capable provider method.")

    def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
        self.calls += 1
        if self.on_invoke is not None:
            self.on_invoke(self.calls)
        input_items = cast(list[dict[str, Any]], kwargs["input_items"])
        first = cast(dict[str, Any], json.loads(input_items[0]["content"]))
        self.inputs.append(first)
        action = self.actions.pop(0) if self.actions else "final"
        if action == "provider":
            raise ModelProviderError("temporary", retryable=True)
        if action == "invalid":
            return AnalystModelInvocation("{}", (), 2, 1)
        if action == "tool":
            call = {"type": "function_call", "name": "get_comparison_snapshot",
                    "call_id": f"call-{self.calls}", "arguments": "{}"}
            return AnalystModelInvocation("", (call,), 2, 1)
        if action == "foreign_quote":
            call = {"type": "function_call", "name": "get_quote_evidence",
                    "call_id": "foreign", "arguments": json.dumps({
                        "quote_id": str(uuid4()), "field_key": "unit_price"})}
            return AnalystModelInvocation("", (call,), 2, 1)
        if action == "excluded_supplier":
            assert self.excluded_supplier_id is not None
            call = {"type": "function_call", "name": "get_supplier_snapshot",
                    "call_id": "excluded", "arguments": json.dumps({
                        "supplier_id": self.excluded_supplier_id})}
            return AnalystModelInvocation("", (call,), 2, 1)
        if self.on_final is not None:
            self.on_final()
        return AnalystModelInvocation(json.dumps(valid_output(first["comparison_payload"])), (), 2, 1)


def test_contract_rejects_unpermitted_references_and_scores() -> None:
    supplier_id, quote_id, requirement_id = uuid4(), uuid4(), uuid4()
    snapshot = ComparisonSnapshotResult(
        availability=EvaluationAvailability.CURRENT, snapshot_id=uuid4(),
        brief_revision=1, quote_revision_snapshot={}, generated_at=datetime.now(UTC), stale=False,
        comparison_payload={"brief": {"requirements": [{"id": str(requirement_id),
            "importance": "REQUIRED"}]}, "suppliers": [{
            "supplier_id": str(supplier_id), "quote_id": str(quote_id),
            "quote_fields": [{"field_key": "unit_price", "evidence": []}],
            "completeness": [{"field_key": "unit_price", "state": "known"},
                             {"field_key": "shipping_cost", "state": "missing"}],
            "supplier_facts": {"evidence": []},
            "evaluation": {"results": [{"requirement_id": str(requirement_id),
                                        "status": "DOES_NOT_MEET"}]},
        }]},
    )
    assert snapshot.comparison_payload is not None
    output = valid_output(cast(dict[str, Any], snapshot.comparison_payload))
    analysis = TradeoffAnalysis.model_validate(output)
    validate_analysis(analysis, snapshot)
    output["important_unknowns"] = [{
        "text": "Shipping cost is unknown.", "supplier_ids": [str(supplier_id)],
        "requirement_ids": [], "quote_fields": [{"quote_id": str(quote_id),
                                                "field_key": "shipping_cost"}], "evidence_ids": [],
    }]
    validate_analysis(TradeoffAnalysis.model_validate(output), snapshot)
    output["supplier_summaries"][0]["supplier_ids"] = [str(uuid4())]
    with pytest.raises(ValueError, match="unpermitted supplier"):
        validate_analysis(TradeoffAnalysis.model_validate(output), snapshot)
    output["supplier_summaries"][0]["supplier_ids"] = [str(supplier_id)]
    output["supplier_summaries"][0]["text"] = "Supplier fit score: 92"
    with pytest.raises(ValueError, match="score"):
        validate_analysis(TradeoffAnalysis.model_validate(output), snapshot)
    output["supplier_summaries"][0]["text"] = "Supplier scored 92/100."
    with pytest.raises(ValueError, match="score"):
        validate_analysis(TradeoffAnalysis.model_validate(output), snapshot)
    for text in ("Supplier A is 8/10.", "Supplier A is 8 out of 10.",
                 "Supplier A has a 92% match.", "Supplier A rating: 8.",
                 "Supplier A has a score of 8."):
        output["supplier_summaries"][0]["text"] = text
        with pytest.raises(ValueError, match="score"):
            validate_analysis(TradeoffAnalysis.model_validate(output), snapshot)
    for text in ("The unit price is USD 8.10.", "MOQ is 100 units.",
                 "Production lead time is 38 days.", "8% shipping tax is quoted."):
        output["supplier_summaries"][0]["text"] = text
        validate_analysis(TradeoffAnalysis.model_validate(output), snapshot)


def test_preconditions_and_success(client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.test_ai_tracing import Observation

    calls = []
    monkeypatch.setattr("sourcepilot.ai.tracing.langfuse_client", lambda: Observation(calls))
    project_id, supplier_ids = setup_project(client)
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        model = FakeModel()
        with pytest.raises(TradeoffNotReadyError, match="Generate"):
            analyze_tradeoffs(session, demo_session_id=project.demo_session_id,
                              project_id=project.id, client_factory=lambda: model)
        assert session.scalar(select(AIRun.id)) is None
    for supplier_id in supplier_ids[:2]:
        confirm_manual(client, project_id, supplier_id)
    comparison = client.post(f"/projects/{project_id}/comparison/generate").json()
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        model = FakeModel(actions=["tool", "final"])
        response = analyze_tradeoffs(session, demo_session_id=project.demo_session_id,
                                     project_id=project.id, client_factory=lambda: model)
        assert str(response.snapshot_id) == comparison["id"]
        assert model.calls == 2
        assert {item["supplier_id"] for item in model.inputs[0]["comparison_payload"]["suppliers"]} == set(supplier_ids[:2])
        run = session.get(AIRun, response.run_id)
        assert run is not None and run.status == "COMPLETED"
        assert run.model_turn_count == 2 and run.tool_call_count == 1
        assert (run.input_tokens, run.output_tokens) == (4, 2)
        assert any(call.get("name") == "tradeoff_analysis" for call in calls)
        assert sum("usage_details" in call for call in calls) == 2
        assert run.prompt_version == PROMPT_VERSION
        initial = {key: model.inputs[0][key] for key in (
            "snapshot_id", "brief_revision", "quote_revision_snapshot", "comparison_payload")}
        assert run.input_hash == structured_input_hash(
            instructions=INSTRUCTIONS, input_text=context_json(initial))
        assert session.scalars(select(SupplierExplanationRunStep).where(
            SupplierExplanationRunStep.air_run_id == run.id)).all()


def test_stale_and_midrun_change(client: TestClient, engine: Engine) -> None:
    project_id, _, quote_ids = ready(client)
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        def change() -> None:
            with Session(engine) as writer:
                quote = writer.get(Quote, UUID(quote_ids[0]))
                assert quote is not None
                quote.revision += 1
                writer.commit()
        with pytest.raises(TradeoffNotReadyError, match="Regenerate"):
            analyze_tradeoffs(session, demo_session_id=project.demo_session_id,
                              project_id=project.id,
                              client_factory=lambda: FakeModel(on_final=change))
        run = session.scalars(select(AIRun).where(AIRun.operation == "tradeoff_analysis")).one()
        assert run.status == "FAILED" and run.error_type == "COMPARISON_STALE"
        before = run.id
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        with pytest.raises(TradeoffNotReadyError, match="Regenerate"):
            analyze_tradeoffs(session, demo_session_id=project.demo_session_id,
                              project_id=project.id, client_factory=FakeModel)
        assert session.scalars(select(AIRun.id)).all() == [before]
    assert client.post(f"/projects/{project_id}/comparison/generate").status_code == 201
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        result = analyze_tradeoffs(session, demo_session_id=project.demo_session_id,
                                   project_id=project.id, client_factory=FakeModel)
        assert result.snapshot_id != before


@pytest.mark.parametrize("actions,expected_status", [
    (["provider", "provider"], "PROVIDER_FAILED"),
    (["invalid", "invalid"], "VALIDATION_FAILED"),
    (["foreign_quote"], "VALIDATION_FAILED"),
    (["tool", "tool"], "FAILED_LIMIT_REACHED"),
])
def test_terminal_failure_reclassifies_changed_quote_inputs(
    client: TestClient, engine: Engine, actions: list[str], expected_status: str,
) -> None:
    project_id, _, quote_ids = ready(client)
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        def change_on_first_turn(turn: int) -> None:
            if turn == 1:
                with Session(engine) as writer:
                    quote = writer.get(Quote, UUID(quote_ids[0]))
                    assert quote is not None
                    quote.revision += 1
                    writer.commit()
        with pytest.raises(TradeoffNotReadyError) as raised:
            analyze_tradeoffs(session, demo_session_id=project.demo_session_id,
                              project_id=project.id,
                              client_factory=lambda: FakeModel(actions=actions,
                                                               on_invoke=change_on_first_turn),
                              max_tool_calls=1, sleep=lambda _: None)
        assert raised.value.code == "COMPARISON_STALE"
        run = session.scalars(select(AIRun).where(AIRun.operation == "tradeoff_analysis")).one()
        assert run.status == "FAILED" and run.error_type == "COMPARISON_STALE"
        assert run.status != expected_status


def test_retry_limits_and_tool_allowlist(client: TestClient, engine: Engine) -> None:
    project_id, supplier_ids, _ = ready(client)
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        model = FakeModel(actions=["provider", "invalid", "final"])
        result = analyze_tradeoffs(session, demo_session_id=project.demo_session_id,
                                   project_id=project.id, client_factory=lambda: model,
                                   sleep=lambda _: None)
        run = session.get(AIRun, result.run_id)
        assert run is not None and run.validation_status == "REPAIRED"
        assert model.calls == 3
        with pytest.raises(TradeoffUnavailableError):
            analyze_tradeoffs(session, demo_session_id=project.demo_session_id,
                              project_id=project.id,
                              client_factory=lambda: FakeModel(actions=["provider", "provider"]),
                              sleep=lambda _: None)
        provider_run = session.scalars(select(AIRun).order_by(AIRun.started_at.desc())).first()
        assert provider_run is not None and provider_run.status == "PROVIDER_FAILED"
        with pytest.raises(TradeoffUnavailableError):
            analyze_tradeoffs(session, demo_session_id=project.demo_session_id,
                              project_id=project.id,
                              client_factory=lambda: FakeModel(actions=["tool", "tool"]),
                              max_tool_calls=1, sleep=lambda _: None)
        latest = session.scalars(select(AIRun).order_by(AIRun.started_at.desc())).first()
        assert latest is not None and latest.status == "FAILED_LIMIT_REACHED"
        with pytest.raises(TradeoffUnavailableError):
            analyze_tradeoffs(session, demo_session_id=project.demo_session_id,
                              project_id=project.id,
                              client_factory=lambda: FakeModel(actions=["foreign_quote"]),
                              sleep=lambda _: None)
        with pytest.raises(TradeoffUnavailableError):
            analyze_tradeoffs(session, demo_session_id=project.demo_session_id,
                              project_id=project.id,
                              client_factory=lambda: FakeModel(
                                  actions=["excluded_supplier"],
                                  excluded_supplier_id=supplier_ids[2]),
                              sleep=lambda _: None)
        with pytest.raises(TradeoffUnavailableError):
            analyze_tradeoffs(session, demo_session_id=project.demo_session_id,
                              project_id=project.id,
                              client_factory=lambda: FakeModel(actions=["invalid", "invalid"]),
                              sleep=lambda _: None)
        invalid_run = session.scalars(select(AIRun).order_by(AIRun.started_at.desc())).first()
        assert invalid_run is not None and invalid_run.status == "VALIDATION_FAILED"
        with pytest.raises(TradeoffUnavailableError):
            analyze_tradeoffs(session, demo_session_id=project.demo_session_id,
                              project_id=project.id,
                              client_factory=lambda: FakeModel(actions=["tool"] * 4),
                              max_model_turns=4, sleep=lambda _: None)
        limit_run = session.scalars(select(AIRun).order_by(AIRun.started_at.desc())).first()
        assert limit_run is not None and limit_run.status == "FAILED_LIMIT_REACHED"
        assert limit_run.model_turn_count == 4


def test_api_is_session_scoped(client: TestClient, engine: Engine,
                               monkeypatch: pytest.MonkeyPatch) -> None:
    project_id, _, _ = ready(client)
    monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", FakeModel)
    response = client.post(f"/projects/{project_id}/comparison/analysis")
    assert response.status_code == 200, response.text
    assert response.json()["snapshot_id"] == client.get(
        f"/projects/{project_id}/comparison").json()["id"]
    with TestClient(app, raise_server_exceptions=False) as other:
        assert other.post("/demo-session").status_code == 204
        assert other.post(f"/projects/{project_id}/comparison/analysis").status_code == 404


def test_api_preconditions_do_not_call_provider(client: TestClient, engine: Engine,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    project_id, supplier_ids = setup_project(client)
    def unavailable_provider() -> None:
        raise AssertionError("Provider must not run without a current comparison.")
    monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment",
                        unavailable_provider)
    absent = client.post(f"/projects/{project_id}/comparison/analysis")
    assert absent.status_code == 404 and absent.json()["error"]["code"] == "COMPARISON_NOT_FOUND"
    for supplier_id in supplier_ids[:2]:
        confirm_manual(client, project_id, supplier_id)
    generated = client.post(f"/projects/{project_id}/comparison/generate")
    assert generated.status_code == 201
    with Session(engine) as session:
        comparison = session.get(Comparison, UUID(generated.json()["id"]))
        assert comparison is not None
        comparison.stale = True
        session.commit()
    stale = client.post(f"/projects/{project_id}/comparison/analysis")
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "COMPARISON_STALE"


def test_n4_tradeoff_prompt_guidance() -> None:
    assert PROMPT_VERSION == "tradeoff-analysis-v9"
    for guidance in (
        "Use the supplied current comparison first", "do not reread",
        "specific claims", "reuse retrieved results", "four model turns",
        "six successful tool calls", "Every call in a batch",
        "Reserve capacity for final output", "Provider retries",
        "Known quote fields and MEETS requirements", "grouped citations",
        "original PDF value as provenance", "all required",
    ):
        assert guidance in INSTRUCTIONS


@pytest.mark.parametrize("mutation", [
    "none", "known-field", "meets-requirement", "mixed-meets-group",
    "omit-conflict", "omit-unknown", "omit-failure",
])
def test_n4_conflicts_and_required_disclosures(mutation: str) -> None:
    from sourcepilot.ai.tradeoff_analysis_eval import CERT, LEAD, A, B, fixture_snapshot

    snapshot = fixture_snapshot()
    assert snapshot.comparison_payload is not None
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    output = valid_output(payload)
    # Correction provenance belongs in a summary, while A's genuine lead-time
    # conflict and C's certification unknown remain in their own sections.
    output["supplier_summaries"][0]["text"] = (
        "Current confirmed price is USD 4.50; original PDF price was USD 4.22, "
        "which does not verify the user correction.")
    point = {"text": "Comparison finding.", "supplier_ids": [A],
             "requirement_ids": [], "quote_fields": [], "evidence_ids": []}
    if mutation == "known-field":
        point["quote_fields"] = [{"quote_id": payload["suppliers"][0]["quote_id"],
                                  "field_key": "unit_price"}]
        output["important_conflicts"].append(point)
    elif mutation == "meets-requirement":
        point.update(supplier_ids=[B], requirement_ids=[LEAD])
        output["important_conflicts"].append(point)
    elif mutation == "mixed-meets-group":
        output["important_conflicts"][0]["supplier_ids"].append(B)
    elif mutation == "omit-conflict":
        output["important_conflicts"] = []
    elif mutation == "omit-unknown":
        output["important_unknowns"] = []
    elif mutation == "omit-failure":
        for summary in output["supplier_summaries"]:
            summary["requirement_ids"] = []
    analysis = TradeoffAnalysis.model_validate(output)
    if mutation == "none":
        validate_analysis(analysis, snapshot)
        assert analysis.important_conflicts[0].requirement_ids == [UUID(LEAD)]
        assert any(UUID(CERT) in point.requirement_ids for point in analysis.important_unknowns)
    else:
        with pytest.raises(ValueError):
            validate_analysis(analysis, snapshot)


def semantic_repair_output(payload: dict[str, Any]) -> dict[str, Any]:
    """Canonical states plus separately cited facts/provenance, using the eval snapshot."""
    from sourcepilot.ai.tradeoff_analysis_eval import CERT, PDF_PRICE, A, C

    output = valid_output(payload)
    labels = {"CERTIFICATION": "certification", "PRODUCTION_LEAD_TIME": "production lead time"}
    requirements = {row["id"]: row for row in payload["brief"]["requirements"]}
    for summary, supplier in zip(output["supplier_summaries"], payload["suppliers"], strict=True):
        summary["requirement_ids"] = [CERT]
        state = supplier["evaluation"]["results"][0]["status"]
        summary["text"] = f"{supplier['supplier_name']} certification is {state}."
    for section in ("important_unknowns", "important_conflicts"):
        for point in output[section]:
            supplier = next(row for row in payload["suppliers"]
                            if row["supplier_id"] == point["supplier_ids"][0])
            kind = labels[requirements[point["requirement_ids"][0]]["kind"]]
            state = "UNKNOWN" if section == "important_unknowns" else "CONFLICT"
            point["text"] = f"{supplier['supplier_name']} {kind} is {state}."
    first, _, third = payload["suppliers"]
    output["key_tradeoffs"] = [{
        "text": "Supplier A quoted production lead time is 25 days.",
        "supplier_ids": [A], "requirement_ids": [], "evidence_ids": [],
        "quote_fields": [{"quote_id": first["quote_id"], "field_key": "production_lead_time"}],
    }, {
        "text": ("Supplier A current confirmed price is USD 4.50. Original PDF price was "
                 "USD 4.22; it does not verify the user correction. Currency must be "
                 "established before comparing any price without a currency."),
        "supplier_ids": [A], "requirement_ids": [], "evidence_ids": [PDF_PRICE],
        "quote_fields": [{"quote_id": first["quote_id"], "field_key": "unit_price"}],
    }]
    output["supplier_summaries"][2]["text"] = (
        "Supplier C quoted production lead time is 30 days. Supplier C certification is UNKNOWN.")
    output["important_unknowns"].append({
        "text": "Supplier C shipping cost is UNKNOWN.", "supplier_ids": [C],
        "requirement_ids": [], "evidence_ids": [],
        "quote_fields": [{"quote_id": third["quote_id"], "field_key": "shipping_cost"}],
    })
    return output


@pytest.mark.parametrize("text", [
    "Supplier A is marked MEETS for certification.",
    "Supplier A certification is evaluated as MEETS.",
    "According to the comparison Supplier A certification is MEETS.",
    "Supplier A GRS requirement is MEETS.",
    "Supplier A certification is MEETS whereas Supplier B does not meet it.",
    "Supplier A certification is MEETS. Its certification is MEETS.",
    "Supplier A (11111111-1111-1111-1111-111111111111) certification is MEETS.",
])
def test_semantic_repair_keeps_closed_grammar(text: str) -> None:
    from sourcepilot.ai.tradeoff_analysis_eval import fixture_snapshot

    snapshot = fixture_snapshot()
    assert snapshot.comparison_payload is not None
    output = semantic_repair_output(cast(dict[str, Any], snapshot.comparison_payload))
    validate_analysis(TradeoffAnalysis.model_validate(output), snapshot)
    output["supplier_summaries"][0]["text"] = text
    with pytest.raises(ValueError):
        validate_analysis(TradeoffAnalysis.model_validate(output), snapshot)
