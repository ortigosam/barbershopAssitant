"""Authenticated HTTP adapter to the existing customer API."""
import httpx
import logging
from time import monotonic
from whatsapp.contracts import ApiError
from whatsapp.logging_config import mask_phone


logger = logging.getLogger(__name__)


class HttpBookingApi:
    def __init__(self, client: httpx.AsyncClient, token: str):
        self.client, self.token = client, token

    async def request(self, phone, method, path, **kwargs):
        started = monotonic()
        logger.info("api_request method=%s path=%s phone=%s", method, path, mask_phone(phone))
        try:
            response = await self.client.request(method, path, headers={
                "Authorization": f"Bearer {self.token}",
                "X-Customer-Phone": phone,
            }, **kwargs)
        except httpx.RequestError as error:
            logger.exception("api_request_network_error method=%s path=%s elapsed_ms=%d",
                             method, path, int((monotonic() - started) * 1000))
            raise ApiError("UNCERTAIN") from None
        logger.info("api_response method=%s path=%s status=%d elapsed_ms=%d",
                    method, path, response.status_code,
                    int((monotonic() - started) * 1000))
        if response.status_code == 204:
            return None
        if response.is_error:
            try:
                code = response.json().get("code", "API_ERROR")
            except ValueError:
                code = "API_ERROR"
            logger.warning("api_response_error method=%s path=%s status=%d code=%s",
                           method, path, response.status_code, code)
            raise ApiError(code)
        return response.json()

    async def customer(self, phone):
        return await self.request(phone, "GET", "/clients/me")

    async def create_customer(self, phone, name):
        return await self.request(phone, "POST", "/clients/me", json={"name": name})

    async def slots(self, phone, week):
        return (await self.request(phone, "GET", "/bookings/availability",
                                   params={"week": week, "count": 1}))["slots"]

    async def bookings(self, phone):
        return await self.request(phone, "GET", "/bookings")

    async def reserve(self, phone, timestamp, request_id):
        return await self.request(phone, "POST", "/bookings", json={
            "timestamp": timestamp, "count": 1, "request_id": request_id})

    async def cancel(self, phone, identifier):
        await self.request(phone, "DELETE", f"/bookings/{identifier}")
