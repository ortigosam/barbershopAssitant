from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from src.api.routes.admin import router as admin_router
from src.api.routes.availability import router as availability_router
from src.api.routes.bookings import router as bookings_router
from src.api.routes.clients import router as clients_router
from src.database.connection import pool
from src.domain.calendar import RuleError


@asynccontextmanager
async def lifespan(app):
    pool.open()
    try:
        yield
    finally:
        await run_in_threadpool(pool.close)


app = FastAPI(
    title="Barbershop Assistant API",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(clients_router)
app.include_router(availability_router)
app.include_router(bookings_router)
app.include_router(admin_router)


@app.exception_handler(RuleError)
async def rule_error(request, error):
    return JSONResponse(
        status_code=error.status, content={"detail": error.message, "code": error.code}
    )


web = Path(__file__).resolve().parents[2] / "web"
app.mount("/assets", StaticFiles(directory=web), name="assets")


@app.get("/", include_in_schema=False)
def calendar_page():
    return FileResponse(web / "index.html")
