"""Deterministic menu use case. Business rules remain in the booking API."""
import asyncio
import logging
from time import monotonic
from datetime import datetime
from uuid import uuid4

from whatsapp.contracts import ApiError, BookingApi, Incoming, Messenger
from whatsapp.logging_config import mask_identifier, mask_phone


logger = logging.getLogger(__name__)

DAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MONTHS = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def date_text(timestamp):
    date = datetime.fromisoformat(timestamp)
    return f"{DAYS[date.weekday()]} {date.day} de {MONTHS[date.month-1]} a las {date:%H:%M}"


def text(body):
    return {"type": "text", "text": {"body": body}}


def menu(state, body, options, page=0):
    """At most eight choices plus navigation, under Meta's ten-row limit."""
    page = max(0, min(page, max(0, (len(options)-1)//8)))
    visible = options[page*8:(page+1)*8]
    if page:
        visible = [*visible, ("Anterior", {"kind": "page", "page": page-1})]
    if (page+1)*8 < len(options):
        visible = [*visible, ("Más opciones", {"kind": "page", "page": page+1})]
    state["menu"] = {"body": body, "options": options}
    state["choices"] = {}
    rows = []
    for title, action in visible:
        identifier = {"reserve": "reserve_booking", "cancel": "cancel_booking"}.get(
            action["kind"], uuid4().hex
        )
        state["choices"][identifier] = action
        rows.append({"id": identifier, "title": title[:24]})
    return {"type": "interactive", "interactive": {
        "type": "list", "body": {"text": body}, "action": {
            "button": "Seleccionar", "sections": [{"title": "Opciones", "rows": rows}]}}}


def main_menu(state, body="¿Qué necesitas hacer?"):
    state.clear()
    return menu(state, body, [
        ("Reservar Cita", {"kind": "reserve"}),
        ("Cancelar Cita", {"kind": "cancel"}),
    ])


class Workflow:
    def __init__(self, api: BookingApi, messenger: Messenger):
        self.api, self.messenger = api, messenger
        self.sessions = {}
        self.events = {}
        self.lock = asyncio.Lock()

    async def handle(self, message: Incoming):
        async with self.lock:
            logger.info("workflow_start id=%s phone=%s selection=%s",
                        mask_identifier(message.id), mask_phone(message.phone),
                        message.selection or "-")
            now = monotonic()
            self.sessions = {k: v for k, v in self.sessions.items() if now-v[0] < 3600}
            self.events = {k: v for k, v in self.events.items() if now-v["time"] < 3600}
            key = (message.phone, message.id)
            previous = self.events.get(key)
            if previous:
                if not previous["sent"]:
                    await self.messenger.send(message.phone, previous["reply"])
                    previous["sent"] = True
                return
            state = self.sessions.get(message.phone, (now, {}))[1]
            try:
                reply = await self.transition(message, state)
            except ApiError as error:
                logger.warning("workflow_api_error id=%s phone=%s code=%s",
                               mask_identifier(message.id), mask_phone(message.phone), error.code)
                reply = self.error(state, error)
            self.sessions[message.phone] = (now, state)
            self.events[key] = {"reply": reply, "sent": False, "time": now}
            await self.messenger.send(message.phone, reply)
            self.events[key]["sent"] = True
            logger.info("workflow_complete id=%s phone=%s reply_type=%s",
                        mask_identifier(message.id), mask_phone(message.phone),
                        reply.get("type", "unknown"))

    def error(self, state, error):
        if error.code == "UNCERTAIN":
            # Retain the offered action and its idempotency key for safe retries.
            return text("No puedo confirmar el resultado porque la API no ha respondido. "
                        "Escribe menú y vuelve a intentarlo en unos segundos.")
        messages = {
            "BOOKING_ALREADY_EXISTS": "Ese horario ya no está disponible. Consulta otro hueco.",
            "INVALID_SLOT": "Ese horario ya no está disponible. Consulta otro hueco.",
            "MONTHLY_LIMIT": "Puedes tener como máximo cinco citas por mes, incluyendo las realizadas.",
            "BOOKING_NOT_FOUND": "No encuentro esa cita entre tus reservas.",
            "BOOKING_STARTED": "Ya no se puede cancelar esta cita.",
            "CLIENT_NOT_FOUND": "No encuentro tu ficha. Selecciona Reservar Cita para crearla.",
        }
        return main_menu(state, messages.get(error.code,
                         "No he podido completar la operación. Inténtalo de nuevo más tarde."))

    async def transition(self, message, state):
        phone = message.phone
        if message.text.strip().lower() in ("menu", "menú", "inicio"):
            return main_menu(state)
        if state.get("awaiting_name") and message.text:
            name = message.text.strip()
            if not 1 <= len(name) <= 59:
                return text("Indica tu nombre, entre 1 y 59 caracteres.")
            try:
                await self.api.create_customer(phone, name)
            except ApiError as error:
                if error.code != "CLIENT_ALREADY_EXISTS":
                    raise
            state.pop("awaiting_name", None)
            return await self.reserve(phone, state, state.pop("pending_slot"))
        if not message.selection:
            return main_menu(state)
        roots = {"reserve_booking": "reserve", "cancel_booking": "cancel"}
        action = ({"kind": roots[message.selection]} if message.selection in roots
                  else state.get("choices", {}).get(message.selection))
        if not action:
            return main_menu(state, "Ese menú ha caducado. ¿Qué necesitas hacer?")
        kind = action["kind"]
        if kind == "page":
            saved = state["menu"]
            return menu(state, saved["body"], saved["options"], action["page"])
        if kind == "reserve":
            state.clear()
            return await self.available_days(phone, state)
        if kind == "day":
            slots = await self.api.slots(phone, action["week"])
            choices = [(slot["timestamp"][11:16], {
                "kind": "slot", "timestamp": slot["timestamp"], "request_id": str(uuid4())})
                for slot in slots if slot["timestamp"][:10] == action["day"]]
            if not choices:
                return main_menu(state, "Ese día ya no tiene huecos disponibles.")
            return menu(state, f"Elige una hora para el {action['day'][8:10]}/{action['day'][5:7]}.", choices)
        if kind == "slot":
            try:
                await self.api.customer(phone)
            except ApiError as error:
                if error.code != "CLIENT_NOT_FOUND":
                    raise
                state["awaiting_name"] = True
                state["pending_slot"] = action
                return text("Para confirmar tu primera reserva, ¿cómo te llamas? Escribe menú para volver al inicio.")
            return await self.reserve(phone, state, action)
        if kind == "cancel":
            bookings = await self.api.bookings(phone)
            if not bookings:
                return main_menu(state, "No tienes próximas citas.")
            return menu(state, "¿Qué cita quieres cancelar?", [
                (datetime.fromisoformat(b["timestamp"]).strftime("%d/%m/%Y %H:%M"),
                 {"kind": "delete", "id": b["id"]}) for b in bookings])
        if kind == "delete":
            await self.api.cancel(phone, action["id"])
            state.clear()
            return text("Cita cancelada con éxito.")
        return main_menu(state)

    async def available_days(self, phone, state):
        """Offer dates from this and next week in one message."""
        current, following = await asyncio.gather(
            self.api.slots(phone, "current"), self.api.slots(phone, "next")
        )
        choices = []
        for week, slots in (("current", current), ("next", following)):
            for day in sorted({slot["timestamp"][:10] for slot in slots}):
                choices.append((
                    f"{DAYS[datetime.fromisoformat(day).weekday()]} {day[8:10]}/{day[5:7]}",
                    {"kind": "day", "day": day, "week": week},
                ))
        if not choices:
            return main_menu(state, "No hay huecos disponibles. ¿Qué necesitas hacer?")
        return menu(state, "¿Qué día prefieres?", choices)

    async def reserve(self, phone, state, action):
        result = await self.api.reserve(phone, action["timestamp"], action["request_id"])
        confirmed = result["bookings"][0]["timestamp"]
        state.clear()
        return text(f"Reserva aceptada. Nos vemos el {date_text(confirmed)}.")
