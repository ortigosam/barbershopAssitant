"""The sender header is accepted ONLY from an authenticated channel adapter.

The provider adapter must validate the WhatsApp webhook signature first.
Admin credentials are separate and never passed to the customer's LLM.
"""

from secrets import compare_digest
from typing import Annotated

from fastapi import Header, HTTPException
from src.config import settings
from src.domain.calendar import phone


def check_token(authorization, expected):
    token = authorization.removeprefix("Bearer ")
    if (
        not expected
        or not authorization.startswith("Bearer ")
        or not compare_digest(token.encode(), expected.encode())
    ):
        raise HTTPException(401, "Credenciales no válidas.")


def actor(
    authorization: Annotated[str, Header()] = "",
    x_customer_phone: Annotated[str, Header()] = "",
):
    check_token(authorization, settings.agent_api_token)
    return phone(x_customer_phone)


def administrator(authorization: Annotated[str, Header()] = ""):
    check_token(authorization, settings.admin_api_token)
