from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from sourcepilot.ai.brief_interpreter import ExtractedBrief, interpret_project_request
from sourcepilot.ai.client import AnalystModelInvocation, ModelInvocation, ModelProviderError
from sourcepilot.main import app
from sourcepilot.persistence.database import get_database_session
from sourcepilot.persistence.models import AIRun, Brief, Project
from tests.database_test_support import (
    create_test_engine,
    persistence_test_database_url_from_environment,
    reset_test_database,
)


class FakeClient:
    model = "test-model"

    def __init__(self, outputs: list[ModelInvocation | Exception]) -> None:
        self.outputs = outputs
        self.calls: list[dict[str, object]] = []

    def invoke(self, **kwargs: object) -> ModelInvocation:
        self.calls.append(kwargs)
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output

    def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
        raise AssertionError("Tool calls are outside these Brief tests.")


def payload() -> dict[str, object]:
    return {
        "product_name": "cosmetic bags",
        "category": "cosmetic bags",
        "quantity": 2000,
        "destination": "Sydney",
        "delivery_target": None,
        "target_unit_price": None,
        "attributes": [{"subject": "DIMENSIONS", "text": "20 x 15 cm"}],
        "requirements": [
            {"kind": "MATERIAL", "importance": None, "expected_value": {"value": "recycled polyester"}}
        ],
        "ambiguities": [],
    }


def test_contract_keeps_attributes_requirements_and_unknowns_separate() -> None:
    extracted = ExtractedBrief.model_validate(payload())

    assert extracted.attributes[0].subject == "DIMENSIONS"
    assert extracted.requirements[0].kind == "MATERIAL"
    assert extracted.requirements[0].importance is None
    assert extracted.delivery_target is None
    assert extracted.target_unit_price is None


@pytest.mark.parametrize(
    "change",
    [
        {"attributes": [{"subject": "ARBITRARY", "text": "value"}]},
        {"requirements": [{"kind": "MATERIAL", "importance": None, "expected_value": {"value": " "}}]},
        {"requirements": [{"kind": "UNKNOWN", "importance": None, "expected_value": {"value": "x"}}]},
        {"requirements": [{"kind": "MOQ", "importance": None, "expected_value": {"quantity": -1}}]},
        {"requirements": [{"kind": "CAPABILITY", "importance": None, "expected_value": {"capability_key": "CUSTOM_BRANDING", "value": 1}}]},
        {"target_unit_price": "not a price"},
        {"quantity": 0},
        {"ambiguities": [" "]},
    ],
)
def test_contract_rejects_out_of_domain_values(change: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ExtractedBrief.model_validate({**payload(), **change})


@pytest.mark.parametrize("value", ["2", True])
@pytest.mark.parametrize("field", ["quantity", "MOQ", "QUANTITY", "PRODUCTION_LEAD_TIME"])
def test_contract_rejects_integer_coercion(field: str, value: object) -> None:
    if field == "quantity":
        change: dict[str, object] = {"quantity": value}
    else:
        value_key = "max_days" if field == "PRODUCTION_LEAD_TIME" else "quantity"
        change = {
            "requirements": [
                {"kind": field, "importance": None, "expected_value": {value_key: value}}
            ]
        }

    with pytest.raises(ValidationError):
        ExtractedBrief.model_validate({**payload(), **change})


@pytest.fixture(scope="module")
def test_database_url() -> str:
    return persistence_test_database_url_from_environment()


@pytest.fixture(scope="module")
def test_engine(test_database_url: str) -> Iterator[Engine]:
    engine = create_test_engine(test_database_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(autouse=True)
def reset_interpreter_database(test_database_url: str) -> Iterator[None]:
    reset_test_database(test_database_url)
    yield
    reset_test_database(test_database_url)


@pytest.fixture
def api_client(test_engine: Engine) -> Iterator[TestClient]:
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)

    def override_database_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_database_session] = override_database_session
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()


def create_project(api_client: TestClient, test_engine: Engine) -> Project:
    assert api_client.post("/demo-session").status_code == 204
    created = api_client.post(
        "/projects",
        json={"name": "Bags", "original_request": "Need 2,000 recycled cosmetic bags."},
    )
    assert created.status_code == 201
    with Session(test_engine) as session:
        project = session.get(Project, created.json()["id"])
        assert project is not None
        session.expunge(project)
        return project


def test_interpreter_returns_extraction_and_air_run_without_persisting_brief(
    api_client: TestClient, test_engine: Engine
) -> None:
    project = create_project(api_client, test_engine)
    client = FakeClient([ModelInvocation(json.dumps(payload()), input_tokens=20, output_tokens=30)])
    with Session(test_engine) as session:
        owned = session.get(Project, project.id)
        assert owned is not None
        result, air_run = interpret_project_request(
            session, demo_session=owned.demo_session, project_id=owned.id, client=client
        )

        assert result is not None
        assert result.requirements[0].importance is None
        assert air_run.status == "COMPLETED"
        assert air_run.attempts == 1
        assert air_run.project_id == owned.id
        assert air_run.prompt_version == "brief-interpreter-v1"
        assert air_run.input_tokens == 20
        assert session.get(Brief, owned.id) is None
        assert client.calls[0]["input_text"] == owned.original_request


def test_interpreter_failure_preserves_project_and_existing_brief(
    api_client: TestClient, test_engine: Engine
) -> None:
    project = create_project(api_client, test_engine)
    with Session(test_engine) as session:
        session.add(Brief(project_id=project.id, product_name="Existing brief", quantity=100))
        session.commit()
        owned = session.get(Project, project.id)
        assert owned is not None
        original_request = owned.original_request
        client = FakeClient(
            [
                ModelProviderError("temporary", retryable=True),
                ModelProviderError("still failing", retryable=True),
            ]
        )
        result, air_run = interpret_project_request(
            session, demo_session=owned.demo_session, project_id=owned.id, client=client
        )
        assert result is None
        assert air_run.status == "PROVIDER_FAILED"
        assert air_run.attempts == 2

    response = api_client.get(f"/projects/{project.id}")
    assert response.status_code == 200
    assert response.json()["original_request"] == original_request
    with Session(test_engine) as session:
        brief = session.get(Brief, project.id)
        assert brief is not None
        assert brief.product_name == "Existing brief"
        assert brief.quantity == 100
        assert session.scalar(select(AIRun).where(AIRun.project_id == project.id)) is not None
