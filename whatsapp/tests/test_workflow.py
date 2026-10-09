import asyncio
from time import monotonic
from unittest.mock import AsyncMock

import httpx
import pytest

from whatsapp.contracts import Incoming, ApiError
from whatsapp.workflow import Workflow

PHONE = "+34600123456"


def setup(tmp_path):
    api, messenger = AsyncMock(), AsyncMock()
    api.slots.return_value = [
        {"timestamp": f"2026-10-07T{hour:02}:00:00"} for hour in range(10, 21)]
    api.reserve.return_value = {"bookings": [{"timestamp": "2026-10-07T10:00:00"}]}
    api.bookings.return_value = [{"id": 8, "timestamp": "2026-10-07T10:00:00"}]
    flow = Workflow(api, messenger)
    return flow, api, messenger, flow.sessions


def option(messenger, title):
    rows = messenger.send.await_args.args[1]["interactive"]["action"]["sections"][0]["rows"]
    return next(row["id"] for row in rows if row["title"] == title)


def test_reserve_pages_identity_duplicate_and_stale(tmp_path):
    async def scenario():
        flow, api, messenger, store = setup(tmp_path)
        await flow.handle(Incoming("1", PHONE, "hola"))
        await flow.handle(Incoming("2", PHONE, selection=option(messenger, "Reservar Cita")))
        await flow.handle(Incoming("3", PHONE, selection=option(messenger, "miércoles 07/10")))
        assert len(messenger.send.await_args.args[1]["interactive"]["action"]["sections"][0]["rows"]) == 9
        await flow.handle(Incoming("5", PHONE, selection=option(messenger, "Más opciones")))
        assert option(messenger, "20:00")
        await flow.handle(Incoming("6", PHONE, selection=option(messenger, "Anterior")))
        selected = option(messenger, "10:00")
        await flow.handle(Incoming("7", PHONE, selection=selected))
        assert "Reserva aceptada. Nos vemos el miércoles 7 de octubre a las 10:00." == messenger.send.await_args.args[1]["text"]["body"]
        assert api.reserve.await_args.args[:2] == (PHONE, "2026-10-07T10:00:00")
        await flow.handle(Incoming("7", PHONE, selection=selected))
        await flow.handle(Incoming("8", PHONE, selection=selected))
        await flow.handle(Incoming("9", "+447700900123", selection=selected))
        assert api.reserve.await_count == 1
    asyncio.run(scenario())


def test_registration_cancel_list(tmp_path):
    async def scenario():
        flow, api, messenger, _ = setup(tmp_path)
        api.customer.side_effect = ApiError("CLIENT_NOT_FOUND")
        await flow.handle(Incoming("1", PHONE, "hola"))
        await flow.handle(Incoming("2", PHONE, selection=option(messenger, "Reservar Cita")))
        await flow.handle(Incoming("week", PHONE, selection=option(messenger, "miércoles 07/10")))
        await flow.handle(Incoming("slot", PHONE, selection=option(messenger, "10:00")))
        assert "cómo te llamas" in messenger.send.await_args.args[1]["text"]["body"]
        await flow.handle(Incoming("3", PHONE, "Ana"))
        api.create_customer.assert_awaited_once_with(PHONE, "Ana")
        await flow.handle(Incoming("4", PHONE, "menú"))
        await flow.handle(Incoming("5", PHONE, selection=option(messenger, "Cancelar Cita")))
        await flow.handle(Incoming("6", PHONE, selection=option(messenger, "07/10/2026 10:00")))
        api.cancel.assert_awaited_once_with(PHONE, 8)
        assert messenger.send.await_args.args[1]["text"]["body"] == "Cita cancelada con éxito."
    asyncio.run(scenario())


@pytest.mark.parametrize("code", ["UNCERTAIN", "BOOKING_ALREADY_EXISTS", "MONTHLY_LIMIT"])
def test_no_false_confirmation(tmp_path, code):
    async def scenario():
        flow, api, messenger, store = setup(tmp_path)
        store[PHONE] = (monotonic(), {"choices": {"slot": {
            "kind": "slot", "timestamp": "2026-10-07T10:00:00", "request_id": "stable"}}})
        api.reserve.side_effect = ApiError(code)
        await flow.handle(Incoming("1", PHONE, selection="slot"))
        assert "Reserva aceptada" not in str(messenger.send.await_args)
        if code == "UNCERTAIN":
            await flow.handle(Incoming("2", PHONE, selection="slot"))
            assert api.reserve.await_args.args[-1] == "stable"
    asyncio.run(scenario())


def test_delivery_retry_without_repeating_delete(tmp_path):
    async def scenario():
        flow, api, messenger, store = setup(tmp_path)
        store[PHONE] = (monotonic(), {"choices": {"delete": {"kind": "delete", "id": 8}}})
        messenger.send.side_effect = httpx.ConnectError("offline")
        incoming = Incoming("1", PHONE, selection="delete")
        with pytest.raises(httpx.ConnectError):
            await flow.handle(incoming)
        messenger.send.side_effect = None
        await flow.handle(incoming)
        api.cancel.assert_awaited_once()
        assert flow.events[(PHONE, "1")]["sent"]
    asyncio.run(scenario())
