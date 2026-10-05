"""Transactional PostgreSQL unit of work for the one-barber application."""

from contextlib import contextmanager

from psycopg import errors

from src.domain.calendar import RuleError
from src.repositories.booking_repository import PostgresBookingRepository
from src.repositories.client_repository import PostgresClientRepository
from src.repositories.receipt_repository import PostgresReceiptRepository
from src.repositories.schedule_repository import PostgresScheduleRepository

LOCK_ID = 78204312


class PostgresUnitOfWork:
    def __init__(self, pool):
        self.pool = pool

    @contextmanager
    def transaction(self):
        try:
            with self.pool.connection() as connection:
                with connection.transaction():
                    connection.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_ID,))
                    yield PostgresTransaction(connection)
        except errors.UniqueViolation:
            raise RuleError(
                "BOOKING_ALREADY_EXISTS",
                "Ese horario ya no está disponible. Puedo consultar otros horarios.",
                409,
            ) from None
        except errors.ExclusionViolation:
            raise RuleError(
                "BOOKING_ALREADY_EXISTS",
                "Ese horario ya no está disponible. Puedo consultar otros horarios.",
                409,
            ) from None


class PostgresTransaction:
    """One transaction exposing focused repositories and old compatibility methods."""

    def __init__(self, connection):
        self.clients = PostgresClientRepository(connection)
        self.bookings = PostgresBookingRepository(connection)
        self.schedule = PostgresScheduleRepository(connection)
        self.receipts = PostgresReceiptRepository(connection)

    # These delegates keep the application service contract stable while the
    # persistence implementation is now split by resource.
    def calendar(self):
        return self.schedule.get()

    def save_calendar(self, calendar):
        self.schedule.save(calendar)

    def customer(self, telephone):
        return self.clients.get(telephone)

    def save_customer(self, telephone, name):
        return self.clients.save(telephone, name)

    def appointments(self, start, end, telephone=None):
        return self.bookings.list(start, end, telephone)

    def appointment(self, identifier):
        return self.bookings.get(identifier)

    def insert(self, timestamp, telephone):
        return self.bookings.create(timestamp, telephone)

    def move(self, identifier, timestamp):
        return self.bookings.move(identifier, timestamp)

    def delete(self, identifier):
        self.bookings.delete(identifier)
        self.receipts.invalidate_for_booking(identifier)

    def receipt(self, request_id):
        return self.receipts.get(request_id)

    def save_receipt(self, request_id, fingerprint, ids):
        self.receipts.save(request_id, fingerprint, ids)
