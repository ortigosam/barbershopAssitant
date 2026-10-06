"""Signed Meta webhook and composition root for the deterministic booking flow."""
import hashlib
import hmac
import json
import logging
import re
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from whatsapp.booking_api import HttpBookingApi
from whatsapp.config import settings
from whatsapp.contracts import Incoming
from whatsapp.meta_client import MetaWhatsAppClient
from whatsapp.logging_config import configure_logging, mask_identifier, mask_phone
from whatsapp.workflow import Workflow


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    if not settings.meta_app_secret.strip() or not settings.agent_api_token.strip():
        raise RuntimeError("Configura META_APP_SECRET y AGENT_API_TOKEN.")
    async with httpx.AsyncClient(base_url=settings.barbershop_api_url, timeout=8) as client:
        app.state.workflow = Workflow(
            HttpBookingApi(client, settings.agent_api_token),
            MetaWhatsAppClient(settings.meta_access_token, settings.meta_phone_number_id,
                               settings.meta_api_version),
        )
        yield


app = FastAPI(title="Barbershop WhatsApp Webhook", version="0.2.0", lifespan=lifespan)


def verify_signature(body: bytes, signature: str) -> bool:
    if not settings.meta_app_secret:
        return False
    expected = hmac.new(settings.meta_app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, f"sha256={expected}")


def incoming_messages(payload: dict, phone_number_id: str):
    if payload.get("object") != "whatsapp_business_account":
        return
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if change.get("field") != "messages":
                continue
            if value.get("metadata", {}).get("phone_number_id") != phone_number_id:
                continue
            for message in value.get("messages", []):
                phone, identifier = message.get("from", ""), message.get("id")
                if not isinstance(phone, str) or not re.fullmatch(r"[1-9]\d{7,14}", phone) or not identifier:
                    continue
                interactive = message.get("interactive", {})
                selection = (interactive.get("list_reply") or interactive.get("button_reply") or {}).get("id", "")
                yield Incoming(str(identifier), "+" + phone,
                               message.get("text", {}).get("body", ""), selection)


@app.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(
    mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
):
    if mode == "subscribe" and token and hmac.compare_digest(
        token, settings.webhook_verify_token
    ) and challenge:
        return challenge
    raise HTTPException(403, "Verificación no válida.")


@app.post("/webhook")
async def receive_webhook(request: Request, x_hub_signature_256: Annotated[str, Header()] = ""):
    body = await request.body()
    if not verify_signature(body, x_hub_signature_256):
        logger.warning("webhook_signature_invalid bytes=%d", len(body))
        raise HTTPException(403, "Firma no válida.")
    try:
        payload = json.loads(body)
        messages = list(incoming_messages(payload, settings.meta_phone_number_id))
    except (ValueError, TypeError, AttributeError):
        logger.warning("webhook_payload_invalid bytes=%d", len(body))
        raise HTTPException(400, "Evento no válido.") from None
    logger.info("webhook_received messages=%d bytes=%d", len(messages), len(body))
    try:
        for message in messages:
            logger.info("message_received id=%s phone=%s selection=%s text=%s",
                        mask_identifier(message.id), mask_phone(message.phone),
                        message.selection or "-", bool(message.text.strip()))
            await request.app.state.workflow.handle(message)
    except httpx.HTTPError:
        logger.exception("webhook_delivery_failed")
        raise HTTPException(503, "No se ha podido entregar la respuesta.") from None
    return {"status": "ok"}
