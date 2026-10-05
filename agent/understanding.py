"""Small, grounded intent contract for the local model.

The model extracts words from the message; application code resolves dates.
It never supplies a made-up timestamp to a booking tool.
"""

import re
import unicodedata
from datetime import date, time, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Intent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal[
        "get_client", "create_client", "update_client", "get_available_slots",
        "list_bookings", "create_booking", "delete_booking",
        "continue", "out_of_scope", "greeting", "thanks", "frustration", "abort",
    ]
    name: str | None = Field(default=None, min_length=1, max_length=59)
    date_text: str | None = Field(default=None, description="Fecha copiada literalmente del mensaje, p. ej. hoy, mañana o martes 6 de octubre. No calcular ni inventar.")
    time_text: str | None = Field(default=None, description="Hora copiada literalmente del mensaje, p. ej. a las 5 o 17:00. No convertir ni inventar.")
    booking_id: int | None = Field(default=None, ge=1)
    week: Literal["current", "next", "both"] | None = None
    count: int | None = Field(default=None, ge=1, le=5)


def extraction_schema():
    def simplify(value):
        if isinstance(value, dict):
            return {k: simplify(v) for k, v in value.items() if k not in {
                "format", "pattern", "minLength", "maxLength", "minimum",
                "maximum", "default", "title",
            }}
        return [simplify(v) for v in value] if isinstance(value, list) else value
    return dict(simplify(Intent.model_json_schema()), title="Intent")


def normalize(text):
    return " ".join("".join(c for c in unicodedata.normalize("NFD", text.casefold())
                            if unicodedata.category(c) != "Mn").split())


def literal_span(message, value):
    """A model field is evidence only if it occurs in the current user message."""
    if value and normalize(value) in normalize(message):
        return value
    return None


WEEKDAYS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
MONTHS = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre")
NUMBERS = {word: i for i, word in enumerate(("cero", "una", "dos", "tres", "cuatro",
           "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce"))}
HOUR = r"(?:\d{1,2}|" + "|".join(NUMBERS) + r")"
TIME = re.compile(r"(?:\ba las?\s+|\blas?\s+)(" + HOUR +
                  r")(?::(\d{2})|\s+y\s+(media|cuarto)|\s+(menos cuarto))?\b")


def read_day(text, today):
    """Resolve supported Spanish date expressions, never guess a missing day."""
    text = normalize(text)
    match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if match:
        return date(*map(int, match.groups()))
    match = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\b", text)
    if match:
        day, month, year = match.groups()
        return date(int(year or today.year), int(month), int(day))
    match = re.search(r"\b(\d{1,2}) de (" + "|".join(MONTHS) + r")(?: (?:de )?(\d{4}))?\b", text)
    if match:
        day, month, year = match.groups()
        return date(int(year or today.year), MONTHS.index(month)+1, int(day))
    if "pasado manana" in text:
        return today + timedelta(days=2)
    if re.search(r"\besta (?:manana|tarde|noche)\b", text):
        return today
    if re.search(r"(?<!la )\bmanana\b", text):
        return today + timedelta(days=1)
    if re.search(r"\bhoy\b", text):
        return today
    match = re.search(r"\b(" + "|".join(WEEKDAYS) + r")\b(?:\s+(\d{1,2})\b)?", text)
    if match:
        weekday, number = match.groups()
        if number:
            day = date(today.year, today.month, int(number))
            if day.weekday() != WEEKDAYS.index(weekday):
                raise ValueError("weekday and date disagree")
            return day
        index = WEEKDAYS.index(weekday)
        if re.search(r"semana (?:que viene|siguiente|proxima)|proxima semana", text):
            return today - timedelta(days=today.weekday()) + timedelta(days=7+index)
        return today + timedelta(days=(index-today.weekday()) % 7)
    match = re.search(r"\bdia (\d{1,2})\b", text)
    if match:
        return date(today.year, today.month, int(match[1]))
    return None


