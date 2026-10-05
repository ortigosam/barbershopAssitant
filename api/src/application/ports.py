"""Ports separating persistence responsibilities from application rules."""

from contextlib import AbstractContextManager
from datetime import datetime
from typing import Protocol

from src.domain.calendar import Appointment, Calendar


class ClientRepository(Protocol):
    def get(self, telephone: str) -> dict | None: ...
    def save(self, telephone: str, name: str) -> dict: ...


class BookingRepository(Protocol):
    def list(
        self, start: datetime, end: datetime, telephone: str | None = None
    ) -> list[Appointment]: ...
    def get(self, identifier: int) -> Appointment | None: ...
    def create(self, timestamp: datetime, telephone: str) -> Appointment: ...
    def move(self, identifier: int, timestamp: datetime) -> Appointment: ...
    def delete(self, identifier: int) -> None: ...


class ScheduleRepository(Protocol):
    def get(self) -> tuple[Calendar, int]: ...
    def save(self, calendar: Calendar) -> None: ...


class ReceiptRepository(Protocol):
    def get(self, request_id: str) -> dict | None: ...
    def save(self, request_id: str, fingerprint: str, ids: list[int]) -> None: ...
    def invalidate_for_booking(self, identifier: int) -> None: ...


class BarbershopTransaction(Protocol):
    clients: ClientRepository
    bookings: BookingRepository
    schedule: ScheduleRepository
    receipts: ReceiptRepository


class BarbershopStore(Protocol):
    def transaction(self) -> AbstractContextManager[BarbershopTransaction]: ...


# Compatibility aliases for existing imports.
CalendarTransaction = BarbershopTransaction
CalendarStore = BarbershopStore
