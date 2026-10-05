"""Authenticated booking resource endpoints."""

from fastapi import APIRouter, Response
from src.api.routes.dependencies import Actor, Service
from src.api.routes.schemas import ReservationInput

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("")
def list_own(customer: Actor, app: Service):
    return app.list_bookings(customer)


@router.post("", status_code=201)
def create_booking(body: ReservationInput, customer: Actor, app: Service):
    return app.reserve(customer, body.timestamp, body.count, str(body.request_id))


@router.get("/{identifier}")
def get_booking(identifier: int, customer: Actor, app: Service):
    return app.get(customer, identifier)


@router.delete("/{identifier}", status_code=204)
def delete_booking(identifier: int, customer: Actor, app: Service):
    app.cancel(customer, identifier)
    return Response(status_code=204)
