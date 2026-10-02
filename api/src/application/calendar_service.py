"""Use cases. Rules are enforced here for both customers and the admin web."""

import hashlib
import json
from collections import Counter
from datetime import datetime, time, timedelta

from src.application.ports import CalendarStore
from src.domain.calendar import (
    DURATION,
    MAX_MONTHLY,
    Calendar,
    RuleError,
    phone,
    require_not_started,
    require_owner,
    validate_start,
)
from src.domain.schedule import madrid_now


class CalendarService:
    def __init__(self, store: CalendarStore, clock=madrid_now):
        self.store, self.clock = store, clock

    def customer(self, actor):
        with self.store.transaction() as tx:
            result = tx.customer(phone(actor))
            if not result:
                raise RuleError(
                    "CLIENT_NOT_FOUND", "No encuentro una ficha con ese teléfono.", 404
                )
            return result

    def save_customer(self, actor, name, create_only=False):
        name = name.strip()
        if not 1 <= len(name) <= 59:
            raise RuleError(
                "INVALID_NAME", "Indica un nombre de entre 1 y 59 caracteres."
            )
        with self.store.transaction() as tx:
            actor = phone(actor)
            if create_only and tx.customer(actor):
                raise RuleError(
                    "CLIENT_ALREADY_EXISTS", "La ficha de cliente ya existe.", 409
                )
            return tx.save_customer(actor, name)

    def availability(self, week, count=1):
        if week not in ("current", "next") or not 1 <= count <= 5:
            raise RuleError("INVALID_REQUEST", "Semana o número de citas inválidos.")
        now = self.clock()
        monday = now.date() - timedelta(days=now.weekday())
        first = monday + timedelta(days=7 if week == "next" else 0)
        last = first + timedelta(days=7)
        with self.store.transaction() as tx:
            calendar, _ = tx.calendar()
            occupied = tx.appointments(
                datetime.combine(first, time.min), datetime.combine(last, time.min)
            )
            slots = []
            for offset in range(7):
                day = first + timedelta(days=offset)
                for opening, closing in calendar.windows(day):
                    start = datetime.combine(day, time.fromisoformat(opening))
                    end = datetime.combine(day, time.fromisoformat(closing))
                    while start + DURATION * count <= end:
                        if start > now and not any(
                            start < b.end and start + DURATION * count > b.timestamp
                            for b in occupied
                        ):
                            slots.append({"timestamp": start.isoformat()})
                        start += DURATION
            return dict(
                week=week,
                week_start=str(first),
                week_end=str(last - timedelta(days=1)),
                slot_duration_minutes=20,
                count=count,
                slots=slots,
            )

    def _free(self, tx, start, exclude=None):
        if any(b.id != exclude for b in tx.appointments(start, start + DURATION)):
            raise RuleError(
                "BOOKING_ALREADY_EXISTS",
                "Ese horario ya no está disponible. Puedo consultar otros horarios.",
                409,
            )

    def _quota(self, tx, actor, starts, exclude=None):
        for (year, month), amount in Counter((s.year, s.month) for s in starts).items():
            first = datetime(year, month, 1)
            last = (
                datetime(year + 1, 1, 1)
                if month == 12
                else datetime(year, month + 1, 1)
            )
            booked = [
                b
                for b in tx.appointments(first, last, actor)
                if b.id != exclude and b.timestamp >= first
            ]
            if len(booked) + amount > MAX_MONTHLY:
                raise RuleError(
                    "MONTHLY_LIMIT",
                    "Puedes tener como máximo cinco citas por mes, incluyendo las ya realizadas.",
                    409,
                )

    def reserve(self, actor, timestamp, count, request_id):
        actor = phone(actor)
        if not 1 <= count <= 5:
            raise RuleError(
                "INVALID_COUNT", "Puedes reservar entre una y cinco citas consecutivas."
            )
        fingerprint = hashlib.sha256(
            json.dumps([actor, timestamp.isoformat(), count]).encode()
        ).hexdigest()
        with self.store.transaction() as tx:
            now = self.clock()
            receipt = tx.receipt(request_id)
            if receipt:
                if receipt["fingerprint"] != fingerprint:
                    raise RuleError(
                        "REQUEST_CONFLICT",
                        "Esa operación pertenece a otra petición.",
                        409,
                    )
                if receipt["invalidated"]:
                    raise RuleError(
                        "BOOKING_NOT_FOUND",
                        "La reserva de esa operación ya fue cancelada.",
                        404,
                    )
                bookings = [tx.appointment(i) for i in receipt["ids"]]
                if not all(bookings):
                    raise RuleError(
                        "BOOKING_NOT_FOUND", "La reserva ya no existe.", 404
                    )
                return {"bookings": [b.result(now) for b in bookings]}
            if not tx.customer(actor):
                raise RuleError(
                    "CLIENT_NOT_FOUND", "No encuentro una ficha con ese teléfono.", 404
                )
            calendar, _ = tx.calendar()
            starts = [timestamp + DURATION * i for i in range(count)]
            for start in starts:
                validate_start(calendar, start, now)
                self._free(tx, start)
            self._quota(tx, actor, starts)
            bookings = [tx.insert(start, actor) for start in starts]
            tx.save_receipt(request_id, fingerprint, [b.id for b in bookings])
            return {"bookings": [b.result(now) for b in bookings]}

    def list_bookings(self, actor, start=None, end=None, admin=False):
        now = self.clock()
        start = start or now
        end = end or datetime.combine(now.date() + timedelta(days=14), time.min)
        if (
            start.tzinfo
            or end.tzinfo
            or start >= end
            or end - start > timedelta(days=366)
        ):
            raise RuleError(
                "INVALID_RANGE", "El rango debe ser local y como máximo de un año."
            )
        with self.store.transaction() as tx:
            return [
                b.result(now)
                for b in tx.appointments(start, end, None if admin else phone(actor))
            ]

    def get(self, actor, identifier, admin=False):
        with self.store.transaction() as tx:
            booking = tx.appointment(identifier)
            require_owner(booking, phone(actor) if not admin else None, admin)
            return booking.result(self.clock())

    def move(self, actor, identifier, timestamp, admin=False):
        with self.store.transaction() as tx:
            now = self.clock()
            booking = tx.appointment(identifier)
            require_owner(booking, phone(actor) if not admin else None, admin)
            require_not_started(booking, now)
            calendar, _ = tx.calendar()
            validate_start(calendar, timestamp, now)
            self._free(tx, timestamp, identifier)
            self._quota(tx, booking.telephone, [timestamp], identifier)
            return tx.move(identifier, timestamp).result(now)

    def cancel(self, actor, identifier, admin=False):
        with self.store.transaction() as tx:
            booking = tx.appointment(identifier)
            require_owner(booking, phone(actor) if not admin else None, admin)
            require_not_started(booking, self.clock(), cancelling=True)
            tx.delete(identifier)

    def settings(self):
        with self.store.transaction() as tx:
            calendar, version = tx.calendar()
            return dict(**calendar.result(), version=version)

    def save_settings(self, weekly, exceptions, version):
        if set(weekly) != set(map(str, range(7))):
            raise RuleError("INVALID_SCHEDULE", "Define los siete días de la semana.")
        calendar = Calendar(
            {int(k): [tuple(w) for w in v] for k, v in weekly.items()},
            {k: [tuple(w) for w in v] for k, v in exceptions.items()},
        )
        calendar.validate()
        with self.store.transaction() as tx:
            _, current_version = tx.calendar()
            if version != current_version:
                raise RuleError(
                    "STALE_CONFIG",
                    "El horario ha cambiado. Recarga antes de guardar.",
                    409,
                )
            now = self.clock()
            bookings = tx.appointments(now, datetime(9999, 1, 1))
            if any(not calendar.accepts(b.timestamp) for b in bookings):
                raise RuleError(
                    "SCHEDULE_CONFLICT",
                    "Hay citas que no encajan en el nuevo horario. Modifícalas o cancélalas primero.",
                    409,
                )
            tx.save_calendar(calendar)
            return dict(**calendar.result(), version=current_version + 1)
