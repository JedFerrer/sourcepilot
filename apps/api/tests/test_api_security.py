"""Valid-payload authorization regression matrix using existing isolated fixtures."""
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from sourcepilot.main import app
from sourcepilot.persistence.base import Base
from sourcepilot.persistence.models import DemoSession, Project
from sourcepilot.session.settings import DEMO_SESSION_COOKIE_NAME
from tests.test_manual_quotes import setup_shortlist
from tests.test_pdf_quotes import client, database_url, engine, pdf_bytes  # noqa: F401


@pytest.mark.parametrize("identity", ["missing", "invalid", "expired", "foreign"])
def test_all_protected_routes_reject_unowned_valid_requests(
    client: TestClient, engine: Engine, identity: str, monkeypatch: pytest.MonkeyPatch,  # noqa: F811
) -> None:
    project_id, supplier_id, _ = setup_shortlist(client)
    quote = client.post(f"/projects/{project_id}/quotes/manual", json={"supplier_id": supplier_id}).json()
    quote_id = quote["id"]
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        owner = session.get(DemoSession, project.demo_session_id)
        assert owner is not None
        if identity == "expired":
            owner.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            session.commit()
    if identity != "expired":
        client.cookies.clear()
    if identity == "invalid":
        client.cookies.set(DEMO_SESSION_COOKIE_NAME, "invalid-session-token")
    elif identity == "foreign":
        assert client.post("/demo-session").status_code == 204
    def forbidden(*args, **kwargs):
        raise AssertionError("Denied requests must not invoke processing, storage, or model clients")
    monkeypatch.setattr("sourcepilot.main.run_pdf_quote_processing", forbidden)
    monkeypatch.setattr("sourcepilot.main.OpenAIResponsesClient.from_environment", forbidden)
    monkeypatch.setattr("sourcepilot.documents.storage.LocalDocumentStorage.put", forbidden)
    with engine.connect() as connection:
        before = {table.name: connection.execute(select(table)).all() for table in Base.metadata.sorted_tables}
    brief = {"product_name": None, "category": None, "quantity": None, "destination": None,
             "delivery_target": None, "target_unit_price": None, "requirements": []}
    prefix = f"/projects/{project_id}"
    routes = [
        ("GET", "/projects", None), ("POST", "/projects", {"name": "Denied", "original_request": "Valid"}),
        ("GET", prefix, None), ("PATCH", prefix, {"name": "Denied"}),
        ("PUT", prefix + "/preferred-supplier", {"supplier_id": supplier_id}),
        ("GET", prefix + "/brief", None), ("PATCH", prefix + "/brief", brief),
        ("POST", prefix + "/brief/approve", {"expected_brief_revision": 1}),
        ("POST", prefix + "/brief/analyze", None), ("POST", prefix + "/brief/clarifications", None),
        ("POST", prefix + "/suppliers/discover", None), ("GET", prefix + "/suppliers", None),
        ("PATCH", prefix + f"/suppliers/{supplier_id}", {"shortlisted": False}),
        ("POST", prefix + f"/suppliers/{supplier_id}/explanation", None),
        ("POST", prefix + "/shortlist/approve", None), ("GET", prefix + "/quotes", None),
        ("POST", prefix + "/quotes/manual", {"supplier_id": supplier_id}),
        ("POST", prefix + "/quotes/upload", None),
        ("GET", f"/quotes/{quote_id}", None), ("PATCH", f"/quotes/{quote_id}", {"notes": "Denied"}),
        ("POST", f"/quotes/{quote_id}/confirm", None), ("POST", f"/quotes/{quote_id}/retry", None),
        ("POST", f"/quotes/{quote_id}/manual-fallback", {}),
        ("POST", prefix + "/comparison/generate", None), ("GET", prefix + "/comparison", None),
        ("POST", prefix + "/comparison/analysis", None),
        ("POST", prefix + "/comparison/advice", {"snapshot_id": str(uuid4())}),
    ]
    for method, path, payload in routes:
        if identity == "foreign" and path == "/projects":
            continue  # These are session collections, not foreign-resource operations.
        if path.endswith("/upload"):
            response = client.post(path, data={"supplier_id": supplier_id},
                                   files={"file": ("quote.pdf", pdf_bytes(), "application/pdf")})
        else:
            response = client.request(method, path, json=payload)
        assert response.status_code == (404 if identity == "foreign" else 401), (method, path, response.text)
    with engine.connect() as connection:
        after = {table.name: connection.execute(select(table)).all() for table in Base.metadata.sorted_tables}
    # Session last-seen is activity metadata; every domain table is unchanged.
    assert {k: v for k, v in before.items() if k != "demo_sessions"} == {
        k: v for k, v in after.items() if k != "demo_sessions"}
    assert all("test" not in getattr(route, "path", "") and "expire" not in getattr(route, "path", "")
               for route in app.routes if hasattr(route, "path"))



def test_non_upload_limit_preserves_exact_body_and_rejects_without_domain_changes(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,  # noqa: F811
) -> None:
    monkeypatch.setenv("API_MAX_REQUEST_BYTES", "128")
    body = json.dumps({"name": "Boundary", "original_request": "Source bags"}).encode()
    body += b" " * (128 - len(body))
    accepted = client.post("/projects", content=body, headers={"Content-Type": "application/json"})
    assert accepted.status_code == 201 and accepted.json()["original_request"] == "Source bags"
    before = client.get("/projects").json()
    rejected = client.post("/projects", content=body + b" ", headers={"Content-Type": "application/json"})
    assert rejected.status_code == 413
    assert rejected.json() == {"error": {"code": "REQUEST_TOO_LARGE", "message": "Request body is too large."}}
    assert client.get("/projects").json() == before
