"""M1-U5 contract, AI, API, and Brief edit regression coverage."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import ClassVar

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from sourcepilot.ai.clarification import ClarificationSet, validate_field_coverage
from sourcepilot.ai.client import ModelInvocation, ModelProviderError
from sourcepilot.main import app
from sourcepilot.persistence.database import get_database_session
from sourcepilot.persistence.models import AIRun, Brief, Project, Requirement
from tests.database_test_support import (
    create_test_engine,
    persistence_test_database_url_from_environment,
    reset_test_database,
)


class FakeClient:
    model = "test-model"
    calls = 0
    requests: ClassVar[list[dict[str, object]]] = []
    outputs: ClassVar[list[str | Exception]] = []
    callbacks: ClassVar[list[Callable[[], None]]] = []

    def invoke(self, **kwargs: object) -> ModelInvocation:
        FakeClient.calls += 1
        FakeClient.requests.append(kwargs)
        if FakeClient.callbacks:
            FakeClient.callbacks[0]()
        output = FakeClient.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return ModelInvocation(output_text=output, input_tokens=10, output_tokens=20)


def questions(*keys: str) -> str:
    return json.dumps(
        {"questions": [
            {"field_key": key, "question": f"What is the {key}?", "reason": "Needed for sourcing."}
            for key in keys
        ]}
    )


def edit(**changes: object) -> dict[str, object]:
    return {
        "product_name": "Cosmetic bag",
        "category": "Cosmetic bags",
        "quantity": 1000,
        "destination": "Sydney",
        "delivery_target": None,
        "target_unit_price": None,
        "requirements": [],
        **changes,
    }


def test_contract_rejects_invalid_structure_and_checks_exact_keys() -> None:
    with pytest.raises(ValidationError):
        ClarificationSet.model_validate_json(questions(""))
    with pytest.raises(ValidationError):
        ClarificationSet.model_validate({"questions": [
            {"field_key": "quantity", "question": "x" * 201, "reason": "Needed"}
        ]})
    with pytest.raises(ValidationError):
        ClarificationSet.model_validate({"questions": []})
    with pytest.raises(ValidationError):
        ClarificationSet.model_validate_json(questions(*(["quantity"] * 6)))
    with pytest.raises(ValidationError):
        ClarificationSet.model_validate({"questions": [
            {"field_key": "quantity", "question": "How many?", "reason": " "}
        ]})
    with pytest.raises(ValueError, match="unique"):
        validate_field_coverage(ClarificationSet.model_validate_json(questions("quantity", "quantity")), {"quantity"})
    with pytest.raises(ValueError, match="exactly match"):
        validate_field_coverage(ClarificationSet.model_validate_json(questions("quantity")), {"quantity", "destination"})
    with pytest.raises(ValueError, match="exactly match"):
        validate_field_coverage(ClarificationSet.model_validate_json(questions("target_unit_price")), {"quantity"})


@pytest.fixture(scope="module")
def database_url() -> str:
    return persistence_test_database_url_from_environment()


@pytest.fixture(scope="module")
def engine(database_url: str) -> Iterator[Engine]:
    value = create_test_engine(database_url)
    yield value
    value.dispose()


@pytest.fixture(autouse=True)
def reset_database(database_url: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    reset_test_database(database_url)
    FakeClient.calls = 0
    FakeClient.requests = []
    FakeClient.outputs = []
    FakeClient.callbacks = []
    monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", FakeClient)
    yield
    reset_test_database(database_url)


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_database_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_database_session] = override_database_session
    with TestClient(app, raise_server_exceptions=False) as value:
        yield value
    app.dependency_overrides.clear()


def create_project(client: TestClient) -> str:
    assert client.post("/demo-session").status_code == 204
    response = client.post("/projects", json={"name": "Bags", "original_request": "Source bags."})
    assert response.status_code == 201
    return response.json()["id"]


def test_generation_uses_readiness_without_mutating_brief(client: TestClient, engine: Engine) -> None:
    project_id = create_project(client)
    endpoint = f"/projects/{project_id}/brief/clarifications"
    assert client.post(endpoint).status_code == 409
    assert FakeClient.calls == 0
    saved = client.patch(f"/projects/{project_id}/brief", json=edit()).json()
    FakeClient.outputs = [questions("delivery_target", "requirement.material", "requirement.custom_branding")]
    response = client.post(endpoint)
    assert response.status_code == 200, response.text
    assert response.json()["brief_revision"] == saved["brief_revision"]
    assert [item["field_key"] for item in response.json()["questions"]] == [
        "delivery_target", "requirement.material", "requirement.custom_branding"
    ]
    model_input = json.loads(str(FakeClient.requests[0]["input_text"]))
    assert model_input["brief"]["destination"] == "Sydney"
    assert [item["field_key"] for item in model_input["unresolved_fields"]] == [
        "delivery_target", "requirement.material", "requirement.custom_branding"
    ]
    with Session(engine) as session:
        assert session.get(Brief, project_id).delivery_target is None  # type: ignore[union-attr]
        assert session.scalars(select(Requirement).where(Requirement.project_id == project_id)).all() == []
        assert session.get(Project, project_id).brief_revision == saved["brief_revision"]  # type: ignore[union-attr]
        run = session.scalars(select(AIRun).where(AIRun.project_id == project_id)).one()
        assert (run.operation, run.status, run.attempts, run.validation_status) == (
            "clarification_generator", "COMPLETED", 1, "VALID"
        )


def test_invalid_field_keys_get_one_repair_then_fail_recoverably(client: TestClient, engine: Engine) -> None:
    project_id = create_project(client)
    client.patch(f"/projects/{project_id}/brief", json=edit())
    FakeClient.outputs = [questions("target_unit_price"), questions("target_unit_price")]
    response = client.post(f"/projects/{project_id}/brief/clarifications")
    assert response.status_code == 503
    assert FakeClient.calls == 2
    with Session(engine) as session:
        run = session.scalars(select(AIRun).where(AIRun.project_id == project_id)).one()
        assert (run.status, run.attempts, run.validation_status) == (
            "VALIDATION_FAILED", 2, "INVALID"
        )
    assert client.get(f"/projects/{project_id}/brief").json()["missing_fields"]


def test_generation_sends_only_first_five_ordered_readiness_fields(client: TestClient) -> None:
    project_id = create_project(client)
    client.patch(f"/projects/{project_id}/brief", json=edit(
        product_name=None, quantity=None, destination=None
    ))
    selected = (
        "product_name", "quantity", "destination", "delivery_target", "requirement.material"
    )
    FakeClient.outputs = [questions(*selected)]
    response = client.post(f"/projects/{project_id}/brief/clarifications")
    assert response.status_code == 200, response.text
    assert [item["field_key"] for item in response.json()["questions"]] == list(selected)
    model_input = json.loads(str(FakeClient.requests[0]["input_text"]))
    assert [item["field_key"] for item in model_input["unresolved_fields"]] == list(selected)


def test_provider_failure_preserves_brief_and_manual_patch(client: TestClient, engine: Engine) -> None:
    project_id = create_project(client)
    saved = client.patch(f"/projects/{project_id}/brief", json=edit()).json()
    FakeClient.outputs = [ModelProviderError("provider unavailable", retryable=False)]
    response = client.post(f"/projects/{project_id}/brief/clarifications")
    assert response.status_code == 503
    with Session(engine) as session:
        run = session.scalars(select(AIRun).where(AIRun.project_id == project_id)).one()
        assert (run.status, run.attempts) == ("PROVIDER_FAILED", 1)
    current = client.get(f"/projects/{project_id}/brief").json()
    assert current["brief_revision"] == saved["brief_revision"]
    manual = client.patch(f"/projects/{project_id}/brief", json=edit(
        delivery_target={"kind": "PERIOD", "label": "Early 2027", "start_date": None, "end_date": None}
    ))
    assert manual.status_code == 200
    assert manual.json()["brief_revision"] == saved["brief_revision"] + 1


def test_repair_succeeds_and_answer_patch_recalculates_readiness(client: TestClient, engine: Engine) -> None:
    project_id = create_project(client)
    saved = client.patch(f"/projects/{project_id}/brief", json=edit()).json()
    correct = questions("delivery_target", "requirement.material", "requirement.custom_branding")
    FakeClient.outputs = [questions("destination"), correct]
    generated = client.post(f"/projects/{project_id}/brief/clarifications")
    assert generated.status_code == 200
    with Session(engine) as session:
        run = session.scalars(select(AIRun).where(AIRun.project_id == project_id)).one()
        assert (run.status, run.attempts, run.validation_status) == ("COMPLETED", 2, "REPAIRED")

    answered = edit(
        delivery_target={"kind": "DATE", "date": "2027-01-01"},
        requirements=[
            {"kind": "MATERIAL", "importance": None, "expected_value": {"value": "Cotton"}, "notes": None},
            {"kind": "CAPABILITY", "importance": None, "expected_value": {"capability_key": "CUSTOM_BRANDING", "value": False}, "notes": None},
        ],
        expected_brief_revision=generated.json()["brief_revision"],
    )
    response = client.patch(f"/projects/{project_id}/brief", json=answered)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "READY_FOR_REVIEW"
    assert response.json()["brief_revision"] == saved["brief_revision"] + 1
    assert response.json()["destination"] == "Sydney"

    stale = client.patch(f"/projects/{project_id}/brief", json=answered)
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "BRIEF_CONFLICT"
    assert client.get(f"/projects/{project_id}/brief").json()["brief_revision"] == response.json()["brief_revision"]

    legacy = client.patch(f"/projects/{project_id}/brief", json=edit(quantity=1200, requirements=[
        {"id": item["id"], "kind": item["kind"], "importance": item["importance"], "expected_value": item["expected_value"], "notes": item["notes"]}
        for item in response.json()["requirements"]
    ], delivery_target=response.json()["delivery_target"]))
    assert legacy.status_code == 200, legacy.text
    assert legacy.json()["quantity"] == 1200
    assert legacy.json()["brief_revision"] == response.json()["brief_revision"] + 1


def test_ready_brief_and_foreign_session_skip_generation(client: TestClient, engine: Engine) -> None:
    project_id = create_project(client)
    ready = edit(category="Totes", delivery_target={"kind": "DATE", "date": "2027-01-01"})
    assert client.patch(f"/projects/{project_id}/brief", json=ready).status_code == 200
    assert client.post(f"/projects/{project_id}/brief/clarifications").status_code == 409
    assert FakeClient.calls == 0

    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_database_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_database_session] = override_database_session
    with TestClient(app, raise_server_exceptions=False) as other:
        assert other.post("/demo-session").status_code == 204
        assert other.post(f"/projects/{project_id}/brief/clarifications").status_code == 404
    assert FakeClient.calls == 0


def test_generation_rejects_revision_changed_during_model_call(client: TestClient, engine: Engine) -> None:
    project_id = create_project(client)
    client.patch(f"/projects/{project_id}/brief", json=edit())
    FakeClient.outputs = [questions("delivery_target", "requirement.material", "requirement.custom_branding")]

    def change_revision() -> None:
        with Session(engine) as session:
            project = session.get(Project, project_id)
            assert project is not None
            project.brief_revision += 1
            session.commit()

    FakeClient.callbacks = [change_revision]
    response = client.post(f"/projects/{project_id}/brief/clarifications")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BRIEF_CONFLICT"
    assert FakeClient.calls == 1


def test_revision_guard_and_invalid_mixed_patch_are_atomic(client: TestClient) -> None:
    project_id = create_project(client)
    original = client.patch(f"/projects/{project_id}/brief", json=edit()).json()
    stale = client.patch(f"/projects/{project_id}/brief", json=edit(
        destination="Melbourne", expected_brief_revision=0
    ))
    assert stale.status_code == 409
    invalid = client.patch(f"/projects/{project_id}/brief", json=edit(
        destination="Melbourne", quantity=-1, expected_brief_revision=original["brief_revision"]
    ))
    assert invalid.status_code == 422
    current = client.get(f"/projects/{project_id}/brief").json()
    assert (current["destination"], current["quantity"], current["brief_revision"]) == (
        "Sydney", 1000, original["brief_revision"]
    )
