"""Request models shared by the client, booking and admin routers."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, NaiveDatetime


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CustomerInput(Input):
    name: str = Field(min_length=1, max_length=59)


class ReservationInput(Input):
    timestamp: NaiveDatetime
    count: int = Field(default=1, ge=1, le=5)
    request_id: UUID


class MoveInput(Input):
    timestamp: NaiveDatetime


class AdminReservationInput(ReservationInput):
    telephone: str
    name: str = Field(min_length=1, max_length=59)


class SettingsInput(Input):
    weekly: dict[str, list[tuple[str, str]]]
    exceptions: dict[str, list[tuple[str, str]]]
    version: int = Field(ge=1)
