from datetime import datetime

from psycopg import errors

from src.domain.exceptions import (
    BookingAlreadyExistsError,
    BookingNotFoundError,
    ClientNotFoundError,
)
from src.repositories.booking_repository import BookingRepository
from src.repositories.client_repository import ClientRepository
from src.schemas.booking import BookingResponse

class BookingService:

    def __init__(
        self,
        booking_repository: BookingRepository,
        client_repository: ClientRepository,
    ):
        self.booking_repository = booking_repository
        self.client_repository = client_repository

    def create_booking(
        self,
        timestamp: datetime,
        telephone: str,
    ):
        client = self.client_repository.get_by_telephone(telephone)

        if client is None:
            raise ClientNotFoundError(
                f"Client {telephone} does not exist"
            )

        try:
            row = self.booking_repository.create(
                timestamp=timestamp,
                telephone=telephone,
            )

            return BookingResponse(id=row[0], timestamp=row[1], telephone=row[2])

        except errors.UniqueViolation:
            raise BookingAlreadyExistsError(
                f"Booking at {timestamp} already exists"
            )

    def get_booking(self, booking_id: int):
        row = self.booking_repository.get_by_id(booking_id)

        if row is None:
            raise BookingNotFoundError(
                f"Booking {booking_id} does not exist"
            )

        return BookingResponse(id=row[0], timestamp=row[1], telephone=row[2])

    def delete_booking(self, booking_id: int):
        deleted = self.booking_repository.delete(booking_id)

        if not deleted:
            raise BookingNotFoundError(
                f"Booking {booking_id} does not exist"
            )

    def update_booking(self, booking_id: int, timestamp: datetime | None = None, telephone: str | None = None):
        # If telephone is provided, ensure client exists
        if telephone is not None:
            client = self.client_repository.get_by_telephone(telephone)

            if client is None:
                raise ClientNotFoundError(
                    f"Client {telephone} does not exist"
                )

        try:
            row = self.booking_repository.update(
                booking_id=booking_id,
                timestamp=timestamp,
                telephone=telephone,
            )

        except errors.UniqueViolation:
            raise BookingAlreadyExistsError(
                f"Booking at {timestamp} already exists"
            )

        if row is None:
            raise BookingNotFoundError(
                f"Booking {booking_id} does not exist"
            )

        return BookingResponse(id=row[0], timestamp=row[1], telephone=row[2])