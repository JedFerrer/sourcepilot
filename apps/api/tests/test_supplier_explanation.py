"""M2-U6 bounded analyst, grounded output, scope, and API tests."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from sourcepilot.ai.client import (
    AISettings,
    AnalystModelInvocation,
    ModelInvocation,
    ModelProviderError,
    OpenAIResponsesClient,
)
from sourcepilot.ai.supplier_explanation import (
    ExplanationNotReadyError,
    ExplanationUnavailableError,
    analyst_limits_from_environment,
    explain_supplier,
)
from sourcepilot.main import app
from sourcepilot.persistence.database import get_database_session
from sourcepilot.persistence.models import (
    AIRun,
    DemoSession,
    Project,
    ProjectSupplier,
    SupplierExplanationRunStep,
)
from sourcepilot.suppliers.seed import seed_suppliers
from tests.database_test_support import (
    create_test_engine,
    persistence_test_database_url_from_environment,
    reset_test_database,
)


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


def discovered(client: TestClient, engine: Engine) -> tuple[UUID, UUID, UUID]:
    created = client.post("/projects", json={
        "name": "Bags", "original_request": "Source cosmetic travel bags.",
    })
    assert created.status_code == 201
    project_id = UUID(created.json()["id"])
    edited = client.patch(f"/projects/{project_id}/brief", json={
        "product_name": "Cosmetic bag", "category": "cosmetic travel bag",
        "quantity": 2000, "destination": "Sydney",
        "delivery_target": {"kind": "DATE", "date": "2027-01-01"},
        "target_unit_price": None,
        "requirements": [
            {"kind": "MATERIAL", "importance": "REQUIRED",
             "expected_value": {"value": "recycled polyester"}},
            {"kind": "CERTIFICATION", "importance": "PREFERRED",
             "expected_value": {"value": "grs"}},
            {"kind": "CAPABILITY", "importance": "REQUIRED",
             "expected_value": {"capability_key": "CUSTOM_BRANDING", "value": True}},
        ],
    })
    assert edited.status_code == 200
    approved = client.post(f"/projects/{project_id}/brief/approve", json={
        "expected_brief_revision": edited.json()["brief_revision"],
    })
    assert approved.status_code == 200
    assert client.post(f"/projects/{project_id}/suppliers/discover").status_code == 200
    suppliers = client.get(f"/projects/{project_id}/suppliers").json()["suppliers"]
    supplier_id = UUID(next(
        item["id"] for item in suppliers
        if any(finding["evidence_ids"] for finding in item["evaluations"])
    ))
    with Session(engine) as session:
        project = session.get(Project, project_id)
        assert project is not None
        demo_session_id = project.demo_session_id
    return demo_session_id, project_id, supplier_id


def invocation(
    *, text: str = "", output_items: tuple[dict[str, object], ...] = (),
) -> AnalystModelInvocation:
    return AnalystModelInvocation(text, output_items, 10, 5)


def test_existing_provider_boundary_sends_tools_without_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class Output:
        def model_dump(self, **kwargs: object) -> dict[str, object]:
            return {"type": "function_call", "name": "get_supplier_evidence",
                    "call_id": "call-1", "arguments": "{}"}

    class Responses:
        def create(self, **kwargs: object) -> object:
            captured.update(kwargs)
            return type("Response", (), {
                "output_text": "", "output": [Output()], "usage": None,
            })()

    class FakeOpenAI:
        def __init__(self, *, api_key: str) -> None:
            self.responses = Responses()

    monkeypatch.setattr("sourcepilot.ai.client.OpenAI", FakeOpenAI)
    provider = OpenAIResponsesClient(AISettings(api_key="test-key", model="test-model"))
    response = provider.invoke_with_tools(
        instructions="Explain", input_items=[{"role": "user", "content": "supplier"}],
        tools=[{"type": "function", "name": "get_supplier_evidence"}],
        schema_name="SupplierExplanation", schema={"type": "object"},
    )
    assert captured["store"] is False
    assert captured["input"] == [{"role": "user", "content": "supplier"}]
    assert captured["tools"] == [{"type": "function", "name": "get_supplier_evidence"}]
    assert response.output_items[0]["call_id"] == "call-1"


def test_analyst_limits_are_configurable_and_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SOURCEPILOT_ANALYST_MAX_MODEL_TURNS", raising=False)
    monkeypatch.delenv("SOURCEPILOT_ANALYST_MAX_TOOL_CALLS", raising=False)
    assert analyst_limits_from_environment() == (4, 6)
    monkeypatch.setenv("SOURCEPILOT_ANALYST_MAX_MODEL_TURNS", "2")
    monkeypatch.setenv("SOURCEPILOT_ANALYST_MAX_TOOL_CALLS", "3")
    assert analyst_limits_from_environment() == (2, 3)
    monkeypatch.setenv("SOURCEPILOT_ANALYST_MAX_TOOL_CALLS", "0")
    with pytest.raises(RuntimeError, match="positive integer"):
        analyst_limits_from_environment()


def valid_payload(input_items: list[dict[str, object]], supplier_id: UUID) -> dict[str, object]:
    first = json.loads(str(input_items[0]["content"]))
    findings = first["snapshot"]["evaluations"]
    sections: dict[str, list[dict[str, object]]] = {
        name: [] for name in (
            "strengths", "required_failures", "preferred_findings", "unknowns", "conflicts", "concerns"
        )
    }
    cited: set[str] = set()
    for finding in findings:
        if finding["status"] == "UNKNOWN":
            section = "unknowns"
        elif finding["status"] == "CONFLICT":
            section = "conflicts"
        elif finding["status"] == "DOES_NOT_MEET" and finding["importance"] == "REQUIRED":
            section = "required_failures"
        elif finding["importance"] == "PREFERRED":
            section = "preferred_findings"
        elif finding["status"] == "MEETS":
            section = "strengths"
        else:
            continue
        ids = finding["evidence_ids"]
        cited.update(ids)
        sections[section].append({
            "text": None,
            "requirement_id": finding["requirement_id"], "evidence_ids": ids,
        })
    return {"supplier_id": str(supplier_id), **sections, "evidence_ids": sorted(cited)}


class FakeClient:
    model = "test-model"

    def __init__(
        self, supplier_id: UUID, *, invalid_first: bool = False,
        on_final: Callable[[], None] | None = None,
        provider_first: bool = False,
    ) -> None:
        self.supplier_id = supplier_id
        self.invalid_first = invalid_first
        self.on_final = on_final
        self.provider_first = provider_first
        self.calls = 0

    def invoke(self, **kwargs: object) -> ModelInvocation:
        raise AssertionError("Analyst must use the existing tool-capable provider method.")

    def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
        self.calls += 1
        if self.provider_first and self.calls == 1:
            raise ModelProviderError("temporary", retryable=True)
        input_items = kwargs["input_items"]
        assert isinstance(input_items, list)
        if not any(item.get("type") == "function_call_output" for item in input_items):
            return invocation(output_items=({
                "type": "function_call", "call_id": "evidence-call",
                "name": "get_supplier_evidence",
                "arguments": json.dumps({
                    "supplier_id": str(self.supplier_id), "claim_keys": None,
                }),
            },))
        payload = valid_payload(input_items, self.supplier_id)
        if self.invalid_first and self.calls == 2:
            payload["evidence_ids"] = [str(uuid4())]
        elif self.on_final is not None:
            self.on_final()
        return invocation(text=json.dumps(payload))


def test_grounded_success_persists_ordered_steps_and_run_id(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.test_ai_tracing import Observation

    calls = []
    monkeypatch.setattr("sourcepilot.ai.tracing.langfuse_client", lambda: Observation(calls))
    demo_session_id, project_id, supplier_id = discovered(client, engine)
    with Session(engine) as session:
        result = explain_supplier(
            session, demo_session_id=demo_session_id, project_id=project_id,
            supplier_id=supplier_id, client_factory=lambda: FakeClient(supplier_id),
        )
    with Session(engine) as session:
        run = session.get(AIRun, result.run_id)
        steps = list(session.scalars(select(SupplierExplanationRunStep).where(
            SupplierExplanationRunStep.air_run_id == result.run_id
        ).order_by(SupplierExplanationRunStep.sequence)))
    assert run is not None and run.status == "COMPLETED"
    assert run.model_turn_count == 2 and run.tool_call_count == 2
    assert [(step.sequence, step.kind, step.outcome) for step in steps] == [
        (1, "tool", "SUCCESS"), (2, "model", "TOOL_CALLS"), (3, "tool", "SUCCESS"),
        (4, "model", "FINAL"), (5, "validation", "VALID"),
        (6, "usage", "COMPLETE"), (7, "usage", "COMPLETE"), (8, "run", "COMPLETED"),
    ]
    assert (run.input_tokens, run.output_tokens) == (20, 10)
    assert any(call.get("name") == "supplier_explanation" for call in calls)
    assert sum("usage_details" in call for call in calls) == 2
    assert result.explanation.supplier_id == supplier_id
    assert result.explanation.evidence_ids
    suppliers = client.get(f"/projects/{project_id}/suppliers").json()["suppliers"]
    supplier = next(item for item in suppliers if item["id"] == str(supplier_id))
    statuses = {
        finding["requirement_id"]: finding["status"].replace("_", " ").title()
        for finding in supplier["evaluations"]
    }
    for section in (
        result.explanation.strengths, result.explanation.required_failures,
        result.explanation.preferred_findings, result.explanation.unknowns,
        result.explanation.conflicts, result.explanation.concerns,
    ):
        for point in section:
            if point.requirement_id is not None:
                assert point.text.endswith(f": {statuses[str(point.requirement_id)]}.")


def test_current_candidate_without_evaluable_requirements_can_be_explained(
    client: TestClient, engine: Engine,
) -> None:
    demo_session_id, project_id, supplier_id = discovered(client, engine)
    with Session(engine) as session:
        candidate = session.get(ProjectSupplier, (project_id, supplier_id))
        assert candidate is not None
        candidate.evaluations.clear()
        session.commit()
    with Session(engine) as session:
        result = explain_supplier(
            session, demo_session_id=demo_session_id, project_id=project_id,
            supplier_id=supplier_id, client_factory=lambda: FakeClient(supplier_id),
        )
    assert result.explanation.strengths == []
    assert result.explanation.unknowns == []


def test_model_and_tool_limits_fail_only_when_they_prevent_completion(
    client: TestClient, engine: Engine,
) -> None:
    demo_session_id, project_id, supplier_id = discovered(client, engine)
    for max_model_turns, max_tool_calls in ((1, 6), (4, 1)):
        with Session(engine) as session, pytest.raises(ExplanationUnavailableError):
            explain_supplier(
                session, demo_session_id=demo_session_id, project_id=project_id,
                supplier_id=supplier_id, client_factory=lambda: FakeClient(supplier_id),
                max_model_turns=max_model_turns, max_tool_calls=max_tool_calls,
            )
        with Session(engine) as session:
            run = session.scalar(select(AIRun).order_by(AIRun.started_at.desc(), AIRun.id.desc()))
            assert run is not None and run.status == "FAILED_LIMIT_REACHED"


def test_success_at_the_exact_six_call_budget(
    client: TestClient, engine: Engine,
) -> None:
    demo_session_id, project_id, supplier_id = discovered(client, engine)

    class ExactBudgetClient(FakeClient):
        def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
            input_items = kwargs["input_items"]
            assert isinstance(input_items, list)
            if not any(item.get("type") == "function_call_output" for item in input_items):
                return invocation(output_items=tuple({
                    "type": "function_call", "call_id": f"call-{index}",
                    "name": "get_supplier_evidence" if index == 4 else "get_supplier_snapshot",
                    "arguments": json.dumps({
                        "supplier_id": str(supplier_id),
                        **({"claim_keys": None} if index == 4 else {}),
                    }),
                } for index in range(5)))
            return invocation(text=json.dumps(valid_payload(input_items, supplier_id)))

    with Session(engine) as session:
        result = explain_supplier(
            session, demo_session_id=demo_session_id, project_id=project_id,
            supplier_id=supplier_id, client_factory=lambda: ExactBudgetClient(supplier_id),
        )
    with Session(engine) as session:
        run = session.get(AIRun, result.run_id)
        assert run is not None and run.status == "COMPLETED"
        assert run.tool_call_count == 6 and run.model_turn_count == 2


def test_repair_and_provider_retry_each_consume_a_model_turn(
    client: TestClient, engine: Engine,
) -> None:
    demo_session_id, project_id, supplier_id = discovered(client, engine)
    for fake in (
        FakeClient(supplier_id, invalid_first=True),
        FakeClient(supplier_id, provider_first=True),
    ):
        with Session(engine) as session:
            result = explain_supplier(
                session, demo_session_id=demo_session_id, project_id=project_id,
                supplier_id=supplier_id, client_factory=lambda fake=fake: fake,
                sleep=lambda _: None,
            )
        with Session(engine) as session:
            run = session.get(AIRun, result.run_id)
            assert run is not None and run.model_turn_count == 3


def test_provider_and_contract_failures_do_not_claim_a_runtime_limit(
    client: TestClient, engine: Engine,
) -> None:
    demo_session_id, project_id, supplier_id = discovered(client, engine)

    class AlwaysProviderFailure(FakeClient):
        def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
            raise ModelProviderError("temporary", retryable=True)

    class AlwaysInvalidOutput(FakeClient):
        def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
            output = super().invoke_with_tools(**kwargs)
            if output.output_text:
                payload = json.loads(output.output_text)
                payload["supplier_id"] = str(uuid4())
                return invocation(text=json.dumps(payload))
            return output

    for fake, status in (
        (AlwaysProviderFailure(supplier_id), "PROVIDER_FAILED"),
        (AlwaysInvalidOutput(supplier_id), "VALIDATION_FAILED"),
    ):
        with Session(engine) as session, pytest.raises(ExplanationUnavailableError):
            explain_supplier(
                session, demo_session_id=demo_session_id, project_id=project_id,
                supplier_id=supplier_id, client_factory=lambda fake=fake: fake,
                sleep=lambda _: None,
            )
        with Session(engine) as session:
            run = session.scalar(select(AIRun).order_by(AIRun.started_at.desc(), AIRun.id.desc()))
            assert run is not None and run.status == status
            assert run.model_turn_count in {2, 3}


def test_only_two_read_only_supplier_tools_are_exposed() -> None:
    from sourcepilot.ai.supplier_explanation import TOOLS

    assert {tool["name"] for tool in TOOLS} == {
        "get_supplier_snapshot", "get_supplier_evidence",
    }


@pytest.mark.parametrize("forgery", ["supplier", "project_id", "demo_session_id"])
def test_model_cannot_call_a_supplier_outside_its_immutable_scope(
    client: TestClient, engine: Engine, forgery: str,
) -> None:
    demo_session_id, project_id, supplier_id = discovered(client, engine)

    class WrongSupplierClient(FakeClient):
        def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
            return invocation(output_items=({
                "type": "function_call", "call_id": "cross-scope",
                "name": "get_supplier_evidence",
                "arguments": json.dumps({"supplier_id": str(uuid4()) if forgery == "supplier" else str(supplier_id),
                                         "claim_keys": None,
                                         **({forgery: str(uuid4())} if forgery != "supplier" else {})}),
            },))

    with Session(engine) as session, pytest.raises(ExplanationUnavailableError):
        explain_supplier(
            session, demo_session_id=demo_session_id, project_id=project_id,
            supplier_id=supplier_id,
            client_factory=lambda: WrongSupplierClient(supplier_id),
        )
    with Session(engine) as session:
        run = session.scalar(select(AIRun).order_by(AIRun.started_at.desc(), AIRun.id.desc()))
        assert run is not None and run.status == "VALIDATION_FAILED"
        assert run.tool_call_count == 1  # Only the application-scoped preflight snapshot succeeded.


@pytest.mark.parametrize("change", ["expire", "remove", "stale"])
def test_changed_authorization_blocks_final_result(
    client: TestClient, engine: Engine, change: str,
) -> None:
    demo_session_id, project_id, supplier_id = discovered(client, engine)

    def change_scope() -> None:
        with Session(engine) as other:
            if change == "expire":
                demo = other.get(DemoSession, demo_session_id)
                assert demo is not None
                demo.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            elif change == "remove":
                candidate = other.get(ProjectSupplier, (project_id, supplier_id))
                assert candidate is not None
                other.delete(candidate)
            else:
                project = other.get(Project, project_id)
                assert project is not None
                project.brief_revision += 1
            other.commit()

    with Session(engine) as session, pytest.raises(ExplanationNotReadyError):
        explain_supplier(
            session, demo_session_id=demo_session_id, project_id=project_id,
            supplier_id=supplier_id,
            client_factory=lambda: FakeClient(supplier_id, on_final=change_scope),
        )
    with Session(engine) as session:
        run = session.scalar(select(AIRun).order_by(AIRun.started_at.desc(), AIRun.id.desc()))
        assert run is not None and run.status == "FAILED" and run.error_type == "SCOPE_CHANGED"


def test_api_enforces_scope_and_staleness(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, project_id, supplier_id = discovered(client, engine)
    monkeypatch.setattr(
        "sourcepilot.main.OpenAIResponsesClient.from_environment",
        lambda: FakeClient(supplier_id),
    )
    endpoint = f"/projects/{project_id}/suppliers/{supplier_id}/explanation"
    assert client.post(endpoint).status_code == 200
    assert client.post(f"/projects/{project_id}/suppliers/{uuid4()}/explanation").status_code == 404
    with TestClient(app, raise_server_exceptions=False) as other:
        assert other.post("/demo-session").status_code == 204
        assert other.post(endpoint).status_code == 404
    with Session(engine) as session:
        project = session.get(Project, project_id)
        assert project is not None
        project.brief_revision += 1
        session.commit()
    stale = client.post(endpoint)
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "SUPPLIER_EVALUATION_STALE"


@pytest.mark.parametrize("state", ["MEETS", "UNKNOWN", "CONFLICT"])
@pytest.mark.parametrize("repair", ["fetch", "strip", "unfetched", "no_lookup"])
def test_evidence_selection_and_repair_preserve_citation_guards(
    client: TestClient, engine: Engine, state: str, repair: str,
) -> None:
    from sourcepilot.ai.supplier_explanation import INSTRUCTIONS, PROMPT_VERSION, TOOLS

    demo_session_id, project_id, _ = discovered(client, engine)
    suppliers = client.get(f"/projects/{project_id}/suppliers").json()["suppliers"]
    supplier = next(item for item in suppliers if
                    any(f["status"] == state for f in item["evaluations"])
                    and any(f["evidence_ids"] for f in item["evaluations"]))
    supplier_id = UUID(supplier["id"])
    errors: list[str] = []

    class SelectionClient(FakeClient):
        def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
            self.calls += 1
            assert kwargs["tools"] == TOOLS
            assert str(kwargs["instructions"]).startswith(INSTRUCTIONS)
            items = kwargs["input_items"]
            assert isinstance(items, list)
            first = json.loads(str(items[0]["content"]))
            if self.calls == 1 and repair != "no_lookup":
                # Historical misuse: valid argument strings select no catalog claims.
                keys = [f["requirement_id"] for f in first["snapshot"]["evaluations"]]
            elif self.calls == 3 and repair == "fetch":
                errors.append(str(kwargs["instructions"]))
                keys = None
            else:
                outputs = [json.loads(item["output"]) for item in items
                           if item.get("type") == "function_call_output"]
                if repair != "no_lookup":
                    assert outputs[0]["evidence"] == []
                payload = json.loads(json.dumps(valid_payload(items, supplier_id)))
                assert payload["evidence_ids"]  # IDs in the snapshot are real but unfetched.
                if self.calls == 3 or (repair == "no_lookup" and self.calls == 2):
                    errors.append(str(kwargs["instructions"]))
                if self.calls == 3 and repair == "strip":
                    for section in ("strengths", "required_failures", "preferred_findings",
                                    "unknowns", "conflicts", "concerns"):
                        for point in payload[section]:
                            point["evidence_ids"] = []
                    payload["evidence_ids"] = []
                if self.calls == 4:
                    fetched = {e["id"] for e in outputs[-1]["evidence"]}
                    assert set(payload["evidence_ids"]).issubset(fetched)
                return invocation(text=json.dumps(payload))
            return invocation(output_items=({
                "type": "function_call", "call_id": f"evidence-{self.calls}",
                "name": "get_supplier_evidence", "arguments": json.dumps({
                    "supplier_id": str(supplier_id), "claim_keys": keys,
                }),
            },))

    fake = SelectionClient(supplier_id)
    with Session(engine) as session:
        if repair == "fetch":
            result = explain_supplier(
                session, demo_session_id=demo_session_id, project_id=project_id,
                supplier_id=supplier_id, client_factory=lambda: fake,
            )
            for section, status in (("unknowns", "UNKNOWN"), ("conflicts", "CONFLICT")):
                points = getattr(result.explanation, section)
                assert {str(p.requirement_id) for p in points} == {
                    f["requirement_id"] for f in supplier["evaluations"] if f["status"] == status
                }
                for point in points:
                    assert point.text.endswith(f": {status.title()}.")
            assert result.explanation.evidence_ids
        else:
            with pytest.raises(ExplanationUnavailableError):
                explain_supplier(
                    session, demo_session_id=demo_session_id, project_id=project_id,
                    supplier_id=supplier_id, client_factory=lambda: fake,
                )
    assert len(errors) == 1
    assert "The previous result failed semantic validation." in errors[0]
    with Session(engine) as session:
        run = session.scalar(select(AIRun).order_by(AIRun.started_at.desc(), AIRun.id.desc()))
        assert run is not None and run.prompt_version == PROMPT_VERSION == "supplier-explanation-v3"
        assert run.status == ("COMPLETED" if repair == "fetch" else "VALIDATION_FAILED")
        assert run.validation_status == ("REPAIRED" if repair == "fetch" else "INVALID")
        assert run.model_turn_count == (4 if repair == "fetch" else
                                        2 if repair == "no_lookup" else 3)
        assert run.tool_call_count == (3 if repair == "fetch" else
                                      1 if repair == "no_lookup" else 2)
        steps = list(session.scalars(select(SupplierExplanationRunStep).where(
            SupplierExplanationRunStep.air_run_id == run.id
        )))
        assert sum(s.kind == "retry" and s.outcome == "REPAIR" for s in steps) == 1
        assert sum(s.kind == "validation" and s.outcome == "INVALID" for s in steps) == (
            1 if repair == "fetch" else 2
        )


def test_evidence_prompt_explains_selection_and_repair() -> None:
    from sourcepilot.ai.supplier_explanation import INSTRUCTIONS, TOOLS

    description = next(t["description"] for t in TOOLS if t["name"] == "get_supplier_evidence")
    for guidance in (INSTRUCTIONS, description):
        assert "catalog claim keys" in guidance
        assert "not requirement UUIDs or" in guidance
        assert "evidence IDs" in guidance
        assert "claim_keys=null when exact keys" in guidance
    assert "before citing evidence or finalizing" in INSTRUCTIONS
    assert "do not remove required citations" in INSTRUCTIONS


@pytest.mark.parametrize("schema_failure", [False, True])
def test_analyst_repair_does_not_promote_rejected_values(
    client: TestClient, engine: Engine, schema_failure: bool,
) -> None:
    demo_session_id, project_id, supplier_id = discovered(client, engine)
    sentinel = "ATTACKER_REPAIR_SENTINEL"
    class MaliciousModel(FakeClient):
        def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
            assert sentinel not in str(kwargs["instructions"])
            output = super().invoke_with_tools(**kwargs)
            if self.calls == 2:
                payload = json.loads(output.output_text)
                if schema_failure:
                    payload[sentinel] = sentinel
                else:
                    payload["strengths"][0]["text"] = "Supplier score: 92 " + sentinel
                return invocation(text=json.dumps(payload))
            if self.calls == 3:
                assert ("schema validation" if schema_failure else "semantic validation") in str(kwargs["instructions"])
            return output
    model = MaliciousModel(supplier_id)
    with Session(engine) as session:
        result = explain_supplier(session, demo_session_id=demo_session_id, project_id=project_id,
                                  supplier_id=supplier_id, client_factory=lambda: model)
        run = session.get(AIRun, result.run_id)
        assert run is not None and run.validation_status == "REPAIRED" and run.model_turn_count == 3
