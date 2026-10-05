"""Barber administration endpoints."""

from fastapi import APIRouter, Depends, Response
from pydantic import NaiveDatetime
from src.api.routes.dependencies import Service
from src.api.routes.schemas import (
    AdminReservationInput,
    MoveInput,
    SettingsInput,
)
from src.api.security import administrator

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(administrator)],
)


@router.get("/bookings")
def list_admin(app: Service, start: NaiveDatetime, end: NaiveDatetime):
    return app.list_bookings(None, start, end, admin=True)


@router.post("/bookings", status_code=201)
def create_admin_booking(body: AdminReservationInput, app: Service):
    app.save_customer(body.telephone, body.name)
    return app.reserve(body.telephone, body.timestamp, body.count, str(body.request_id))


@router.put("/bookings/{identifier}")
def update_admin_booking(identifier: int, body: MoveInput, app: Service):
    return app.move(None, identifier, body.timestamp, admin=True)


@router.delete("/bookings/{identifier}", status_code=204)
def delete_admin_booking(identifier: int, app: Service):
    app.cancel(None, identifier, admin=True)
    return Response(status_code=204)


@router.get("/settings")
def get_settings(app: Service):
    return app.settings()


@router.put("/settings")
def update_settings(body: SettingsInput, app: Service):
    return app.save_settings(body.weekly, body.exceptions, body.version)
