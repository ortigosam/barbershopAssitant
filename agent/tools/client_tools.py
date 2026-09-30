
import httpx
from langchain_core.tools import tool

from agent.models.booking import Client, CreateClientResult, GetClientResult


API_URL = "http://localhost:8000"


@tool
def create_client(telephone: str, name: str) -> CreateClientResult:
    """Create a customer before making their first booking.

    Ask for both their phone number and name before calling this tool.
    """
    try:
        response = httpx.post(
            f"{API_URL}/clients", json={"telephone": telephone, "name": name}, timeout=10
        )
    except httpx.HTTPError:
        return CreateClientResult(success=False, error="API_UNAVAILABLE", message="The booking API is unavailable.")

    if response.status_code == 409:
        return CreateClientResult(success=False, error="CLIENT_ALREADY_EXISTS", message="Client already exists")

    response.raise_for_status()
    data = response.json()

    return CreateClientResult(success=True, client=Client.model_validate(data), message="Client created.")


@tool
def get_client(telephone: str) -> GetClientResult:
    """Look up a customer by phone number before creating a booking."""
    try:
        response = httpx.get(f"{API_URL}/clients/{telephone}", timeout=10)
    except httpx.HTTPError:
        return GetClientResult(success=False, error="API_UNAVAILABLE", message="The booking API is unavailable.")

    if response.status_code == 404:
        return GetClientResult(success=False, error="CLIENT_NOT_FOUND", message="Client not found")

    response.raise_for_status()
    data = response.json()
    return GetClientResult(success=True, client=Client.model_validate(data))
