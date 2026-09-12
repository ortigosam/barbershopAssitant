from datetime import datetime

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