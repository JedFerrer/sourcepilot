"""M1-U4 API and application integration coverage."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import ClassVar
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

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
    outputs: ClassVar[list[ModelInvocation | Exception]] = []

    def invoke(self, **_: object) -> ModelInvocation:
        FakeClient.calls += 1
        result = FakeClient.outputs.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def extraction(**changes: object) -> dict[str, object]:
    return {
        "product_name": "Cosmetic bag",
        "category": "Cosmetic bags",
        "quantity": 2000,
        "destination": "Sydney",
        "delivery_target": {"kind": "DATE", "date": "2027-01-01"},
        "target_unit_price": None,
        "attributes": [{"subject": "COLOR", "text": "Blue"}],
        "requirements": [
            {"kind": "MATERIAL", "importance": None, "expected_value": {"value": "Recycled polyester"}},
            {"kind": "CAPABILITY", "importance": "REQUIRED", "expected_value": {"capability_key": "CUSTOM_BRANDING", "value": True}},
        ],
        "ambiguities": ["Branding method was not stated."],
        **changes,
    }


def empty_edit() -> dict[str, object]:
    return {
        "product_name": None,
        "category": None,
        "quantity": None,
        "destination": None,
        "delivery_target": None,
        "target_unit_price": None,
        "requirements": [],
    }


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
    FakeClient.outputs = []
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
    response = client.post(
        "/projects",
        json={"name": "Bags", "original_request": "Source recycled cosmetic bags."},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_empty_get_and_noop_patch_do_not_create_brief_domain_state(
    client: TestClient, engine: Engine
) -> None:
    project_id = create_project(client)
    response = client.get(f"/projects/{project_id}/brief")
    assert response.status_code == 200
    assert response.json()["requirements"] == []
    assert response.json()["brief_revision"] == 0
    assert response.json()["can_analyze"] is True
    assert response.json()["missing_fields"][0]["field_key"] == "product_name"
    with Session(engine) as session:
        assert session.get(Brief, project_id) is None
        assert session.scalars(select(Requirement).where(Requirement.project_id == project_id)).all() == []
        assert session.get(Project, project_id).brief_revision == 0  # type: ignore[union-attr]
    assert client.patch(f"/projects/{project_id}/brief", json=empty_edit()).status_code == 200
    with Session(engine) as session:
        assert session.get(Brief, project_id) is None
        assert session.get(Project, project_id).brief_revision == 0  # type: ignore[union-attr]


@pytest.mark.parametrize(
    "change",
    [
        {"quantity": 2_147_483_648},
        {"product_name": "x" * 256},
        {"category": "x" * 256},
        {"destination": "x" * 256},
        *[
            {"requirements": [{"kind": kind, "importance": None, "expected_value": {key: 2_147_483_648}}]}
            for kind, key in [("MOQ", "quantity"), ("QUANTITY", "quantity"), ("PRODUCTION_LEAD_TIME", "max_days")]
        ],
    ],
)
def test_patch_rejects_values_beyond_persistence_bounds(
    client: TestClient, engine: Engine, change: dict[str, object]
) -> None:
    project_id = create_project(client)
    response = client.patch(f"/projects/{project_id}/brief", json={**empty_edit(), **change})
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    if "quantity" in change:
        assert response.json()["error"]["fields"] == [
            {"field": "body.quantity", "message": "Value error, quantity must be at most 2147483647"}
        ]
    with Session(engine) as session:
        assert session.get(Brief, project_id) is None
        assert session.scalars(select(Requirement).where(Requirement.project_id == project_id)).all() == []
        assert session.get(Project, project_id).brief_revision == 0  # type: ignore[union-attr]


@pytest.mark.parametrize(
    "change",
    [
        {"product_name": "x" * 256},
        {"category": "x" * 256},
        {"destination": "x" * 256},
        {"quantity": 2_147_483_648},
        *[
            {"requirements": [{"kind": kind, "importance": None, "expected_value": {key: 2_147_483_648}}]}
            for kind, key in [("MOQ", "quantity"), ("QUANTITY", "quantity"), ("PRODUCTION_LEAD_TIME", "max_days")]
        ],
    ],
)
def test_analyze_rejects_oversized_extraction_before_persistence(
    client: TestClient, engine: Engine, change: dict[str, object]
) -> None:
    project_id = create_project(client)
    oversized = extraction(**change)
    FakeClient.outputs = [ModelInvocation(json.dumps(oversized), None, None)] * 2
    response = client.post(f"/projects/{project_id}/brief/analyze")
    assert response.status_code == 503, response.text
    assert response.json()["error"]["code"] == "BRIEF_ANALYSIS_UNAVAILABLE"
    assert FakeClient.calls == 2
    with Session(engine) as session:
        assert session.get(Brief, project_id) is None
        assert session.scalars(select(Requirement).where(Requirement.project_id == project_id)).all() == []
        assert session.get(Project, project_id).brief_revision == 0  # type: ignore[union-attr]
        run = session.scalar(select(AIRun).where(AIRun.project_id == project_id))
        assert run is not None and run.status == "VALIDATION_FAILED"


def test_analyze_persists_extraction_null_importance_and_uncertainty_for_approval(
    client: TestClient, engine: Engine
) -> None:
    project_id = create_project(client)
    FakeClient.outputs = [ModelInvocation(json.dumps(extraction()), 10, 20)]
    result = client.post(f"/projects/{project_id}/brief/analyze")
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["brief_revision"] == 1
    assert data["can_analyze"] is False
    assert data["status"] == "READY_FOR_REVIEW"
    assert data["ambiguities"] == ["Branding method was not stated."]
    assert data["uncertainties"] == ["Branding method was not stated."]
    material = next(item for item in data["requirements"] if item["kind"] == "MATERIAL")
    attribute = next(item for item in data["requirements"] if item["expected_value"].get("subject") == "COLOR")
    assert material["importance"] is None
    assert attribute["importance"] == "INFORMATIONAL"
    assert attribute["expected_value"] == {"subject": "COLOR", "text": "Blue"}
    reread = client.get(f"/projects/{project_id}/brief").json()
    assert "ambiguities" not in reread
    assert reread["uncertainties"] == ["Branding method was not stated."]
    saved = client.patch(f"/projects/{project_id}/brief", json={
        **{key: reread[key] for key in (
            "product_name", "category", "quantity", "destination", "delivery_target",
            "target_unit_price", "requirements",
        )},
        "quantity": 2200,
        "expected_brief_revision": reread["brief_revision"],
    })
    assert saved.status_code == 200, saved.text
    assert saved.json()["brief_revision"] == 2
    assert saved.json()["uncertainties"] == ["Branding method was not stated."]
    assert client.get(f"/projects/{project_id}/brief").json()["uncertainties"] == [
        "Branding method was not stated."
    ]
    assert reread["brief_revision"] == 1
    with Session(engine) as session:
        assert len(session.scalars(select(AIRun).where(AIRun.project_id == project_id)).all()) == 1


def test_empty_extraction_can_retry_without_revision(client: TestClient, engine: Engine) -> None:
    project_id = create_project(client)
    FakeClient.outputs = [ModelInvocation(json.dumps(extraction(
        product_name=None, category=None, quantity=None, destination=None,
        delivery_target=None, attributes=[], requirements=[], ambiguities=[],
    )), None, None)]
    first = client.post(f"/projects/{project_id}/brief/analyze")
    assert first.status_code == 200
    assert first.json()["brief_revision"] == 0
    assert first.json()["can_analyze"] is True
    with Session(engine) as session:
        assert session.get(Brief, project_id) is None
    FakeClient.outputs = [ModelInvocation(json.dumps(extraction()), None, None)]
    assert client.post(f"/projects/{project_id}/brief/analyze").json()["brief_revision"] == 1


def test_blocked_reanalysis_never_calls_model_or_creates_airun(
    client: TestClient, engine: Engine
) -> None:
    project_id = create_project(client)
    saved = client.patch(
        f"/projects/{project_id}/brief", json={**empty_edit(), "product_name": "Manual bag"}
    )
    assert saved.status_code == 200
    assert saved.json()["brief_revision"] == 1
    blocked = client.post(f"/projects/{project_id}/brief/analyze")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "BRIEF_CONFLICT"
    assert FakeClient.calls == 0
    with Session(engine) as session:
        assert session.scalars(select(AIRun).where(AIRun.project_id == project_id)).all() == []


def test_ai_failure_allows_manual_edit_then_blocks_analysis(
    client: TestClient, engine: Engine
) -> None:
    project_id = create_project(client)
    FakeClient.outputs = [
        ModelProviderError("temporary", retryable=True),
        ModelProviderError("failed", retryable=True),
    ]
    assert client.post(f"/projects/{project_id}/brief/analyze").status_code == 503
    saved = client.patch(
        f"/projects/{project_id}/brief", json={**empty_edit(), "product_name": "Manual bag"}
    )
    assert saved.status_code == 200
    assert saved.json()["brief_revision"] == 1
    assert client.post(f"/projects/{project_id}/brief/analyze").status_code == 409
    with Session(engine) as session:
        project = session.get(Project, project_id)
        assert project is not None
        assert project.original_request == "Source recycled cosmetic bags."
        assert len(session.scalars(select(AIRun).where(AIRun.project_id == project_id)).all()) == 1


def test_patch_add_update_remove_clear_and_noop_revision(client: TestClient) -> None:
    project_id = create_project(client)
    path = f"/projects/{project_id}/brief"
    first = client.patch(path, json={
        **empty_edit(),
        "category": "Cosmetic bags",
        "requirements": [{"kind": "MATERIAL", "importance": None, "expected_value": {"value": "Cotton"}}],
    }).json()
    assert first["brief_revision"] == 1
    assert first["status"] == "IN_PROGRESS"
    assert client.patch(path, json={**empty_edit(), "category": "Cosmetic bags", "requirements": first["requirements"]}).json()["brief_revision"] == 1
    requirement = first["requirements"][0]
    changed = client.patch(path, json={
        **empty_edit(), "category": "Cosmetic bags",
        "requirements": [{**requirement, "importance": "REQUIRED", "expected_value": {"value": "Recycled cotton"}}],
    }).json()
    assert changed["brief_revision"] == 2
    cleared = client.patch(path, json=empty_edit()).json()
    assert cleared["brief_revision"] == 3
    assert cleared["can_analyze"] is False
    assert cleared["requirements"] == []
    assert client.patch(path, json=empty_edit()).json()["brief_revision"] == 3
    assert client.post(f"{path}/analyze").status_code == 409


def ready_edit() -> dict[str, object]:
    return {
        **empty_edit(),
        "product_name": "Desk lamp",
        "category": "Lighting",
        "quantity": 100,
        "destination": "Manila",
        "delivery_target": {"kind": "DATE", "date": "2027-01-01"},
    }


def test_approval_and_post_approval_stage_transitions(client: TestClient, engine: Engine) -> None:
    project_id = create_project(client)
    path = f"/projects/{project_id}/brief"
    approve_path = f"{path}/approve"
    assert client.post(approve_path, json={"expected_brief_revision": 0}).status_code == 409
    saved = client.patch(path, json=ready_edit()).json()
    assert saved["status"] == "READY_FOR_REVIEW"
    assert saved["approved_at"] is None
    assert client.get(f"/projects/{project_id}").json()["stage"] == "BRIEF"
    assert client.post(approve_path, json={"expected_brief_revision": 0}).status_code == 409

    approved = client.post(approve_path, json={"expected_brief_revision": 1})
    assert approved.status_code == 200, approved.text
    first = approved.json()
    assert first["status"] == "APPROVED"
    assert first["approved_at"] is not None
    assert first["brief_revision"] == 1
    assert client.get(f"/projects/{project_id}").json()["stage"] == "SUPPLIERS"

    with Session(engine) as session:
        project = session.get(Project, project_id)
        brief = session.get(Brief, project_id)
        assert project is not None and brief is not None
        before_updated_at = project.updated_at
        before_approved_at = brief.approved_at

    repeated = client.post(approve_path, json={"expected_brief_revision": 1})
    assert repeated.status_code == 200
    assert repeated.json() == first
    with Session(engine) as session:
        project = session.get(Project, project_id)
        brief = session.get(Brief, project_id)
        assert project is not None and brief is not None
        assert project.stage == "SUPPLIERS"
        assert project.brief_revision == 1
        assert project.updated_at == before_updated_at
        assert brief.approved_at == before_approved_at

    still_ready = client.patch(path, json={**ready_edit(), "quantity": 200, "expected_brief_revision": 1}).json()
    assert still_ready["brief_revision"] == 2
    assert still_ready["status"] == "APPROVED"
    assert still_ready["approved_at"] == first["approved_at"]
    assert client.get(f"/projects/{project_id}").json()["stage"] == "SUPPLIERS"
    noop = client.patch(path, json={**ready_edit(), "quantity": 200, "expected_brief_revision": 2}).json()
    assert noop == still_ready

    incomplete = client.patch(path, json={**ready_edit(), "quantity": None, "expected_brief_revision": 2}).json()
    assert incomplete["brief_revision"] == 3
    assert incomplete["status"] == "IN_PROGRESS"
    assert incomplete["approved_at"] is None
    assert client.get(f"/projects/{project_id}").json()["stage"] == "BRIEF"
    assert client.post(approve_path, json={"expected_brief_revision": 3}).status_code == 409

    restored = client.patch(path, json={**ready_edit(), "expected_brief_revision": 3}).json()
    assert restored["brief_revision"] == 4
    assert restored["status"] == "READY_FOR_REVIEW"
    reapproved = client.post(approve_path, json={"expected_brief_revision": 4}).json()
    assert reapproved["status"] == "APPROVED"
    assert reapproved["approved_at"] is not None
    assert reapproved["brief_revision"] == 4
    assert client.get(f"/projects/{project_id}").json()["stage"] == "SUPPLIERS"


def test_approval_is_session_scoped_and_failed_edits_keep_approval(client: TestClient) -> None:
    project_id = create_project(client)
    path = f"/projects/{project_id}/brief"
    client.patch(path, json=ready_edit())
    approved = client.post(f"{path}/approve", json={"expected_brief_revision": 1}).json()
    foreign = TestClient(app, raise_server_exceptions=False)
    assert foreign.post("/demo-session").status_code == 204
    assert foreign.post(f"{path}/approve", json={"expected_brief_revision": 1}).status_code == 404
    assert client.patch(path, json={**ready_edit(), "quantity": None, "expected_brief_revision": 0}).status_code == 409
    assert client.patch(path, json={**ready_edit(), "quantity": -1, "expected_brief_revision": 1}).status_code == 422
    assert client.get(path).json() == approved
    assert client.get(f"/projects/{project_id}").json()["stage"] == "SUPPLIERS"


@pytest.mark.parametrize("invalid_case", ["value", "foreign_id"])
def test_mixed_patch_failure_rolls_back_entire_snapshot(
    client: TestClient, engine: Engine, invalid_case: str
) -> None:
    project_id = create_project(client)
    path = f"/projects/{project_id}/brief"
    initial = client.patch(path, json={
        **empty_edit(),
        "product_name": "Original bag",
        "requirements": [{"kind": "MATERIAL", "importance": "REQUIRED", "expected_value": {"value": "Cotton"}}],
    })
    assert initial.status_code == 200
    before = initial.json()
    foreign_project_id = client.post(
        "/projects", json={"name": "Foreign", "original_request": "Other"}
    ).json()["id"]
    foreign = client.patch(f"/projects/{foreign_project_id}/brief", json={
        **empty_edit(),
        "requirements": [{"kind": "MATERIAL", "importance": None, "expected_value": {"value": "Wool"}}],
    }).json()["requirements"][0]
    invalid = (
        {"kind": "MOQ", "importance": None, "expected_value": {"quantity": 0}}
        if invalid_case == "value" else {**foreign, "id": foreign["id"]}
    )
    mixed = client.patch(path, json={
        **empty_edit(),
        "product_name": "Changed bag",
        "category": "Changed category",
        "requirements": [
            {**before["requirements"][0], "expected_value": {"value": "Linen"}},
            {"kind": "CERTIFICATION", "importance": "PREFERRED", "expected_value": {"value": "GRS"}},
            invalid,
        ],
    })
    assert mixed.status_code == 422, mixed.text
    assert mixed.json()["error"]["code"] == "VALIDATION_ERROR"
    after = client.get(path).json()
    assert after == before
    with Session(engine) as session:
        brief = session.get(Brief, project_id)
        assert brief is not None and brief.product_name == "Original bag" and brief.category is None
        requirements = session.scalars(select(Requirement).where(Requirement.project_id == project_id)).all()
        assert len(requirements) == 1
        assert requirements[0].id == UUID(before["requirements"][0]["id"])
        assert requirements[0].expected_value == {"value": "cotton"}
        assert session.get(Project, project_id).brief_revision == 1  # type: ignore[union-attr]


def test_foreign_requirement_id_and_project_are_rejected(client: TestClient) -> None:
    first_id = create_project(client)
    second_id = client.post("/projects", json={"name": "Other", "original_request": "Other"}).json()["id"]
    first = client.patch(f"/projects/{first_id}/brief", json={
        **empty_edit(),
        "requirements": [{"kind": "MATERIAL", "importance": "PREFERRED", "expected_value": {"value": "Cotton"}}],
    }).json()
    foreign = client.patch(f"/projects/{second_id}/brief", json={
        **empty_edit(), "requirements": [first["requirements"][0]],
    })
    assert foreign.status_code == 422
    assert client.get(f"/projects/{second_id}/brief").json()["brief_revision"] == 0
    other = TestClient(app, raise_server_exceptions=False)
    assert other.post("/demo-session").status_code == 204
    assert other.get(f"/projects/{first_id}/brief").status_code == 404


def test_existing_empty_brief_row_is_analyze_eligible(client: TestClient, engine: Engine) -> None:
    project_id = create_project(client)
    with Session(engine) as session:
        session.add(Brief(project_id=project_id))
        session.commit()
    assert client.get(f"/projects/{project_id}/brief").json()["can_analyze"] is True
    FakeClient.outputs = [ModelInvocation(json.dumps(extraction()), None, None)]
    assert client.post(f"/projects/{project_id}/brief/analyze").json()["brief_revision"] == 1


def test_manual_save_during_model_call_is_not_overwritten(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id = create_project(client)

    def invoke_and_save(self: FakeClient, **_: object) -> ModelInvocation:
        with Session(engine) as session:
            project = session.get(Project, project_id)
            assert project is not None
            session.add(Brief(project_id=project.id, product_name="Manual winner"))
            project.brief_revision += 1
            session.commit()
        return ModelInvocation(json.dumps(extraction()), None, None)

    monkeypatch.setattr(FakeClient, "invoke", invoke_and_save)
    response = client.post(f"/projects/{project_id}/brief/analyze")
    assert response.status_code == 409
    saved = client.get(f"/projects/{project_id}/brief").json()
    assert saved["product_name"] == "Manual winner"
    assert saved["brief_revision"] == 1
