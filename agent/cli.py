"""Local channel simulation. In WhatsApp the verified sender supplies identity."""

import argparse
import logging

from agent.whatsapp_agent import build_whatsapp_agent, handle_whatsapp_message


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phone", nargs="?", help="Número de prueba con prefijo internacional; si falta, se solicita al iniciar"
    )
    parser.add_argument("--debug", action="store_true", help="Mostrar clasificación, resolución de hora y resultados de tools")
    args = parser.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.WARNING, format="[%(name)s] %(message)s")
        logging.getLogger("agent").setLevel(logging.DEBUG)
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
