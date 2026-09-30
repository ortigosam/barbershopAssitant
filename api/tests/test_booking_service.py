from datetime import date, datetime

from src.services.booking_service import BookingService


class FakeBookingRepository:
    def __init__(self, booked_timestamps: list[datetime]) -> None:
        self.booked_timestamps = booked_timestamps

    def list_between(self, start: datetime, end: datetime):
        return [
            (index + 1, timestamp, "600123456")
            for index, timestamp in enumerate(self.booked_timestamps)
            if start <= timestamp < end
        ]


def test_next_week_availability_excludes_existing_booking() -> None:
    booked_timestamp = datetime(2026, 10, 5, 10, 0)
    service = BookingService(FakeBookingRepository([booked_timestamp]), object())

    availability = service.get_availability("next", reference_date=date(2026, 9, 29))

    assert availability.week_start == date(2026, 10, 5)
    assert availability.week_end == date(2026, 10, 11)
    assert availability.slot_duration_minutes == 30
    assert booked_timestamp not in [slot.timestamp for slot in availability.slots]
    assert len(availability.slots) == 95


def test_bookable_slots_follow_the_business_schedule() -> None:
    assert BookingService._is_bookable_slot(datetime(2026, 10, 5, 10, 0))
    assert BookingService._is_bookable_slot(datetime(2026, 10, 5, 19, 30))
    assert not BookingService._is_bookable_slot(datetime(2026, 10, 5, 14, 0))
    assert not BookingService._is_bookable_slot(datetime(2026, 10, 5, 15, 0))
    assert not BookingService._is_bookable_slot(datetime(2026, 10, 4, 10, 0))
    assert not BookingService._is_bookable_slot(datetime(2026, 10, 5, 10, 0).astimezone())
