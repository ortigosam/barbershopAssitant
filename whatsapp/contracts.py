"""Application contracts, independent of FastAPI and Meta."""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Incoming:
    id: str
    phone: str
    text: str = ""
    selection: str = ""


class ApiError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class BookingApi(Protocol):
    async def customer(self, phone: str) -> dict: ...
    async def create_customer(self, phone: str, name: str) -> dict: ...
    async def slots(self, phone: str, week: str) -> list[dict]: ...
    async def bookings(self, phone: str) -> list[dict]: ...
    async def reserve(self, phone: str, timestamp: str, request_id: str) -> dict: ...
    async def cancel(self, phone: str, identifier: int) -> None: ...


class Messenger(Protocol):
    async def send(self, phone: str, message: dict) -> None: ...

