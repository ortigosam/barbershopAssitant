"""Pure calendar rules. No HTTP, database or language-model dependencies."""

import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

DURATION = timedelta(minutes=20)
MAX_MONTHLY = 5


class RuleError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def phone(value: str) -> str:
    value = re.sub(r"[\s().-]", "", value)
    if value.startswith("00"):
        value = "+" + value[2:]
    if re.fullmatch(r"[6789]\d{8}", value):
        value = "+34" + value
    if not re.fullmatch(r"\+[1-9]\d{7,14}", value):
        raise RuleError(
            "INVALID_PHONE",
            "Indica el teléfono con prefijo internacional, por ejemplo +34600123456.",
        )
    return value


@dataclass(frozen=True)
class Appointment:
    id: int
    timestamp: datetime
    telephone: str
    name: str = ""

    @property
    def end(self):
        return self.timestamp + DURATION

    def result(self, now):
        return dict(
            id=self.id,
            timestamp=self.timestamp.isoformat(),
            end=self.end.isoformat(),
            telephone=self.telephone,
            name=self.name,
            status="completed" if self.end <= now else "confirmed",
        )


@dataclass(frozen=True)
class Calendar:
    # Monday=0. Exceptions replace the entire regular day; [] means closed.
    weekly: dict[int, list[tuple[str, str]]]
    exceptions: dict[str, list[tuple[str, str]]]

    def windows(self, day: date):
        return self.exceptions.get(day.isoformat(), self.weekly.get(day.weekday(), []))

    def accepts(self, start: datetime):
        if start.tzinfo is not None or start.second or start.microsecond:
            return False
        for opening, closing in self.windows(start.date()):
            first = datetime.combine(start.date(), time.fromisoformat(opening))
            last = datetime.combine(start.date(), time.fromisoformat(closing))
            if (
                first <= start
                and start + DURATION <= last
                and (start - first) % DURATION == timedelta()
            ):
                return True
        return False

    def validate(self):
        if set(self.weekly) != set(range(7)):
            raise RuleError(
                "INVALID_SCHEDULE",
                "Define los siete días de la semana, incluidos los cerrados.",
            )
        for key in self.exceptions:
            try:
                date.fromisoformat(key)
            except ValueError:
                raise RuleError(
                    "INVALID_SCHEDULE", "Fecha de excepción inválida."
                ) from None
        for windows in [*self.weekly.values(), *self.exceptions.values()]:
            previous = None
            for opening, closing in windows:
                try:
                    first, last = (
                        time.fromisoformat(opening),
                        time.fromisoformat(closing),
                    )
                except (TypeError, ValueError):
                    raise RuleError(
                        "INVALID_SCHEDULE", "Utiliza horas HH:MM."
                    ) from None
                if (
                    first.tzinfo
                    or last.tzinfo
                    or first.second
                    or last.second
                    or first.microsecond
                    or last.microsecond
                ):
                    raise RuleError("INVALID_SCHEDULE", "Utiliza horas locales HH:MM.")
                if first >= last or (previous is not None and first < previous):
                    raise RuleError(
                        "INVALID_SCHEDULE",
                        "Los intervalos deben estar ordenados y no solaparse.",
                    )
                if (
                    datetime.combine(date.min, last) - datetime.combine(date.min, first)
                    < DURATION
                ):
                    raise RuleError(
                        "INVALID_SCHEDULE",
                        "Cada intervalo debe permitir al menos un corte de 20 minutos.",
                    )
                previous = last

    def result(self):
        return deepcopy(
            {
                "weekly": {str(k): v for k, v in self.weekly.items()},
                "exceptions": self.exceptions,
            }
        )


def validate_start(calendar: Calendar, start: datetime, now: datetime):
    if start.tzinfo is not None:
        raise RuleError(
            "INVALID_SLOT", "Usa fecha y hora local de Europe/Madrid sin zona."
        )
    monday = now.date() - timedelta(days=now.weekday())
    if start <= now or start.date() >= monday + timedelta(days=14):
        raise RuleError(
            "INVALID_SLOT",
            "Sólo puedes reservar un horario futuro de esta semana o la siguiente.",
        )
    if not calendar.accepts(start):
        raise RuleError(
            "INVALID_SLOT", "Ese horario está fuera del horario disponible del barbero."
        )


def require_owner(booking, actor, admin=False):
    if booking is None or (not admin and booking.telephone != actor):
        raise RuleError("BOOKING_NOT_FOUND", "No encuentro esa reserva.", 404)


def require_cancellable(booking, now):
    if now >= booking.timestamp:
        raise RuleError(
            "BOOKING_STARTED",
            "Ya no se puede cancelar esta cita.",
            409,
        )
