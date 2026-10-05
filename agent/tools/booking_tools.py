from datetime import datetime
from typing import Literal

from langchain_core.tools import tool

from agent.http_client import request

@tool
def get_available_slots(
    week: Literal["current", "next"] = "current",
    count: int = 1,
) -> dict:
    """
    Get the available appointment start times for the current or next week.

    Use this tool when:
    - The user asks what appointment times are available.
    - The user asks for a free slot, free time, availability, or when they can book.
    - The user wants to make or move a booking but has not chosen an exact
      available time yet.
    - You need to verify which times are available before asking the user
      to choose one.

    Do NOT use this tool to:
    - Create a booking.
    - List appointments already owned by the user.
    - Modify or cancel an existing booking.

    Parameters:
    - week:
        "current" -> search availability in the current week.
        "next" -> search availability in the following week.
    - count:
        Number of consecutive 20-minute appointment slots required.
        Use 1 for a normal 20-minute appointment.
        Use 2 for 40 consecutive minutes, 3 for 60 minutes, etc.

    This tool only returns availability. It does NOT reserve any slot.
    """
    return request(
        "GET",
        "/bookings/availability",
        params={"week": week, "count": count},
    )


@tool
def list_bookings() -> dict:
    """
    List all upcoming appointments belonging to the authenticated user.

    Use this tool when:
    - The user asks what appointments or bookings they currently have.
    - The user asks when their next appointment is.
    - The user wants to see their upcoming appointments.
    - The user wants to modify or cancel an appointment but has not provided
      its booking_id. Use the returned bookings to identify the correct one.

    Do NOT use this tool to:
    - Search for available appointment times.
    - Create a new booking.
    - Modify an appointment.
    - Cancel an appointment.

    No parameters are required because the authenticated sender is
    automatically used to identify the customer.
    """
    return request("GET", "/bookings")


@tool
def create_booking(
    timestamp: datetime,
    request_id: str,
    count: int = 1,
) -> dict:
    """
    Create and confirm a new appointment for the authenticated user.

    Use this tool ONLY when:
    - The user clearly wants to book, reserve, or create an appointment.
    - The exact appointment date and start time are known.
    - The user has selected or explicitly requested that specific time.

    Do NOT use this tool when:
    - The user is only asking about availability.
    - The user has not yet chosen a specific date and time.
    - The user wants to modify an existing appointment.
    - The user wants to cancel an appointment.
    - The user only wants to see their existing appointments.

    Parameters:
    - timestamp:
        Exact date and start time requested by the user.
        Never invent or guess a missing date or time.
    - request_id:
        Unique identifier for this booking request, used to make creation
        idempotent and avoid accidental duplicate bookings.
        Reuse the same request_id when retrying the same booking operation.
    - count:
        Number of consecutive 20-minute appointment slots to book.
        Use 1 for a normal 20-minute appointment.
        Use 2 for 40 consecutive minutes, 3 for 60 minutes, etc.

    Calling this tool performs the actual booking. Do not claim that the
    appointment was successfully booked unless this tool returns success.
    """
    return request(
        "POST",
        "/bookings",
        json={
            "timestamp": timestamp.isoformat(),
            "request_id": request_id,
            "count": count,
        },
    )


@tool
def get_booking(booking_id: int) -> dict:
    """
    Retrieve the details of one specific appointment belonging to the
    authenticated user.

    Use this tool when:
    - You already know the booking_id and need the details of that booking.
    - You need to inspect or verify a specific appointment before another
      operation.

    Do NOT use this tool when:
    - You do not know the booking_id. Use list_bookings instead.
    - The user asks for all their appointments. Use list_bookings.
    - The user asks for available appointment times.
    - The user wants to create a new appointment.

    Parameters:
    - booking_id:
        Identifier of an existing booking owned by the authenticated user.
        Never invent a booking_id.
    """
    return request("GET", f"/bookings/{booking_id}")


@tool
def update_booking(
    booking_id: int,
    timestamp: datetime,
) -> dict:
    """
    Move an existing appointment belonging to the authenticated user to a
    new date and time.

    Use this tool ONLY when:
    - The user clearly wants to move, reschedule, or change an existing
      appointment.
    - The booking_id of the appointment to modify is known.
    - The new exact date and start time are known.

    If the user wants to modify an appointment but the booking_id is unknown,
    first use list_bookings to identify the appointment.

    If the user has not selected a new time yet, use get_available_slots
    before updating the booking.

    Do NOT use this tool to:
    - Create a new appointment.
    - Cancel an appointment.
    - Search for availability.
    - Change an appointment when the new timestamp is still unknown.

    Parameters:
    - booking_id:
        Identifier of the existing appointment to move.
        Never invent a booking_id.
    - timestamp:
        Exact new date and start time requested or selected by the user.
        Never invent or guess a missing date or time.

    Do not claim that the appointment was successfully changed unless this
    tool returns success.
    """
    return request(
        "PUT",
        f"/bookings/{booking_id}",
        json={"timestamp": timestamp.isoformat()},
    )


@tool
def delete_booking(booking_id: int) -> dict:
    """
    Cancel an existing appointment belonging to the authenticated user.

    Use this tool ONLY when:
    - The user clearly wants to cancel, delete, or remove an existing
      appointment.
    - The booking_id of the appointment to cancel is known.

    If the user wants to cancel an appointment but the booking_id is unknown,
    first use list_bookings to identify the correct appointment.

    Do NOT use this tool to:
    - Create an appointment.
    - Move or reschedule an appointment.
    - Search for available times.
    - Cancel an appointment when it is unclear which booking the user means.

    Parameters:
    - booking_id:
        Identifier of the existing appointment to cancel.
        Never invent a booking_id.

    Calling this tool performs the actual cancellation. Do not tell the user
    that the appointment was cancelled unless this tool returns success.
    """
    return request("DELETE", f"/bookings/{booking_id}")