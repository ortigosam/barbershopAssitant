from typing import Annotated

from fastapi import Depends

from src.database.connection import pool
from src.repositories.booking_repository import BookingRepository
from src.repositories.client_repository import ClientRepository
from src.services.booking_service import BookingService
from src.services.client_service import ClientService


def get_client_service() -> ClientService:
    repository = ClientRepository(pool)
    return ClientService(repository)


def get_booking_service() -> BookingService:
    booking_repository = BookingRepository(pool)
    client_repository = ClientRepository(pool)

    return BookingService(
        booking_repository=booking_repository,
        client_repository=client_repository,
    )


# FastAPI dependency aliases (use `Annotated` in route signatures)
BookingServiceDep = Annotated[BookingService, Depends(get_booking_service)]
ClientServiceDep = Annotated[ClientService, Depends(get_client_service)]