"""LangChain agent used by the barbershop WhatsApp integration.

The tools call the FastAPI service, which remains the single source of truth
for customers, bookings and free appointment slots.
"""

import os
from pathlib import Path
from typing import Any

from langchain_ollama import ChatOllama

from agent.tools.booking_tools import (
    create_booking,
    delete_booking,
    get_available_slots,
    get_booking,
    list_bookings,
    update_booking,
)
from agent.tools.client_tools import create_client, get_client, update_client
from agent.workflow import BookingConversation, extraction_schema


def _load_local_env() -> None:
    """Load simple KEY=VALUE entries without adding a dotenv dependency."""
    # Keep agent settings isolated from API/database credentials. When the
    # CLI runs from the repository root, this explicitly selects agent/.env.
    candidates = (
        Path(__file__).resolve().parent / ".env",
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[1] / ".env",
    )
    env_path = next((path for path in candidates if path.is_file()), None)
    if env_path is None:
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env()


def build_whatsapp_agent(llm: Any | None = None, *, customer_phone: str) -> Any:
    """Build the LangChain v1 agent backed by a local Ollama model."""
    model = llm or ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "qwen3:4b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
        reasoning=False,
        num_predict=256,
        num_ctx=4096,
        keep_alive="30m",
    )
    return BookingConversation(
        model.with_structured_output(extraction_schema(), method="json_schema"),
        {
            tool.name: tool
            for tool in [
                create_client,
                get_client,
                update_client,
                list_bookings,
                get_available_slots,
                create_booking,
                get_booking,
                update_booking,
                delete_booking,
            ]
        },
        customer_phone,
    )


def handle_whatsapp_message(agent: Any, message: str) -> str:
    """Invoke an agent with one WhatsApp message and return its final text."""
    return agent.respond(message)


__all__ = ["build_whatsapp_agent", "handle_whatsapp_message"]
