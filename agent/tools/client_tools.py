from langchain_core.tools import tool

from agent.http_client import request


@tool
def get_client() -> dict:
    """Get the authenticated sender's customer record."""
    return request("GET", "/clients/me")


@tool
def create_client(name: str) -> dict:
    """Create the authenticated sender's customer record."""
    return request("POST", "/clients/me", json={"name": name})


@tool
def update_client(name: str) -> dict:
    """Update the authenticated sender's name."""
    return request("PUT", "/clients/me", json={"name": name})
