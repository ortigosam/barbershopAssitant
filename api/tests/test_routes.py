from datetime import datetime

import pytest
from calendar_memory import MemoryStore
from fastapi.testclient import TestClient
from src.api.routes.calendar import service
from src.application.calendar_service import CalendarService
from src.config import settings
from src.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "agent_api_token", "test-agent")
    monkeypatch.setattr(settings, "admin_api_token", "test-admin")
    app.dependency_overrides[service] = lambda: CalendarService(
        store, clock=lambda: datetime(2026, 10, 2, 9)
    )
    store = MemoryStore()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_authentication_and_identity(client):
    assert client.get("/bookings").status_code == 401
    headers = {"Authorization": "Bearer test-agent", "X-Customer-Phone": "+34600123456"}
    assert (
        client.post("/clients/me", headers=headers, json={"name": "Ana"}).status_code
        == 201
    )
    payload = {
        "timestamp": "2026-10-05T10:00:00",
        "count": 1,
        "request_id": "00000000-0000-0000-0000-000000000001",
    }
    result = client.post("/bookings", headers=headers, json=payload)
    assert result.status_code == 201
    identifier = result.json()["bookings"][0]["id"]
    foreign = {**headers, "X-Customer-Phone": "+447700900123"}
    assert client.delete(f"/bookings/{identifier}", headers=foreign).status_code == 404
    assert (
        client.put(
            f"/bookings/{identifier}",
            headers=headers,
            json={"telephone": "+447700900123"},
        ).status_code
        == 422
    )
    assert client.get("/admin/settings", headers=headers).status_code == 401
    assert client.delete(f"/bookings/{identifier}", headers=headers).status_code == 204


def test_admin_and_static_shell(client):
    headers = {"Authorization": "Bearer test-admin"}
    assert client.get("/admin/settings", headers=headers).status_code == 200
    assert client.get("/").status_code == 200
    assert "La agenda" in client.get("/").text
