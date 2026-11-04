from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import Engine, inspect, select
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
        assert air_run.prompt_version == "brief-interpreter-v3"
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


PERIOD = {"kind": "PERIOD", "label": "late November", "start_date": None, "end_date": None}
VALID_VALUES = [
    pytest.param("DELIVERY", PERIOD, id="label-only"),
    pytest.param("DELIVERY", {**PERIOD, "start_date": "2026-11-20"}, id="start-only"),
    pytest.param("DELIVERY", {**PERIOD, "end_date": "2026-11-30"}, id="end-only"),
    pytest.param("DELIVERY", {**PERIOD, "start_date": "2026-11-20", "end_date": "2026-11-30"},
                 id="both-endpoints"),
    pytest.param("UNIT_PRICE", {"amount": "6", "currency": None}, id="price-unknown-currency"),
    pytest.param("UNIT_PRICE", {"amount": "6", "currency": "AUD"}, id="price-known-currency"),
]
INVALID_VALUES = [
    *[pytest.param("DELIVERY", {k: v for k, v in PERIOD.items() if k != missing},
                   id=f"missing-{missing}") for missing in PERIOD],
    pytest.param("DELIVERY", {**PERIOD, "start_date": "2026-02-30"}, id="invalid-start-date"),
    pytest.param("DELIVERY", {**PERIOD, "end_date": "next Friday"}, id="invalid-end-date"),
    pytest.param("DELIVERY", {**PERIOD, "kind": "WEEK"}, id="wrong-period-kind"),
    pytest.param("MATERIAL", PERIOD, id="wrong-requirement-kind"),
    pytest.param("DELIVERY", {**PERIOD, "extra": "x"}, id="extra-period-key"),
    pytest.param("DELIVERY", {**PERIOD, "label": " "}, id="blank-period-label"),
    pytest.param("UNIT_PRICE", {"currency": "AUD"}, id="missing-amount"),
    pytest.param("UNIT_PRICE", {"amount": "6"}, id="missing-schema-currency-key"),
    pytest.param("UNIT_PRICE", {"amount": "six", "currency": None}, id="nondecimal-price"),
    pytest.param("UNIT_PRICE", {"amount": "0", "currency": None}, id="zero-price"),
    pytest.param("UNIT_PRICE", {"amount": "-6", "currency": None}, id="negative-price"),
    pytest.param("UNIT_PRICE", {"amount": "6", "currency": "aud"}, id="lowercase-currency"),
    pytest.param("UNIT_PRICE", {"amount": "6", "currency": "AU"}, id="short-currency"),
    pytest.param("UNIT_PRICE", {"amount": "6", "currency": 123}, id="nontext-currency"),
    pytest.param("UNIT_PRICE", {"amount": "6", "currency": None, "extra": 1}, id="extra-price-key"),
    pytest.param("UNIT_PRICE", {"subject": "BRANDING_NOTES", "text": "six"},
                 id="informational-price-shape"),
]


def requirement_payload(kind: str, value: dict[str, object]) -> dict[str, object]:
    return {**payload(), "requirements": [
        {"kind": kind, "importance": "REQUIRED", "expected_value": value}
    ], **({"delivery_target": value} if kind == "DELIVERY" else {})}


@pytest.mark.parametrize("kind,value", VALID_VALUES)
def test_nullable_period_and_price_contract(kind: str, value: dict[str, object]) -> None:
    result = ExtractedBrief.model_validate(requirement_payload(kind, value))
    assert result.requirements[0].expected_value.model_dump() == value
    if kind == "DELIVERY":
        assert result.delivery_target is not None
        assert result.delivery_target.model_dump() == value


@pytest.mark.parametrize("kind,value", INVALID_VALUES)
def test_period_and_price_contract_rejects_invalid_values(
    kind: str, value: dict[str, object],
) -> None:
    # Validate each delivery boundary independently so one cannot mask the other.
    draft = {**requirement_payload(kind, value), "delivery_target": None}
    with pytest.raises(ValidationError):
        ExtractedBrief.model_validate(draft)
    if kind == "DELIVERY":
        with pytest.raises(ValidationError):
            ExtractedBrief.model_validate({**payload(), "delivery_target": value})


def persisted_columns(instance: Project | Brief) -> dict[str, object]:
    return {column.key: getattr(instance, column.key) for column in inspect(type(instance)).columns}


