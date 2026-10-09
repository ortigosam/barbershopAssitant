"""Minimal Meta WhatsApp Cloud API client."""

import httpx
import logging
from time import monotonic
from whatsapp.logging_config import mask_phone


logger = logging.getLogger(__name__)


class MetaWhatsAppClient:
    def __init__(self, access_token: str, phone_number_id: str, api_version: str):
        self.url = (
            f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
        )
        self.access_token = access_token

    async def send(self, recipient: str, message: dict) -> None:
        payload = {"messaging_product": "whatsapp", "recipient_type": "individual",
                   "to": recipient.lstrip("+"), **message}
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        started = monotonic()
        message_type = message.get("type", "unknown")
        logger.info("meta_send recipient=%s type=%s", mask_phone(recipient), message_type)
        async with httpx.AsyncClient(timeout=10) as client:
            response = None
            try:
                response = await client.post(self.url, json=payload, headers=headers)
                response.raise_for_status()
            except httpx.HTTPError:
                logger.exception("meta_send_failed recipient=%s type=%s elapsed_ms=%d status=%s body=%s",
                                 mask_phone(recipient), message_type,
                                 int((monotonic() - started) * 1000),
                                 getattr(response, "status_code", "network"),
                                 getattr(response, "text", "")[:300])
                raise
        logger.info("meta_send_ok recipient=%s type=%s status=%d elapsed_ms=%d",
                    mask_phone(recipient), message_type, response.status_code,
                    int((monotonic() - started) * 1000))
