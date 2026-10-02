"""Local channel simulation. In WhatsApp the verified sender supplies identity."""

import argparse

from agent.whatsapp_agent import build_whatsapp_agent, handle_whatsapp_message


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phone", help="Simulated WhatsApp sender, including international prefix"
    )
    args = parser.parse_args()
    telephone = (
        args.phone
        or input("Tu número de WhatsApp (con prefijo internacional): ").strip()
    )
    agent = build_whatsapp_agent(customer_phone=telephone)
    print("Agente listo. Escribe 'salir' para terminar.")
    while True:
        try:
            message = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if message.lower() in {"salir", "exit", "quit"}:
            break
        if message:
            print("Agente: " + handle_whatsapp_message(agent, message))


if __name__ == "__main__":
    main()