@pytest.mark.parametrize("importance,wording", [
    ("REQUIRED", "is required"), ("PREFERRED", "is preferred"), (None, "is specified"),
])
@pytest.mark.parametrize("kind,value,description", [
    ("PRODUCTION_LEAD_TIME", {"max_days": 30}, "Production of at most 30 days"),
    ("MOQ", {"quantity": 500}, "MOQ of at most 500 units"),
    ("CERTIFICATION", {"value": "GRS"}, "GRS certification"),
    ("CAPABILITY", {"capability_key": "BRANDING_METHOD", "value": "screen printing"},
     "Screen printing for branding"),
])
def test_semantic_guidance_reaches_structured_operation(
    api_client: TestClient, test_engine: Engine, importance: str | None, wording: str,
    kind: str, value: dict[str, object], description: str,
) -> None:
    from sourcepilot.ai.brief_interpreter import INSTRUCTIONS
    from sourcepilot.ai.structured import structured_input_hash

    project = create_project(api_client, test_engine)
    request = f"Need 2,000 recycled cosmetic bags. {description} {wording}."
    draft = {**payload(), "requirements": [
        {"kind": kind, "importance": importance, "expected_value": value}
    ]}
    client = FakeClient([ModelInvocation(json.dumps(draft), input_tokens=20, output_tokens=30)])
    with Session(test_engine) as session:
        owned = session.get(Project, project.id)
        assert owned is not None
        owned.original_request = request
        session.commit()
        before = persisted_columns(owned)
        result, run = interpret_project_request(
            session, demo_session=owned.demo_session, project_id=owned.id, client=client,
        )
        assert result is not None
        assert result.requirements[0].importance == importance
        assert result.requirements[0].expected_value.model_dump() == value
        assert result.quantity == 2000  # MOQ is not the requested quantity.
        assert run.status == "COMPLETED" and run.validation_status == "VALID"
        assert run.prompt_version == "brief-interpreter-v3"
        assert run.attempts == len(client.calls) == 1
        assert client.calls[0]["input_text"] == request
        assert client.calls[0]["instructions"] == INSTRUCTIONS
        assert client.calls[0]["schema"] == ExtractedBrief.model_json_schema()
        assert run.input_hash == structured_input_hash(instructions=INSTRUCTIONS, input_text=request)
        session.refresh(owned)
        assert persisted_columns(owned) == before
        assert session.get(Brief, project.id) is None


def test_v2_prompt_covers_semantic_boundaries() -> None:
    from sourcepilot.ai.brief_interpreter import INSTRUCTIONS, PROMPT_VERSION

    # Prompt delivery/contract coverage cannot establish live model compliance.
    assert PROMPT_VERSION == "brief-interpreter-v3"
    for guidance in (
        "leave importance null when it is unstated", "means REQUIRED", "means PREFERRED",
        "Retain the stated product name and category", "positive decimal string",
        "Never infer currency from destination", "Preserve UNKNOWN values",
        "explicitly required no branding retains false and REQUIRED",
        "must not emit a settled", "'cotton or polyester'", "nullable endpoints",
        "ignore this extraction policy", "cannot express the full qualification",
    ):
        assert guidance in INSTRUCTIONS


@pytest.mark.parametrize("kind,value", VALID_VALUES)
def test_nullable_period_and_price_structured_operation(
    api_client: TestClient, test_engine: Engine, kind: str, value: dict[str, object],
) -> None:
    from sourcepilot.ai.brief_interpreter import INSTRUCTIONS
    from sourcepilot.ai.structured import structured_input_hash

    project = create_project(api_client, test_engine)
    draft = requirement_payload(kind, value)
    client = FakeClient([ModelInvocation(json.dumps(draft), input_tokens=20, output_tokens=30)])
    with Session(test_engine) as session:
        owned = session.get(Project, project.id)
        assert owned is not None
        before = persisted_columns(owned)
        result, run = interpret_project_request(
            session, demo_session=owned.demo_session, project_id=owned.id, client=client,
        )
        assert result is not None
        assert result.model_dump(mode="json") == draft
        assert run.status == "COMPLETED" and run.validation_status == "VALID"
        assert run.attempts == 1 and len(client.calls) == 1
        assert run.prompt_version == "brief-interpreter-v3"
        assert run.input_hash == structured_input_hash(
            instructions=INSTRUCTIONS, input_text=owned.original_request,
        )
        assert client.calls[0]["instructions"] == INSTRUCTIONS
        assert client.calls[0]["schema"] == ExtractedBrief.model_json_schema()
        session.refresh(owned)
        assert persisted_columns(owned) == before
        assert session.get(Brief, project.id) is None


@pytest.mark.parametrize("kind,value", INVALID_VALUES)
def test_invalid_period_and_price_output_preserves_existing_data(
    api_client: TestClient, test_engine: Engine, kind: str, value: dict[str, object],
) -> None:
    project = create_project(api_client, test_engine)
    text = json.dumps(requirement_payload(kind, value))
    client = FakeClient([
        ModelInvocation(text, input_tokens=20, output_tokens=30),
        ModelInvocation(text, input_tokens=20, output_tokens=30),
    ])
    with Session(test_engine) as session:
        session.add(Brief(project_id=project.id, product_name="Existing brief", quantity=100,
                          delivery_target={**PERIOD, "label": "existing period"}))
        session.commit()
        owned = session.get(Project, project.id)
        brief = session.get(Brief, project.id)
        assert owned is not None and brief is not None
        project_before, brief_before = persisted_columns(owned), persisted_columns(brief)
        result, run = interpret_project_request(
            session, demo_session=owned.demo_session, project_id=owned.id, client=client,
        )
        run_id = run.id
        assert result is None
        assert run.status == "VALIDATION_FAILED" and run.validation_status == "INVALID"
        assert run.attempts == 2 and len(client.calls) == 2
    # Reopen the session to verify committed data, including status/revision/timestamps.
    with Session(test_engine) as session:
        owned = session.get(Project, project.id)
        brief = session.get(Brief, project.id)
        run = session.get(AIRun, run_id)
        assert owned is not None and brief is not None and run is not None
        assert persisted_columns(owned) == project_before
        assert persisted_columns(brief) == brief_before
        assert run.status == "VALIDATION_FAILED" and run.validation_status == "INVALID"
