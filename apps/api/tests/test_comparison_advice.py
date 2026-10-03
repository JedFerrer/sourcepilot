"""Combined advice API, scope, tracing, stale outcomes and structural validation."""

# ruff: noqa: F811 -- pytest fixtures are intentionally imported and injected by name.

import json
from copy import deepcopy
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from sourcepilot.ai.client import AnalystModelInvocation
from sourcepilot.ai.comparison_advice import (
    INSTRUCTIONS,
    PROMPT_VERSION,
    ComparisonAdvice,
    analyze_comparison_advice,
    validate_advice,
)
from sourcepilot.ai.structured import structured_input_hash
from sourcepilot.ai.tradeoff_analysis import TradeoffNotReadyError, TradeoffUnavailableError
from sourcepilot.ai.tradeoff_analysis_eval import CERT, PDF_PRICE, A, B, fixture_snapshot
from sourcepilot.comparison.advice import (
    QuoteFieldReference,
    SuggestedSupplierResult,
    validate_suggestion,
)
from sourcepilot.persistence.models import (
    AIRun,
    Comparison,
    Project,
    ProjectSupplier,
    Quote,
    SupplierExplanationRunStep,
)
from tests.test_tradeoff_analysis import (
    FakeModel,
    client,  # noqa: F401
    database_url,  # noqa: F401
    engine,  # noqa: F401
    ready,
    valid_output,
)


def suggestion(payload: dict[str, Any], selected: str | None = None) -> dict[str, Any]:
    owner = selected or payload["suppliers"][0]["supplier_id"]
    point = {"text": "Confirmed quote facts support further investigation.",
             "supplier_ids": [owner], "requirement_ids": [], "quote_fields": [], "evidence_ids": []}
    tradeoffs, uncertainties = [], []
    for supplier in payload["suppliers"]:
        if supplier["supplier_id"] != owner:
            continue
        for finding in supplier["evaluation"]["results"]:
            if finding["requirement_id"] is None or finding["status"] == "MEETS":
                continue
            item = {**point, "text": f"The requirement state is {finding['status']}.",
                    "requirement_ids": [finding["requirement_id"]]}
            (tradeoffs if finding["status"] == "DOES_NOT_MEET" else uncertainties).append(item)
    if selected is None:
        uncertainties.append({**point, "text": "There is no justified single supplier to suggest yet."})
    return {"supplier_id": selected, "supporting_reasons": [point] if selected else [],
            "tradeoffs": tradeoffs, "uncertainties": uncertainties, "evidence_ids": []}


