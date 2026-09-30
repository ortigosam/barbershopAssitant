from datetime import datetime
from typing import Literal

import httpx
from langchain_core.tools import tool

from agent.models.booking import (
    AvailabilityResult,
    AvailableSlot,
    Booking,
    CreateBookingResult,
    GetBookingResult,
    UpdateBookingResult,
    DeleteBookingResult,
)


API_URL = "http://localhost:8000"


@tool
def get_available_slots(week: Literal["current", "next"] = "current") -> AvailabilityResult:
    """List free 30-minute appointment slots for the current or next week.

    Use ``current`` for this week and ``next`` for the following week. Always
    check availability before creating or moving a booking.
    """
    try:
        response = httpx.get(f"{API_URL}/bookings/availability", params={"week": week}, timeout=10)
    except httpx.HTTPError:
        return AvailabilityResult(success=False, error="API_UNAVAILABLE", message="The booking API is unavailable.")

    response.raise_for_status()
    data = response.json()
    return AvailabilityResult(
        success=True,
        week=data["week"],
        week_start=data["week_start"],
        week_end=data["week_end"],
        slots=[AvailableSlot.model_validate(slot) for slot in data["slots"]],
    )


@tool
def create_booking(
    timestamp: datetime,
    telephone: str,
) -> CreateBookingResult:
    """
    Create a new booking for an existing client.

    Use this tool when the customer wants to book an appointment.
    The customer must already exist.

    Args:
        timestamp: Date and time of the appointment.
        telephone: Customer's telephone number.
    """
    try:
        response = httpx.post(
            f"{API_URL}/bookings",
            json={"timestamp": timestamp.isoformat(), "telephone": telephone},
            timeout=10,
        )
    except httpx.HTTPError:
        return CreateBookingResult(success=False, error="API_UNAVAILABLE", message="The booking API is unavailable.")

    if response.status_code == 404:
        return CreateBookingResult(
            success=False,
            error="CLIENT_NOT_FOUND",
            message="The customer does not exist.",
        )

    if response.status_code == 409:
        return CreateBookingResult(
            success=False,
            error="BOOKING_ALREADY_EXISTS",
            message="There is already a booking at that time.",
        )

    if response.status_code == 422:
        return CreateBookingResult(
            success=False, error="INVALID_SLOT", message="That time is not a future available barber-shop slot."
        )

    response.raise_for_status()
    # pydantic v2: `parse_obj` is deprecated in favor of `model_validate`.
    booking = Booking.model_validate(response.json())
    return CreateBookingResult(success=True, booking=booking)


@tool
def get_booking(
    booking_id: int,
) -> GetBookingResult:
    """
    Get an existing booking by its ID.

    Args:
        booking_id: The booking ID.
    """
    try:
        response = httpx.get(f"{API_URL}/bookings/{booking_id}", timeout=10)
    except httpx.HTTPError:
        return GetBookingResult(success=False, error="API_UNAVAILABLE", message="The booking API is unavailable.")

    if response.status_code == 404:
        return GetBookingResult(
            success=False,
            error="BOOKING_NOT_FOUND",
            message="The booking does not exist.",
        )

    response.raise_for_status()
    booking = Booking.model_validate(response.json())
    return GetBookingResult(success=True, booking=booking)


@tool
def update_booking(
    booking_id: int,
    timestamp: datetime | None = None,
    telephone: str | None = None,
) -> UpdateBookingResult:
    """
    Update an existing booking.

    Use this tool when a customer wants to change
    the date or time of an appointment.

    Args:
        booking_id: The booking ID.
        timestamp: New date and time, if it changes.
        telephone: Customer's telephone number, if it changes.
    """
    try:
        response = httpx.put(
            f"{API_URL}/bookings/{booking_id}",
            json={
                key: value
                for key, value in {
                    "timestamp": timestamp.isoformat() if timestamp else None,
                    "telephone": telephone,
                }.items()
                if value is not None
            },
            timeout=10,
        )
    except httpx.HTTPError:
        return UpdateBookingResult(success=False, error="API_UNAVAILABLE", message="The booking API is unavailable.")

    if response.status_code == 404:
        return UpdateBookingResult(
            success=False,
            error="BOOKING_NOT_FOUND",
            message="The booking does not exist.",
        )

    if response.status_code == 409:
        return UpdateBookingResult(
            success=False,
            error="BOOKING_ALREADY_EXISTS",
            message="There is already a booking at that time.",
        )

    if response.status_code == 422:
        return UpdateBookingResult(
            success=False, error="INVALID_SLOT", message="That time is not a future available barber-shop slot."
        )

    response.raise_for_status()
    booking = Booking.model_validate(response.json())
    return UpdateBookingResult(success=True, booking=booking)


@tool
def delete_booking(
    booking_id: int,
) -> DeleteBookingResult:
    """
    Cancel an existing booking.

    Args:
        booking_id: The booking ID.
    """
    try:
        response = httpx.delete(f"{API_URL}/bookings/{booking_id}", timeout=10)
    except httpx.HTTPError:
        return DeleteBookingResult(success=False, error="API_UNAVAILABLE", message="The booking API is unavailable.")

    if response.status_code == 404:
        return DeleteBookingResult(
            success=False,
            error="BOOKING_NOT_FOUND",
            message="The booking does not exist.",
        )

    response.raise_for_status()
    return DeleteBookingResult(
        success=True, message="Booking cancelled successfully.", booking_id=booking_id
    )
