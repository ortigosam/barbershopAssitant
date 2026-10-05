"""Compatibility exports for the formerly combined calendar router.

New code imports resource routers from ``clients``, ``bookings``,
``availability`` and ``admin``. These exports preserve existing dependency
overrides while the public HTTP contract remains unchanged.
"""

from fastapi import APIRouter
from src.api.routes.admin import router as admin
from src.api.routes.availability import router as availability
from src.api.routes.bookings import router as bookings
from src.api.routes.clients import router as clients
from src.api.routes.dependencies import service

router = APIRouter()
router.include_router(clients)
router.include_router(availability)
router.include_router(bookings)

__all__ = ["admin", "availability", "bookings", "clients", "router", "service"]
