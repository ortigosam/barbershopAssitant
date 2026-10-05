"""Conversation integration: actual tools and HTTP API, disposable in-memory data."""

from datetime import datetime

import pytest
from calendar_memory import MemoryStore
from fastapi.testclient import TestClient
from src.api.routes.calendar import service
from src.application.calendar_service import CalendarService
from src.config import settings
from src.main import app

from agent import http_client


@pytest.fixture
def booking_api(monkeypatch):
    clock = lambda: datetime(2026, 10, 2, 12)
    application = CalendarService(MemoryStore(), clock=clock)
    monkeypatch.setattr(settings, "agent_api_token", "test-channel")
    monkeypatch.setenv("AGENT_API_TOKEN", "test-channel")
    app.dependency_overrides[service] = lambda: application
    client = TestClient(app)
    monkeypatch.setattr(http_client, "_client", client)
    try:
        yield application, clock
    finally:
        client.close()
        app.dependency_overrides.pop(service, None)
