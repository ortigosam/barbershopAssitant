from unittest.mock import Mock

from agent.workflow import SCOPE, BookingConversation, Intent


def conversation(*intents):
    interpreter = Mock()
    interpreter.invoke.side_effect = [Intent(**i) for i in intents]
    names = (
        "get_client",
        "create_client",
        "update_client",
        "get_available_slots",
        "list_bookings",
        "create_booking",
        "update_booking",
        "delete_booking",
    )
    tools = {name: Mock() for name in names}
    tools["get_client"].invoke.return_value = {"success": True, "data": {"name": "Ana"}}
    tools["create_booking"].invoke.return_value = {
        "success": True,
        "data": {"bookings": [{"id": 1, "timestamp": "2026-10-06T10:00:00"}]},
    }
    tools["list_bookings"].invoke.return_value = {"success": True, "data": []}
    return BookingConversation(interpreter, tools, "+34600123456"), tools


def test_out_of_scope():
    a, tools = conversation({"action": "out_of_scope"})
    assert a.respond("Capital de Francia") == SCOPE
    assert not any(t.invoke.called for t in tools.values())


def test_slot_filling_and_exact_confirmation():
    a, tools = conversation(
        {"action": "create_booking"},
        {"action": "continue", "timestamp": "2026-10-06T10:00:00"},
    )
    assert "día y la hora" in a.respond("Quiero reservar")
    assert (
        a.respond("6 de octubre a las 10")
        == "Nos vemos el martes 6 de octubre a las 10:00."
    )
    assert "telephone" not in tools["create_booking"].invoke.call_args.args[0]


def test_unknown_reuses_request():
    a, tools = conversation(
        {"action": "create_booking", "timestamp": "2026-10-06T10:00:00"},
        {"action": "continue"},
    )
    tools["create_booking"].invoke.return_value = {
        "success": False,
        "error": "RESULT_UNKNOWN",
    }
    assert "No puedo confirmar" in a.respond("Reserva")
    key = tools["create_booking"].invoke.call_args.args[0]["request_id"]
    a.respond("Reintenta")
    assert tools["create_booking"].invoke.call_args.args[0]["request_id"] == key


def test_multiple_owned_appointments_need_selection():
    a, tools = conversation({"action": "delete_booking"})
    tools["list_bookings"].invoke.return_value = {
        "success": True,
        "data": [
            {"id": 1, "timestamp": "2026-10-06T10:00:00"},
            {"id": 2, "timestamp": "2026-10-07T10:00:00"},
        ],
    }
    tools["delete_booking"].invoke.return_value = {"success": True}
    assert "varias citas" in a.respond("Cancela mi cita")
    assert "Elige" in a.respond("999")
    assert not tools["delete_booking"].invoke.called
    assert a.respond("2") == "Tu reserva se ha cancelado correctamente."


def test_new_customer_and_no_identity_in_model():
    a, tools = conversation(
        {"action": "create_booking", "timestamp": "2026-10-06T10:00:00"},
        {"action": "continue", "name": "Ana"},
    )
    tools["get_client"].invoke.return_value = {
        "success": False,
        "error": "CLIENT_NOT_FOUND",
    }
    tools["create_client"].invoke.return_value = {"success": True}
    assert "tu nombre" in a.respond("Reserva")
    assert "Nos vemos" in a.respond("Ana")
    tools["create_client"].invoke.assert_called_with({"name": "Ana"})


def test_both_weeks():
    a, tools = conversation({"action": "get_available_slots", "week": "both"})
    tools["get_available_slots"].invoke.side_effect = [
        {"success": True, "data": {"slots": []}},
        {"success": True, "data": {"slots": []}},
    ]
    a.respond("Ambas semanas")
    assert [
        c.args[0]["week"] for c in tools["get_available_slots"].invoke.call_args_list
    ] == ["current", "next"]


def test_failure_never_confirms():
    a, tools = conversation(
        {"action": "create_booking", "timestamp": "2026-10-06T10:00:00"}
    )
    tools["create_booking"].invoke.return_value = {
        "success": False,
        "error": "MONTHLY_LIMIT",
    }
    assert "cinco citas" in a.respond("Reserva")


def test_new_intent_replaces_old():
    a, tools = conversation({"action": "create_booking"}, {"action": "get_client"})
    a.respond("Reserva")
    assert a.respond("Existe mi ficha") == "Tu ficha de cliente ya existe."


def test_irrelevant_model_count_is_ignored_but_booking_count_is_validated():
    a, tools = conversation()
    a.interpreter.invoke.side_effect = [
        {"action": "list_bookings", "count": 0},
        {"action": "create_booking", "count": 0},
    ]
    assert a.respond("Consulta mis citas") == "No tienes citas próximas."
    assert "No he podido interpretar" in a.respond("Reserva cero cortes")
    assert not tools["create_booking"].invoke.called
