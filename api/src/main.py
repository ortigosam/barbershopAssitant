from fastapi import FastAPI

from src.api.routes.bookings import router as bookings_router
from src.api.routes.clients import router as clients_router


app = FastAPI(
    title="Barbershop Assistant API",
    version="0.1.0",
)


app.include_router(clients_router)
app.include_router(bookings_router)