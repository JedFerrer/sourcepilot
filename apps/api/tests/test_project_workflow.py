"""Workflow projection through actual API transitions and batched reads."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, select
from sqlalchemy.orm import Session

from sourcepilot.comparison.service import active_quote_revisions, comparison_response
from sourcepilot.persistence.models import Comparison, Project, ProjectSupplier, QuoteValue
from sourcepilot.projects.workflow import project_responses
from tests import test_comparison_snapshot as snapshot_tests

client = snapshot_tests.client
engine = snapshot_tests.engine
database_url = snapshot_tests.database_url
confirm_manual = snapshot_tests.confirm_manual
setup_project = snapshot_tests.setup_project



def workflow(client: TestClient, project_id: str) -> dict:
    response = client.get(f"/projects/{project_id}")
    assert response.status_code == 200, response.text
    summary = response.json()["workflow"]
    listed = client.get("/projects").json()
    assert next(row for row in listed if row["id"] == project_id)["workflow"] == summary
    return summary


def assert_action(client: TestClient, project_id: str, action: str, reason: str) -> dict:
    summary = workflow(client, project_id)
    assert summary["next_action"] == {
        "code": action, "reason_code": reason, "target_stage": summary["current_stage"],
    }
    return summary


def test_brief_eligibility_completion_and_approval(client: TestClient) -> None:
    created = client.post("/projects", json={"name": "Lamp", "original_request": "Desk lamps"})
    key = created.json()["id"]
    assert created.json()["workflow"]["next_action"]["reason_code"] == "BRIEF_ANALYSIS_AVAILABLE"
    assert_action(client, key, "ANALYZE_BRIEF", "BRIEF_ANALYSIS_AVAILABLE")
    payload = {"product_name": "Lamp", "category": None, "quantity": None,
               "destination": None, "delivery_target": None, "target_unit_price": None,
               "requirements": []}
    assert client.patch(f"/projects/{key}/brief", json=payload).status_code == 200
    assert_action(client, key, "COMPLETE_BRIEF", "BRIEF_INCOMPLETE")
    payload.update(category="Lighting", quantity=100, destination="Manila",
                   delivery_target={"kind": "DATE", "date": "2027-01-01"})
    brief = client.patch(f"/projects/{key}/brief", json=payload).json()
    assert_action(client, key, "APPROVE_BRIEF", "BRIEF_APPROVAL_REQUIRED")
    assert client.post(f"/projects/{key}/brief/approve", json={
        "expected_brief_revision": brief["brief_revision"],
    }).status_code == 200
    assert_action(client, key, "DISCOVER_SUPPLIERS", "SUPPLIERS_NOT_DISCOVERED")


def test_shortlist_counts_and_stale_priority(client: TestClient, engine: Engine) -> None:
    key, selected = setup_project(client)
    for supplier_id in selected:
        assert client.patch(f"/projects/{key}/suppliers/{supplier_id}",
                            json={"shortlisted": False}).status_code == 200
    assert_action(client, key, "REVIEW_SHORTLIST", "SHORTLIST_EMPTY")
    candidates = client.get(f"/projects/{key}/suppliers").json()["suppliers"]
    for index, supplier in enumerate(candidates[:4]):
        assert client.patch(f"/projects/{key}/suppliers/{supplier['id']}",
                            json={"shortlisted": True}).status_code == 200
        expected = "SHORTLIST_OVER_LIMIT" if index == 3 else "SHORTLIST_APPROVAL_REQUIRED"
        action = "REVIEW_SHORTLIST" if index == 3 else "APPROVE_SHORTLIST"
        assert_action(client, key, action, expected)
    # A saved preference does not hide upstream work needing attention.
    assert client.put(f"/projects/{key}/preferred-supplier", json={
        "supplier_id": selected[0],
    }).status_code == 200
    with Session(engine) as session:
        project = session.get(Project, UUID(key))
        assert project is not None
        project.brief_revision += 1
        session.commit()
    summary = assert_action(client, key, "REFRESH_SUPPLIERS", "SUPPLIER_EVALUATIONS_STALE")
    assert summary["suppliers_stale"] is True
    assert client.post(f"/projects/{key}/suppliers/discover").status_code == 200
    assert workflow(client, key)["suppliers_stale"] is False


def test_two_quotes_missing_third_comparison_and_decision(client: TestClient, engine: Engine) -> None:
    key, suppliers = setup_project(client)
    assert_action(client, key, "COMPLETE_QUOTES", "INSUFFICIENT_CONFIRMED_QUOTES")
    first = confirm_manual(client, key, suppliers[0])
    assert workflow(client, key)["confirmed_quote_count"] == 1
    assert_action(client, key, "COMPLETE_QUOTES", "INSUFFICIENT_CONFIRMED_QUOTES")
    confirm_manual(client, key, suppliers[1])
    summary = assert_action(client, key, "GENERATE_COMPARISON", "COMPARISON_NOT_GENERATED")
    assert summary["confirmed_quote_count"] == 2
    assert summary["shortlist_count"] == 3
    assert summary["comparison_ready"] is True
    generated = client.post(f"/projects/{key}/comparison/generate")
    assert generated.status_code == 201
    assert_action(client, key, "RECORD_PREFERENCE", "PREFERENCE_NOT_RECORDED")
    choice = client.put(f"/projects/{key}/preferred-supplier", json={"supplier_id": suppliers[2]})
    assert choice.status_code == 200
    assert choice.json()["workflow"]["next_action"]["code"] == "MANAGE_PREFERENCE"
    assert_action(client, key, "MANAGE_PREFERENCE", "PREFERENCE_RECORDED")
    assert client.get(f"/projects/{key}/comparison").json() == generated.json()
    # Fingerprint-only change: no stored stale flag or revision bump required.
    with Session(engine) as session:
        value = session.scalars(select(QuoteValue).where(
            QuoteValue.quote_id == UUID(first), QuoteValue.field_key == "unit_price",
        )).one()
        value.current_value = "4.75"
        session.commit()
    summary = assert_action(client, key, "REGENERATE_COMPARISON", "COMPARISON_STALE")
    assert summary["comparison_stale"] is True
    with Session(engine) as session:
        snapshot = session.get(Comparison, UUID(generated.json()["id"]))
        assert snapshot is not None
        assert comparison_response(session, snapshot)["stale"] is True
        assert len(active_quote_revisions(session, UUID(key))) == summary["confirmed_quote_count"]
    assert client.post(f"/projects/{key}/comparison/generate").status_code == 201
    assert_action(client, key, "MANAGE_PREFERENCE", "PREFERENCE_RECORDED")


def test_quote_membership_exclusion_and_single_supplier(client: TestClient, engine: Engine) -> None:
    key, suppliers = setup_project(client)
    confirm_manual(client, key, suppliers[0])
    confirm_manual(client, key, suppliers[1])
    for supplier_id in suppliers[1:]:
        assert client.patch(f"/projects/{key}/suppliers/{supplier_id}",
                            json={"shortlisted": False}).status_code == 200
    assert client.post(f"/projects/{key}/shortlist/approve").status_code == 200
    summary = assert_action(client, key, "COMPLETE_QUOTES", "INSUFFICIENT_CONFIRMED_QUOTES")
    assert summary["confirmed_quote_count"] == 1
    assert summary["shortlist_count"] == 1
    assert summary["comparison_ready"] is False
    assert client.post(f"/projects/{key}/comparison/generate").status_code == 409
    with Session(engine) as session:
        row = session.get(ProjectSupplier, (UUID(key), UUID(suppliers[0])))
        assert row is not None
        row.dismissed = True
        session.commit()
    assert workflow(client, key)["confirmed_quote_count"] == 0


def test_batched_projection_read_only_and_no_comparison_payload(client: TestClient, engine: Engine) -> None:
    key, suppliers = setup_project(client)
    confirm_manual(client, key, suppliers[0])
    confirm_manual(client, key, suppliers[1])
    assert client.post(f"/projects/{key}/comparison/generate").status_code == 201
    other = client.post("/projects", json={"name": "Other", "original_request": "Source"}).json()["id"]
    statements: list[str] = []

    def capture(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        counts = []
        for ids in ([key], [key, other]):
            with Session(engine) as session:
                projects = list(session.scalars(select(Project).where(
                    Project.id.in_([UUID(item) for item in ids]),
                )))
                statements.clear()
                result = project_responses(session, projects)
                assert len(result) == len(ids)
                assert not session.new and not session.dirty and not session.deleted
                assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
                assert all("comparison_payload" not in statement for statement in statements)
                counts.append(len(statements))
        assert counts[0] == counts[1]
        assert counts[0] <= 10
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    before = workflow(client, key)
    renamed = client.patch(f"/projects/{key}", json={"name": "Renamed"}).json()
    assert renamed["workflow"] == before
    # Existing ownership API tests cover foreign projects; list summaries only project owned inputs.
    assert client.get("/projects/00000000-0000-0000-0000-000000000000").status_code == 404
