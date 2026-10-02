from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field, NaiveDatetime
from src.api.security import actor, administrator
from src.application.calendar_service import CalendarService
from src.database.connection import pool
from src.repositories.calendar_store import PostgresCalendarStore


def service():
    return CalendarService(PostgresCalendarStore(pool))


Service = Annotated[CalendarService, Depends(service)]
Actor = Annotated[str, Depends(actor)]
router = APIRouter()
admin = APIRouter(prefix="/admin", dependencies=[Depends(administrator)])


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Customer(Input):
    name: str = Field(min_length=1, max_length=59)


class Reserve(Input):
    timestamp: NaiveDatetime
    count: int = Field(default=1, ge=1, le=5)
    request_id: UUID


class Move(Input):
    timestamp: NaiveDatetime


class AdminReserve(Reserve):
    telephone: str
    name: str = Field(min_length=1, max_length=59)


class SettingsInput(Input):
    weekly: dict[str, list[tuple[str, str]]]
    exceptions: dict[str, list[tuple[str, str]]]
    version: int = Field(ge=1)


@router.get("/clients/me")
def get_customer(customer: Actor, app: Service):
    return app.customer(customer)


@router.post("/clients/me", status_code=201)
def create_customer(body: Customer, customer: Actor, app: Service):
    return app.save_customer(customer, body.name, create_only=True)


@router.put("/clients/me")
def update_customer(body: Customer, customer: Actor, app: Service):
    return app.save_customer(customer, body.name)


@router.get("/bookings/availability")
def availability(
    customer: Actor,
    app: Service,
    week: Literal["current", "next"] = "current",
    count: int = 1,
):
    return app.availability(week, count)


@router.get("/bookings")
def list_own(customer: Actor, app: Service):
    return app.list_bookings(customer)


@router.post("/bookings", status_code=201)
def reserve(body: Reserve, customer: Actor, app: Service):
    return app.reserve(customer, body.timestamp, body.count, str(body.request_id))


@router.get("/bookings/{identifier}")
def get(identifier: int, customer: Actor, app: Service):
    return app.get(customer, identifier)


@router.put("/bookings/{identifier}")
def move(identifier: int, body: Move, customer: Actor, app: Service):
    return app.move(customer, identifier, body.timestamp)


@router.delete("/bookings/{identifier}", status_code=204)
def cancel(identifier: int, customer: Actor, app: Service):
    app.cancel(customer, identifier)
    return Response(status_code=204)


@admin.get("/bookings")
def list_admin(app: Service, start: NaiveDatetime, end: NaiveDatetime):
    return app.list_bookings(None, start, end, admin=True)


@admin.post("/bookings", status_code=201)
def reserve_admin(body: AdminReserve, app: Service):
    app.save_customer(body.telephone, body.name)
    return app.reserve(body.telephone, body.timestamp, body.count, str(body.request_id))


@admin.put("/bookings/{identifier}")
def move_admin(identifier: int, body: Move, app: Service):
    return app.move(None, identifier, body.timestamp, admin=True)


@admin.delete("/bookings/{identifier}", status_code=204)
def cancel_admin(identifier: int, app: Service):
    app.cancel(None, identifier, admin=True)
    return Response(status_code=204)


@admin.get("/settings")
def get_settings(app: Service):
    return app.settings()


@admin.put("/settings")
def save_settings(body: SettingsInput, app: Service):
    return app.save_settings(body.weekly, body.exceptions, body.version)
