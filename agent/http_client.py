"""Reusable HTTP transport; no automatic mutation retries."""
import os
import httpx

_client = httpx.Client(timeout=10)

def request(method, path, *, missing="BOOKING_NOT_FOUND", **kwargs):
    try:
        response = _client.request(method, os.getenv("BARBERSHOP_API_URL", "http://localhost:8000").rstrip("/") + path, **kwargs)
        if response.status_code == 204:
            return {"success": True}
        if response.is_success:
            return {"success": True, "data": response.json()}
        detail = response.json().get("detail", "")
        if response.status_code == 404 and isinstance(detail, str) and detail.startswith("Client"):
            missing = "CLIENT_NOT_FOUND"
        error = {404: missing, 409: "BOOKING_ALREADY_EXISTS", 422: "INVALID_SLOT"}.get(response.status_code, "API_ERROR")
        return {"success": False, "error": error}
    except (httpx.HTTPError, ValueError):
        return {"success": False, "error": "RESULT_UNKNOWN"}
