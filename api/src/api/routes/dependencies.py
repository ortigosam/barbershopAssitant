"""Shared FastAPI dependencies for the resource routers."""

from typing import Annotated

from fastapi import Depends
from src.api.security import actor
from src.application.barbershop_service import BarbershopService
from src.database.connection import pool
from src.repositories.barbershop_store import PostgresBarbershopStore


def service() -> BarbershopService:
    return BarbershopService(PostgresBarbershopStore(pool))


Service = Annotated[BarbershopService, Depends(service)]
Actor = Annotated[str, Depends(actor)]
