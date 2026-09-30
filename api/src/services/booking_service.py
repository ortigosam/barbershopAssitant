from datetime import date, datetime, time, timedelta
from typing import Optional, Tuple, Any

from psycopg import errors

from src.domain.exceptions import (
    BookingAlreadyExistsError,
    BookingNotFoundError,
    BookingOutsideBusinessHoursError,
    ClientNotFoundError,
)
from src.repositories.booking_repository import BookingRepository
from src.repositories.client_repository import ClientRepository
from src.schemas.booking import (
    AvailabilityResponse,
    AvailabilityWeek,
    AvailableSlot,
    BookingResponse,
)


class BookingService:
    """Business rules for 30-minute barber appointments.

    The database stores local Europe/Madrid wall-clock timestamps without a
    timezone. Keep API timestamps in that same local time convention.
    """

    SLOT_DURATION = timedelta(minutes=30)
    BUSINESS_WINDOWS = ((time(10, 0), time(14, 0)), (time(16, 0), time(20, 0)))
    BUSINESS_WEEKDAYS = frozenset(range(6))  # Monday through Saturday

    def __init__(
        self,
        booking_repository: BookingRepository,
        client_repository: ClientRepository,
    ):
        self.booking_repository = booking_repository
        self.client_repository = client_repository

    def _row_to_response(self, row: Tuple[Any, Any, Any]) -> BookingResponse:
        return BookingResponse(id=row[0], timestamp=row[1], telephone=row[2])

    @classmethod
    def _is_bookable_slot(cls, timestamp: datetime) -> bool:
        if timestamp.tzinfo is not None:
            return False
        if timestamp.weekday() not in cls.BUSINESS_WEEKDAYS:
            return False
        if timestamp.second or timestamp.microsecond:
            return False

        for start, end in cls.BUSINESS_WINDOWS:
            window_start = datetime.combine(timestamp.date(), start)
            window_end = datetime.combine(timestamp.date(), end)
            if window_start <= timestamp < window_end:
                return (timestamp - window_start) % cls.SLOT_DURATION == timedelta()
        return False

    def get_availability(
        self,
        week: AvailabilityWeek,
        reference_date: date | None = None,
    ) -> AvailabilityResponse:
        """Calculate free slots for the current or next Monday-Sunday week."""
        today = reference_date or datetime.now().date()
        current_monday = today - timedelta(days=today.weekday())
        week_start = current_monday if week == "current" else current_monday + timedelta(days=7)
        week_end = week_start + timedelta(days=7)
        start = datetime.combine(week_start, time.min)
        end = datetime.combine(week_end, time.min)
        occupied = {row[1] for row in self.booking_repository.list_between(start, end)}
        now = datetime.now()
        slots: list[AvailableSlot] = []

        for day_offset in range(7):
            appointment_date = week_start + timedelta(days=day_offset)
            if appointment_date.weekday() not in self.BUSINESS_WEEKDAYS:
                continue
            for opening, closing in self.BUSINESS_WINDOWS:
                timestamp = datetime.combine(appointment_date, opening)
                window_end = datetime.combine(appointment_date, closing)
                while timestamp < window_end:
                    if timestamp not in occupied and (week != "current" or timestamp >= now):
                        slots.append(AvailableSlot(timestamp=timestamp))
                    timestamp += self.SLOT_DURATION

        return AvailabilityResponse(
            week=week,
            week_start=week_start,
            week_end=week_end - timedelta(days=1),
            slot_duration_minutes=int(self.SLOT_DURATION.total_seconds() // 60),
            slots=slots,
        )

    def _validate_bookable_timestamp(self, timestamp: datetime) -> None:
        if (
            timestamp.tzinfo is not None
            or timestamp < datetime.now()
            or not self._is_bookable_slot(timestamp)
        ):
            raise BookingOutsideBusinessHoursError(
                "Bookings must be future 30-minute slots, Monday-Saturday, "
                "between 10:00-14:00 or 16:00-20:00 (Europe/Madrid)"
            )

    def create_booking(
        self,
        timestamp: datetime,
        telephone: str,
    ) -> BookingResponse:
        self._validate_bookable_timestamp(timestamp)
        client = self.client_repository.get_by_telephone(telephone)

        if client is None:
            raise ClientNotFoundError(f"Client {telephone} does not exist")

        try:
            row = self.booking_repository.create(timestamp=timestamp, telephone=telephone)
            return self._row_to_response(row)

        except errors.UniqueViolation:
            raise BookingAlreadyExistsError(f"Booking at {timestamp} already exists")

    def get_booking(self, booking_id: int) -> BookingResponse:
        row = self.booking_repository.get_by_id(booking_id)

        if row is None:
            raise BookingNotFoundError(f"Booking {booking_id} does not exist")

        return self._row_to_response(row)

    def delete_booking(self, booking_id: int) -> None:
        deleted = self.booking_repository.delete(booking_id)

        if not deleted:
            raise BookingNotFoundError(f"Booking {booking_id} does not exist")

    def update_booking(
        self, booking_id: int, timestamp: Optional[datetime] = None, telephone: Optional[str] = None
    ) -> BookingResponse:
        if timestamp is not None:
            self._validate_bookable_timestamp(timestamp)

        # If telephone is provided, ensure client exists
        if telephone is not None:
            client = self.client_repository.get_by_telephone(telephone)
            if client is None:
                raise ClientNotFoundError(f"Client {telephone} does not exist")

        try:
            row = self.booking_repository.update(
                booking_id=booking_id, timestamp=timestamp, telephone=telephone
            )

        except errors.UniqueViolation:
            raise BookingAlreadyExistsError(f"Booking at {timestamp} already exists")

        if row is None:
            raise BookingNotFoundError(f"Booking {booking_id} does not exist")

        return self._row_to_response(row)
