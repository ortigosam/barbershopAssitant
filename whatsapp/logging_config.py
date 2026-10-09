"""Logging helpers for the WhatsApp integration.

Logs are intentionally concise and redact phone numbers and message identifiers.
"""

import logging
import os


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def mask_phone(phone: str) -> str:
    """Keep only the last four digits, enough to correlate a conversation."""
    digits = phone.lstrip("+")
    return f"***{digits[-4:]}" if len(digits) >= 4 else "***"


def mask_identifier(identifier: str) -> str:
    return f"...{identifier[-8:]}" if len(identifier) > 8 else identifier
