from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class BookingCreate(BaseModel):
    timestamp: datetime
    telephone: str


class BookingResponse(BaseModel):
    id: int
    timestamp: datetime
    telephone: str


class BookingUpdate(BaseModel):
    timestamp: datetime | None = None
    telephone: str | None = None


AvailabilityWeek = Literal["current", "next"]


class AvailableSlot(BaseModel):
    timestamp: datetime


class AvailabilityResponse(BaseModel):
    week: AvailabilityWeek
    week_start: date
    week_end: date
    slot_duration_minutes: int
    slots: list[AvailableSlot]
