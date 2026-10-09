import asyncio
import hashlib
import hmac
import json
from datetime import datetime
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from whatsapp.booking_api import HttpBookingApi
from whatsapp.contracts import ApiError
from whatsapp.meta_client import MetaWhatsAppClient


def test_existing_api_contract_and_ownership(monkeypatch):
    from calendar_memory import MemoryStore
    from src.api.routes.dependencies import service
    from src.application.barbershop_service import BarbershopService
    from src.config import settings
    from src.main import app
    monkeypatch.setattr(settings, "agent_api_token", "test-channel")
    application = BarbershopService(MemoryStore(), clock=lambda: datetime(2026, 10, 6, 9))
    app.dependency_overrides[service] = lambda: application

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            api = HttpBookingApi(client, "test-channel")
            phone = "+34600123456"
            await api.create_customer(phone, "Ana")
            assert (await api.customer(phone))["name"] == "Ana"
            slots = await api.slots(phone, "current")
            timestamp = slots[0]["timestamp"]
            request_id = "00000000-0000-0000-0000-000000000111"
            booking = (await api.reserve(phone, timestamp, request_id))["bookings"][0]
            assert (await api.reserve(phone, timestamp, request_id))["bookings"][0]["id"] == booking["id"]
            assert {"timestamp": timestamp} not in await api.slots(phone, "current")
            with pytest.raises(ApiError, match="BOOKING_NOT_FOUND"):
                await api.cancel("+447700900123", booking["id"])
            assert len(await api.bookings(phone)) == 1
            await api.cancel(phone, booking["id"])
            assert await api.bookings(phone) == []
            assert {"timestamp": timestamp} in await api.slots(phone, "current")
            # Full interactive journey through the actual api/ endpoints.
            from whatsapp.workflow import Workflow
            from whatsapp.contracts import Incoming
            messenger = AsyncMock()
            workflow = Workflow(api, messenger)
            await workflow.handle(Incoming("hello", phone, "Hola"))
            await workflow.handle(Incoming("reserve", phone, selection="reserve_booking"))
            for event_id in ("day", "hour"):
                rows = messenger.send.await_args.args[1]["interactive"]["action"]["sections"][0]["rows"]
                await workflow.handle(Incoming(event_id, phone, selection=rows[0]["id"]))
            assert "Reserva aceptada" in messenger.send.await_args.args[1]["text"]["body"]
            assert len(await api.bookings(phone)) == 1
            await workflow.handle(Incoming("cancel", phone, selection="cancel_booking"))
            rows = messenger.send.await_args.args[1]["interactive"]["action"]["sections"][0]["rows"]
            await workflow.handle(Incoming("confirm_cancel", phone, selection=rows[0]["id"]))
            assert messenger.send.await_args.args[1]["text"]["body"] == "Cita cancelada con éxito."
            assert await api.bookings(phone) == []
    try:
        asyncio.run(scenario())
    finally:
        app.dependency_overrides.pop(service, None)


def test_signed_webhook_and_wrong_receiver(monkeypatch, tmp_path):
    from whatsapp.main import app, settings
    monkeypatch.setattr(settings, "meta_app_secret", "secret")
    monkeypatch.setattr(settings, "agent_api_token", "test-channel")
    monkeypatch.setattr(settings, "meta_phone_number_id", "123")
    with TestClient(app) as client:
        app.state.workflow = AsyncMock()
        payload = {"object": "whatsapp_business_account", "entry": [{"changes": [{
            "field": "messages", "value": {"metadata": {"phone_number_id": "123"},
            "messages": [{"id": "wamid.test", "from": "34600123456", "text": {"body": "hola"}}]}}]}]}
        body = json.dumps(payload).encode()
        assert client.post("/webhook", content=body).status_code == 403
        signature = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
        assert client.post("/webhook", content=body, headers={"X-Hub-Signature-256": signature}).status_code == 200
        incoming = app.state.workflow.handle.await_args.args[0]
        assert incoming.phone == "+34600123456"
        monkeypatch.setattr(settings, "meta_phone_number_id", "other")
        assert client.post("/webhook", content=body, headers={"X-Hub-Signature-256": signature}).status_code == 200
        assert app.state.workflow.handle.await_count == 1


def test_http_adapter_timeout_and_meta_payload(monkeypatch):
    async def scenario():
        def offline(request):
            raise httpx.ReadTimeout("timeout")
        async with httpx.AsyncClient(transport=httpx.MockTransport(offline), base_url="http://test") as client:
            with pytest.raises(ApiError, match="UNCERTAIN"):
                await HttpBookingApi(client, "token").bookings("+34600123456")
        transport_client = httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"messages": [{"id": "test"}]})))
        post = AsyncMock(return_value=httpx.Response(200, request=httpx.Request("POST", "https://test")))
        transport_client.post = post
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: transport_client)
        await MetaWhatsAppClient("token", "123", "v23.0").send("+34600123456", {"type": "text", "text": {"body": "Hola"}})
        assert post.await_args.kwargs["json"]["to"] == "34600123456"
    asyncio.run(scenario())
