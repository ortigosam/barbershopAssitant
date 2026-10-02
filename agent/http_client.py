"""Authenticated channel transport. Identity comes from the adapter, not the LLM."""

import os
from contextlib import contextmanager
from contextvars import ContextVar

import httpx

_client = httpx.Client(timeout=10)
_sender = ContextVar("sender_phone", default=None)


@contextmanager
def customer_identity(telephone):
    token = _sender.set(telephone)
    try:
        yield
    finally:
        _sender.reset(token)


def request(method, path, **kwargs):
    if not _sender.get():
        return {"success": False, "error": "UNAUTHENTICATED"}
    headers = {
        "Authorization": "Bearer " + os.getenv("AGENT_API_TOKEN", ""),
        "X-Customer-Phone": _sender.get(),
    }
    try:
        response = _client.request(
            method,
            os.getenv("BARBERSHOP_API_URL", "http://localhost:8000").rstrip("/") + path,
            headers=headers,
            **kwargs,
        )
        if response.status_code == 204:
            return {"success": True}
        data = response.json()
        if response.is_success:
            return {"success": True, "data": data}
        return {
            "success": False,
            "error": data.get("code", "API_ERROR"),
            "message": data.get("detail"),
        }
    except (httpx.HTTPError, ValueError):
        return {"success": False, "error": "RESULT_UNKNOWN"}
