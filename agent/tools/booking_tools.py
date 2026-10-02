from datetime import datetime
from typing import Literal

from langchain_core.tools import tool

from agent.http_client import request


@tool
def get_available_slots(
    week: Literal["current", "next"] = "current", count: int = 1
) -> dict:
    """List available starts for consecutive 20-minute appointments."""
    return request(
        "GET", "/bookings/availability", params={"week": week, "count": count}
    )


@tool
def list_bookings() -> dict:
    """List the authenticated sender's upcoming appointments."""
    return request("GET", "/bookings")


@tool
def create_booking(timestamp: datetime, request_id: str, count: int = 1) -> dict:
    """Atomically book one or more appointments for the authenticated sender."""
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
    """Retrieve an appointment owned by the authenticated sender."""
    return request("GET", f"/bookings/{booking_id}")


@tool
def update_booking(booking_id: int, timestamp: datetime) -> dict:
    """Move an owned appointment without changing its customer."""
    return request(
        "PUT", f"/bookings/{booking_id}", json={"timestamp": timestamp.isoformat()}
    )


@tool
def delete_booking(booking_id: int) -> dict:
    """Cancel an owned appointment before its start."""
    return request("DELETE", f"/bookings/{booking_id}")
