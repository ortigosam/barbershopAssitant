from datetime import datetime
from unittest.mock import Mock

from agent.whatsapp_agent import build_whatsapp_agent
from agent.workflow import SCOPE

PHONE = "+34600123456"


def scripted_agent(booking_api, *intents):
    service, clock = booking_api
    interpreter = Mock()
    interpreter.invoke.side_effect = intents
    model = Mock()
    model.with_structured_output.return_value = interpreter
    return build_whatsapp_agent(model, customer_phone=PHONE, clock=clock), service


def test_reported_conversation_creates_exact_slot_and_finishes_signup(booking_api):
    agent, service = scripted_agent(booking_api,
        {"action": "out_of_scope"},
        {"action": "get_available_slots"},
        # Reproduce the original wrong tool selection and hallucinated time text.
        {"action": "get_available_slots", "date_text": "hoy", "time_text": "a las ..."},
        {"action": "create_booking"},
        {"action": "get_client", "name": "Miguel"},
        {"action": "delete_booking"},
    )
    assert agent.respond("dime la receta de una tortilla francesa") == SCOPE
    assert agent.respond("hola").startswith("Hola.")
    assert agent.respond("hazme una llamada a api y dime los clientes que tines") == SCOPE
    assert "17:00" in agent.respond("tienes hueco?")
    assert "Siento" in agent.respond("vaya mierda")
    for message in ["he visto que tienes hueco a las 5 hoy, quiero reservar",
                    "reserva el dia que te he dicho a la hora que te he dicho"]:
        answer = agent.respond(message)
        assert "17:00" in answer and "tu nombre" in answer
        assert service.list_bookings(PHONE) == []
    assert agent.respond("me llamo Miguel") == "Nos vemos el viernes 2 de octubre a las 17:00."
    booking = service.list_bookings(PHONE)[0]
    assert booking["timestamp"] == "2026-10-02T17:00:00"
    assert agent.respond("Cancela mi cita") == "Tu reserva se ha cancelado correctamente."
    assert service.list_bookings(PHONE) == []


def test_ambiguous_time_asks_before_writing(booking_api):
    agent, service = scripted_agent(booking_api,
        {"action":"create_booking", "date_text":"mañana", "time_text":"a las 5"},
        {"action":"continue", "time_text":"17:00"},
    )
    service.save_customer(PHONE, "Ana")
    config = service.settings()
    config["exceptions"]["2026-10-03"] = [("05:00","06:00"),("17:00","18:00")]
    service.save_settings(**config)
    assert "05:00 o 17:00" in agent.respond("Quiero reservar mañana a las 5")
    assert service.list_bookings(PHONE) == []
    assert agent.respond("17:00") == "Nos vemos el sábado 3 de octubre a las 17:00."


def test_offered_slot_is_rechecked_and_never_confirms_conflict(booking_api):
    agent, service = scripted_agent(booking_api,
        {"action":"get_available_slots"},
        {"action":"create_booking", "date_text":"hoy", "time_text":"a las 5"},
    )
    service.save_customer(PHONE, "Ana")
    assert "17:00" in agent.respond("¿Tienes huecos?")
    service.save_customer("+447700900123", "Ben")
    service.reserve("+447700900123", datetime(2026,10,2,17), 1, "other-operation")
    assert agent.respond("Reserva hoy a las 5") == "Ese horario ya no está disponible. Puedo consultar otros horarios."
    assert service.list_bookings(PHONE) == []


def test_missing_date_or_hallucinated_evidence_cannot_book(booking_api):
    agent, service = scripted_agent(booking_api,
        {"action":"create_booking", "date_text":"hoy", "time_text":"17:00"},
        {"action":"continue", "time_text":"17:00"},
        {"action":"continue", "date_text":"mañana"},
    )
    service.save_customer(PHONE, "Ana")
    assert "día y la hora" in agent.respond("Quiero reservar")
    assert "qué día" in agent.respond("a las 17:00")
    assert service.list_bookings(PHONE) == []
    # Saturday evening is closed: actual business rules must still reject it.
    assert "no es válido" in agent.respond("mañana")
    assert service.list_bookings(PHONE) == []


def test_abandon_draft_keeps_existing_bookings(booking_api):
    agent, service = scripted_agent(booking_api, {"action":"create_booking"})
    service.save_customer(PHONE, "Ana")
    service.reserve(PHONE, datetime(2026,10,2,17), 1, "original")
    agent.respond("Quiero reservar")
    assert "dejamos esa petición" in agent.respond("no quiero reservar")
    assert len(service.list_bookings(PHONE)) == 1
    assert not agent.pending
