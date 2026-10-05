"""Availability read endpoints."""

from typing import Literal

from fastapi import APIRouter
from src.api.routes.dependencies import Actor, Service

router = APIRouter(prefix="/bookings", tags=["availability"])


@router.get("/availability")
def availability(
    customer: Actor,
    app: Service,
    week: Literal["current", "next"] = "current",
    count: int = 1,
):
    return app.availability(week, count)
