import pytest
from fastapi.testclient import TestClient

from sourcepilot.main import app


def test_health_returns_ok_without_database_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
