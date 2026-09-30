from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status, Path

from src.api.dependencies import BookingServiceDep
from src.domain.exceptions import (
    BookingAlreadyExistsError,
    BookingNotFoundError,
    BookingOutsideBusinessHoursError,
    ClientNotFoundError,
)
from src.schemas.booking import (
    AvailabilityResponse,
    AvailabilityWeek,
    BookingCreate,
    BookingResponse,
    BookingUpdate,
)

router = APIRouter(
    prefix="/bookings",
    tags=["bookings"],
)


@router.get(
    "/availability",
    response_model=AvailabilityResponse,
    summary="List free appointment slots for this or next week",
)
def get_availability(
    service: BookingServiceDep,
    week: Annotated[AvailabilityWeek, Query(description="'current' or 'next' week")] = "current",
) -> AvailabilityResponse:
    return service.get_availability(week)


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_booking(
    booking: BookingCreate,
    service: BookingServiceDep,
) -> BookingResponse:
    try:
        result = service.create_booking(
            timestamp=booking.timestamp,
            telephone=booking.telephone,
        )

    except ClientNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except BookingAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    except BookingOutsideBusinessHoursError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    return result


@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
)
def get_booking(
    booking_id: Annotated[int, Path(ge=1)],
    service: BookingServiceDep,
) -> BookingResponse:
    try:
        result = service.get_booking(booking_id)

    except BookingNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return result


@router.delete(
    "/{booking_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_booking(
    booking_id: Annotated[int, Path(ge=1)],
    service: BookingServiceDep,
) -> None:
    try:
        service.delete_booking(booking_id)

    except BookingNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error



@router.put(
    "/{booking_id}",
    response_model=BookingResponse,
)
def update_booking(
    booking_id: Annotated[int, Path(ge=1)],
    booking: BookingUpdate,
    service: BookingServiceDep,
) -> BookingResponse:
    try:
        result = service.update_booking(
            booking_id=booking_id,
            timestamp=booking.timestamp,
            telephone=booking.telephone,
        )

    except ClientNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except BookingAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    except BookingNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except BookingOutsideBusinessHoursError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    return result
