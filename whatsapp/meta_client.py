"""Minimal Meta WhatsApp Cloud API client."""

from typing import Final

import httpx


SURVEY_TEXT: Final = "¿Qué necesitas hacer?"
SURVEY_OPTIONS: Final = (
    ("reserve_booking", "Reservar Cita"),
    ("cancel_booking", "Cancelar Cita"),
    ("list_bookings", "Ver mis próximas Citas"),
)


class MetaWhatsAppClient:
    def __init__(self, access_token: str, phone_number_id: str, api_version: str):
        self.url = (
            f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
        )
        self.access_token = access_token

    async def send_survey(self, recipient: str) -> None:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": SURVEY_TEXT},
                "action": {
                    "button": "Seleccionar",
                    "sections": [
                        {
                            "title": "Opciones",
                            "rows": [
                                {"id": option_id, "title": title}
                                for option_id, title in SURVEY_OPTIONS
                            ],
                        }
                        ],
                },
            },
        }
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(self.url, json=payload, headers=headers)
            response.raise_for_status()
