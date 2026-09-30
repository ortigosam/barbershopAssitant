from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Booking(BaseModel):
    id: int
    timestamp: datetime
    telephone: str


class Client(BaseModel):
    telephone: str
    name: str


class AvailableSlot(BaseModel):
    timestamp: datetime


class ToolResult(BaseModel):
    success: bool
    error: Optional[str] = None
    message: Optional[str] = None


class CreateBookingResult(ToolResult):
    booking: Optional[Booking] = None


class CreateClientResult(ToolResult):
    client: Optional[Client] = None


class GetClientResult(ToolResult):
    client: Optional[Client] = None


class AvailabilityResult(ToolResult):
    week: Optional[Literal["current", "next"]] = None
    week_start: Optional[date] = None
    week_end: Optional[date] = None
    slots: list[AvailableSlot] = Field(default_factory=list)


class GetBookingResult(ToolResult):
    booking: Optional[Booking] = None


class UpdateBookingResult(ToolResult):
    booking: Optional[Booking] = None


class DeleteBookingResult(ToolResult):
    booking_id: Optional[int] = None
