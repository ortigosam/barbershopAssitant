"""LangChain agent used by the barbershop WhatsApp integration.

The tools call the FastAPI service, which remains the single source of truth
for customers, bookings and free appointment slots.
"""

import os
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_ollama import ChatOllama

from agent.tools.booking_tools import (
    create_booking,
    get_booking,
    update_booking,
    delete_booking,
    get_available_slots,
)
from agent.tools.client_tools import create_client, get_client


SYSTEM_PROMPT = """Eres el asistente de una barbería y respondes siempre en español.
Usa las herramientas para cualquier dato de clientes o citas; nunca inventes
un identificador, cliente ni hueco. Antes de crear o cambiar una cita consulta
get_available_slots y usa sólo uno de los huecos devueltos. Si el cliente no
existe, pide nombre y teléfono y crea el cliente antes de reservar. Antes de
cancelar o editar, solicita el identificador de la reserva si no lo tienes.
Confirma al cliente el día, hora e identificador de la cita cuando corresponda.
"""

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


def build_whatsapp_agent(llm: Any | None = None) -> Any:
    """Build the LangChain v1 agent backed by a local Ollama model."""
    model = llm or ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "qwen3:4b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
    )
    return create_agent(
        model=model,
        tools=[
            create_client,
            get_client,
            get_available_slots,
            create_booking,
            get_booking,
            update_booking,
            delete_booking,
        ],
        system_prompt=SYSTEM_PROMPT,
    )


def handle_whatsapp_message(agent: Any, message: str) -> str:
    """Invoke an agent with one WhatsApp message and return its final text."""
    result = agent.invoke({"messages": [{"role": "user", "content": message}]})
    content = result["messages"][-1].content
    if isinstance(content, str):
        return content
    return str(content)


__all__ = ["build_whatsapp_agent", "handle_whatsapp_message"]
