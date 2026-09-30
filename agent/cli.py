"""Small local smoke-test client for the WhatsApp agent.

Run from the repository root with:
    uv run python -m agent.cli

Ollama must already be running and the model must have been pulled. Configure
OLLAMA_BASE_URL and OLLAMA_MODEL in agent/.env (or export them as environment
variables).
"""

from agent.whatsapp_agent import build_whatsapp_agent, handle_whatsapp_message


def main() -> None:
    agent = build_whatsapp_agent()
    print("Agente listo. Escribe 'salir' para terminar.")

    while True:
        try:
            message = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if message.lower() in {"salir", "exit", "quit"}:
            break
        if not message:
            continue

        try:
            print(f"Agente: {handle_whatsapp_message(agent, message)}")
        except Exception as error:  # pragma: no cover - local diagnostic boundary
            print(f"Error ejecutando el agente: {error}")


if __name__ == "__main__":
    main()