class AdviceModel(FakeModel):
    def __init__(self, *, selected: bool = False, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.selected = selected

    def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
        self.last_schema = kwargs["schema_name"]
        self.last_instructions = kwargs["instructions"]
        result = super().invoke_with_tools(**kwargs)
        if result.output_items or result.output_text == "{}":
            return result
        payload = self.inputs[-1]["comparison_payload"]
        selected = payload["suppliers"][0]["supplier_id"] if self.selected else None
        return AnalystModelInvocation(json.dumps({"analysis": json.loads(result.output_text),
                                                  "suggestion": suggestion(payload, selected)}), (), 2, 1)


def test_structural_suggestion_validation() -> None:
    snapshot = fixture_snapshot()
    assert snapshot.comparison_payload is not None
    payload = cast(dict[str, Any], snapshot.comparison_payload)
    valid = SuggestedSupplierResult.model_validate(suggestion(payload, B))
    validate_suggestion(valid, payload)  # Required failure is disclosed, not excluded.
    validate_suggestion(SuggestedSupplierResult.model_validate(suggestion(payload)), payload)
    for change, message in [
        ({"supplier_id": uuid4()}, "outside"),
        ({"supporting_reasons": []}, "supporting"),
        ({"tradeoffs": []}, "omits"),
        ({"evidence_ids": [uuid4()]}, "unknown evidence"),
    ]:
        with pytest.raises(ValueError, match=message):
            validate_suggestion(valid.model_copy(update=change), payload)
    conflict = valid.model_copy(deep=True)
    conflict.supporting_reasons[0].requirement_ids = [UUID(CERT)]
    with pytest.raises(ValueError, match="contradicts"):
        validate_suggestion(conflict, payload)
    unknown = SuggestedSupplierResult.model_validate(suggestion(payload, payload["suppliers"][2]["supplier_id"]))
    unknown.uncertainties.clear()
    with pytest.raises(ValueError, match="omits"):
        validate_suggestion(unknown, payload)
    for mutation in ("supplier", "requirement", "quote", "evidence", "coverage", "blank"):
        changed = valid.model_copy(deep=True)
        point = changed.supporting_reasons[0]
        if mutation == "supplier":
            point.supplier_ids = [uuid4()]
        elif mutation == "requirement":
            point.requirement_ids = [uuid4()]
        elif mutation == "quote":
            point.quote_fields = [QuoteFieldReference(quote_id=uuid4(), field_key="unit_price")]
        elif mutation == "evidence":
            point.evidence_ids = [UUID(PDF_PRICE)]  # A's evidence cannot support B.
            changed.evidence_ids = [UUID(PDF_PRICE)]
        elif mutation == "coverage":
            point.supplier_ids.append(UUID(A))
            point.evidence_ids = [UUID(PDF_PRICE)]
        else:
            point.text = " "
        with pytest.raises(ValueError):
            validate_suggestion(changed, payload)
    no_result = SuggestedSupplierResult.model_validate(suggestion(payload))
    no_result.uncertainties.clear()
    with pytest.raises(ValueError, match="explanation"):
        validate_suggestion(no_result, payload)
    # Structural validation deliberately does not interpret arbitrary prose.
    valid.supporting_reasons[0].text = "Advisory interpretation without a prose parser."
    validate_suggestion(valid, payload)


def test_contract_and_existing_analysis_validation() -> None:
    snapshot = fixture_snapshot()
    assert snapshot.comparison_payload is not None
    output = {"analysis": valid_output(snapshot.comparison_payload),
              "suggestion": suggestion(snapshot.comparison_payload, A)}
    validate_advice(ComparisonAdvice.model_validate(output), snapshot)
    bad = deepcopy(output)
    bad["analysis"]["important_unknowns"] = []
    with pytest.raises(ValueError, match="omits"):
        validate_advice(ComparisonAdvice.model_validate(bad), snapshot)
    with pytest.raises(ValueError):
        ComparisonAdvice.model_validate({**output, "preferred_supplier_id": A})


def invoke(session: Session, project: Project, snapshot_id: UUID, model: AdviceModel,
           **limits: int) -> Any:
    return analyze_comparison_advice(
        session, demo_session_id=project.demo_session_id, project_id=project.id,
        snapshot_id=snapshot_id, client_factory=lambda: model, sleep=lambda _: None, **limits,
    )


@pytest.mark.parametrize("selected", [False, True])
def test_combined_success_trace_and_hash(client: TestClient, engine: Engine, selected: bool) -> None:
    project_id, _, _ = ready(client)
    snapshot_id = UUID(client.get(f"/projects/{project_id}/comparison").json()["id"])
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        model = AdviceModel(selected=selected, actions=["tool", "invalid", "final"])
        result = invoke(session, project, snapshot_id, model)
        run = session.get(AIRun, result.run_id)
        assert run is not None
        assert (run.operation, run.prompt_version, run.validation_status) == (
            "comparison_advice", PROMPT_VERSION, "REPAIRED")
        assert (run.model_turn_count, run.tool_call_count, run.status) == (3, 1, "COMPLETED")
        assert run.input_hash == structured_input_hash(
            instructions=INSTRUCTIONS, input_text=json.dumps(model.inputs[0], sort_keys=True))
        steps = session.scalars(select(SupplierExplanationRunStep).where(
            SupplierExplanationRunStep.air_run_id == result.run_id).order_by(SupplierExplanationRunStep.sequence)).all()
        assert [(s.kind, s.outcome) for s in steps][-1] == ("run", "COMPLETED")
        assert ("retry", "REPAIR") in [(s.kind, s.outcome) for s in steps]
        assert ("scope", "CURRENT") in [(s.kind, s.outcome) for s in steps]
        assert (result.suggestion.supplier_id is not None) == selected
        assert result.snapshot_id == snapshot_id
        assert model.last_schema == "ComparisonAdviceV1"
        assert str(model.last_instructions).startswith(INSTRUCTIONS)


@pytest.mark.parametrize("actions,limits,status", [
    (["provider", "provider"], {}, "PROVIDER_FAILED"),
    (["invalid", "invalid"], {}, "VALIDATION_FAILED"),
    (["tool", "tool"], {"max_model_turns": 1}, "FAILED_LIMIT_REACHED"),
    (["tool", "tool"], {"max_tool_calls": 1}, "FAILED_LIMIT_REACHED"),
    (["foreign_quote"], {}, "VALIDATION_FAILED"),
])
@pytest.mark.parametrize("change", [False, True])
def test_terminal_failure_and_freshness_precedence(
    client: TestClient, engine: Engine, actions: list[str], limits: dict[str, int], status: str, change: bool,
) -> None:
    project_id, _, quote_ids = ready(client)
    snapshot_id = UUID(client.get(f"/projects/{project_id}/comparison").json()["id"])
    def mutate(turn: int) -> None:
        if change and turn == 1:
            with Session(engine) as writer:
                quote = writer.get(Quote, UUID(quote_ids[0]))
                assert quote is not None
                quote.revision += 1
                writer.commit()
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        with pytest.raises(TradeoffNotReadyError if change else TradeoffUnavailableError) as raised:
            invoke(session, project, snapshot_id, AdviceModel(actions=actions.copy(), on_invoke=mutate), **limits)
        if change:
            assert raised.value.code == "COMPARISON_STALE"  # type: ignore[attr-defined]
        run = session.scalars(select(AIRun)).one()
        assert run.status == ("FAILED" if change else status)
        if change:
            assert run.error_type == "COMPARISON_STALE"


@pytest.mark.parametrize("change", ["membership", "brief", "replacement", "quote"])
def test_final_freshness_and_membership(client: TestClient, engine: Engine, change: str) -> None:
    project_id, supplier_ids, quote_ids = ready(client)
    snapshot_id = UUID(client.get(f"/projects/{project_id}/comparison").json()["id"])
    def mutate() -> None:
        with Session(engine) as writer:
            if change == "membership":
                row = writer.get(ProjectSupplier, (UUID(project_id), UUID(supplier_ids[0])))
                assert row is not None
                row.shortlisted = False  # No new staleness flag or revision is needed.
            elif change == "brief":
                project = writer.get(Project, UUID(project_id))
                assert project is not None
                project.brief_revision += 1
            elif change == "replacement":
                old = writer.get(Comparison, snapshot_id)
                assert old is not None
                writer.add(Comparison(project_id=old.project_id, brief_revision=old.brief_revision,
                                      quote_revision_snapshot=old.quote_revision_snapshot,
                                      comparison_payload=old.comparison_payload, stale=False))
            else:
                quote = writer.get(Quote, UUID(quote_ids[0]))
                assert quote is not None
                quote.revision += 1
            writer.commit()
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        with pytest.raises(TradeoffNotReadyError) as raised:
            invoke(session, project, snapshot_id, AdviceModel(on_final=mutate))
        assert raised.value.code == "COMPARISON_STALE"


def test_api_preconditions_isolation_and_success(client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    project_id, _, _ = ready(client)
    path = f"/projects/{project_id}/comparison/advice"
    snapshot_id = client.get(f"/projects/{project_id}/comparison").json()["id"]
    model = AdviceModel()
    monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", lambda: model)
    assert client.post(path, json={"snapshot_id": str(uuid4())}).json()["error"]["code"] == "COMPARISON_STALE"
    assert model.calls == 0
    response = client.post(path, json={"snapshot_id": snapshot_id})
    assert response.status_code == 200 and response.json()["suggestion"]["supplier_id"] is None
    with Session(engine) as writer:
        row = writer.get(Comparison, UUID(snapshot_id))
        assert row is not None
        row.stale = True
        writer.commit()
    assert client.post(path, json={"snapshot_id": snapshot_id}).status_code == 409
    assert model.calls == 1
    regenerated = client.post(f"/projects/{project_id}/comparison/generate").json()["id"]
    assert regenerated != snapshot_id
    assert client.post(path, json={"snapshot_id": regenerated}).status_code == 200
    assert model.inputs[-1]["snapshot_id"] == regenerated
    client.cookies.clear()
    assert client.post("/demo-session").status_code == 204
    assert client.post(path, json={"snapshot_id": regenerated}).status_code == 404


def test_missing_comparison_and_unavailable_api(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.test_comparison_snapshot import setup_project
    project_id, _ = setup_project(client)
    path = f"/projects/{project_id}/comparison/advice"
    assert client.post(path, json={"snapshot_id": str(uuid4())}).json()["error"]["code"] == "COMPARISON_NOT_FOUND"
    project_id, _, _ = ready(client)
    snapshot_id = client.get(f"/projects/{project_id}/comparison").json()["id"]
    monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", lambda: AdviceModel(actions=["invalid", "invalid"]))
    response = client.post(f"/projects/{project_id}/comparison/advice", json={"snapshot_id": snapshot_id})
    assert response.status_code == 503 and response.json()["error"]["code"] == "COMPARISON_ADVICE_UNAVAILABLE"


def test_membership_rejection_before_provider(client: TestClient, engine: Engine) -> None:
    project_id, supplier_ids, _ = ready(client)
    snapshot_id = UUID(client.get(f"/projects/{project_id}/comparison").json()["id"])
    with Session(engine) as writer:
        row = writer.get(ProjectSupplier, (UUID(project_id), UUID(supplier_ids[0])))
        assert row is not None
        row.dismissed = True
        writer.commit()
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        model = AdviceModel()
        with pytest.raises(TradeoffNotReadyError) as raised:
            invoke(session, project, snapshot_id, model)
        assert raised.value.code == "COMPARISON_STALE"
        assert model.calls == 0 and session.scalar(select(AIRun.id)) is None