def read_times(text, bare=False):
    text = normalize(text)
    match = TIME.search(text)
    if not match:
        match = re.search(r"\b(\d{1,2}):(\d{2})\b", text)
    if not match and bare:
        match = re.fullmatch(r"(" + HOUR + r")(?::(\d{2}))?(?: (?:de la )?(?:tarde|noche|manana)|\s*[ap]m)?[.!]?", text)
    if not match:
        return None
    groups = match.groups()
    hour = int(groups[0]) if groups[0].isdigit() else NUMBERS[groups[0]]
    minute = int(groups[1] or 0)
    if len(groups) == 4:
        minute = 30 if groups[2] == "media" else 15 if groups[2] else minute
        if groups[3]:
            hour, minute = hour-1, 45
    # Validate before using modulo arithmetic.
    time(hour, minute)
    if re.search(r"\b(tarde|noche|pm)\b", text):
        return [time(hour % 12 + 12, minute)] if hour <= 12 else [time(hour, minute)]
    if re.search(r"(?:de la|por la) manana|\bam\b", text):
        return [time(hour % 12, minute)] if hour <= 12 else [time(hour, minute)]
    if ":" in match[0] or hour == 0 or hour > 12:
        return [time(hour, minute)]
    return sorted({time(hour % 12, minute), time(hour % 12 + 12, minute)})


def temporal_details(message, date_text, time_text, today, bare_time=False):
    # Prefer a grounded target span: "cambia del lunes al martes" targets martes.
    date_source = literal_span(message, date_text)
    time_source = literal_span(message, time_text)
    day = read_day(date_source or message, today)
    if day is None and date_source:
        day = read_day(message, today)
    times = read_times(time_source or message, bare=bool(time_source) or bare_time)
    if times is None and time_source:
        times = read_times(message, bare=bare_time)
    return day, times


def references_previous(message):
    return bool(re.search(r"\b(?:ese (?:dia|horario|hueco)|esa hora|(?:te he|he) dicho|reservalo|la misma hora)\b", normalize(message)))


def supplies_name(message, name):
    if not literal_span(message, name):
        return False
    return bool(re.fullmatch(r"(?:(?:me llamo|soy|mi nombre es)\s+)?" + re.escape(normalize(name)) + r"[.!]?", normalize(message)))


def explicit_reservation(message):
    text = normalize(message)
    if re.search(r"\b(?:no|sin)\b.*\b(?:reserv|cita)", text):
        return False
    return bool(re.search(r"\b(?:quiero|quisiera|necesito|puedes|podrias|gustaria)\s+(?:que me\s+)?reserv\w*|\breservame\b|^reserva\b", text))


def requested_count(message):
    match = re.search(r"\b(\d+|uno|un|dos|tres|cuatro|cinco)\s+(?:cortes?|citas?|servicios?|consecutiv[oa]s|seguid[oa]s)\b", normalize(message))
    if not match:
        return None
    value = match[1]
    return int(value) if value.isdigit() else {"uno":1,"un":1,"dos":2,"tres":3,"cuatro":4,"cinco":5}[value]


def conversational_action(message):
    """Cheap, exact conversational turns and an explicit privacy boundary."""
    text = normalize(message).strip(" ¡!¿?.,")
    if re.fullmatch(r"(?:hola|buenas|buenos dias|buenas tardes|buenas noches)(?:,? que tal)?", text):
        return "greeting"
    if re.fullmatch(r"(?:muchas )?gracias(?: por todo)?", text):
        return "thanks"
    if text in {"vaya mierda", "no me entiendes", "esto no funciona", "que desastre"}:
        return "frustration"
    if text in {"olvida eso", "dejalo", "no quiero reservar", "no reserves", "cancela esta peticion"}:
        return "abort"
    if re.search(r"\b(?:clientes|telefonos)\b|datos de otr[oa]s?", text):
        return "out_of_scope"
    return None
