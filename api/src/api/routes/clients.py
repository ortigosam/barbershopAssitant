"""Customer resource endpoints."""

from fastapi import APIRouter
from src.api.routes.dependencies import Actor, Service
from src.api.routes.schemas import CustomerInput

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("/me")
def get_customer(customer: Actor, app: Service):
    return app.customer(customer)


@router.post("/me", status_code=201)
def create_customer(body: CustomerInput, customer: Actor, app: Service):
    return app.save_customer(customer, body.name, create_only=True)


@router.put("/me")
def update_customer(body: CustomerInput, customer: Actor, app: Service):
    return app.save_customer(customer, body.name)
