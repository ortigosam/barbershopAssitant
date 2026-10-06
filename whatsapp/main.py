"""Simple WhatsApp Cloud API webhook.

This module intentionally contains no booking or customer logic. Every inbound
message receives the same three-option survey.
"""

import hashlib
import hmac
from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from whatsapp.config import settings
from whatsapp.meta_client import MetaWhatsAppClient

app = FastAPI(title="Barbershop WhatsApp Webhook", version="0.1.0")
whatsapp = MetaWhatsAppClient(
    settings.meta_access_token,
    settings.meta_phone_number_id,
    settings.meta_api_version,
)


def verify_signature(body: bytes, signature: str) -> bool:
    """Validate Meta's X-Hub-Signature-256 when an app secret is configured."""

    if not settings.meta_app_secret:
        return True
    expected = hmac.new(
        settings.meta_app_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, f"sha256={expected}")


def incoming_senders(payload: dict[str, Any]) -> list[str]:
    """Extract senders from message events and ignore delivery statuses."""

    senders: list[str] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                sender = message.get("from")
                if isinstance(sender, str) and sender:
                    senders.append(sender)
    return senders


@app.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(
    mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
):
    if mode == "subscribe" and token == settings.webhook_verify_token and challenge:
        return challenge
    raise HTTPException(status_code=403, detail="Verificación no válida.")


@app.post("/webhook")
async def receive_webhook(
    request: Request,
    x_hub_signature_256: Annotated[str, Header()] = "",
):
    body = await request.body()
    if not verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Firma no válida.")

    payload = await request.json()
    for sender in incoming_senders(payload):
        await whatsapp.send_survey(sender)
    return {"status": "ok"}
