from unittest.mock import Mock

from agent import cli


def test_phone_flag_without_value_prompts(monkeypatch):
    monkeypatch.setattr("sys.argv", ["cli", "--phone"])
    answers = iter(["+34600123456", "salir"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    build = Mock()
    monkeypatch.setattr(cli, "build_whatsapp_agent", build)
    cli.main()
    build.assert_called_once_with(customer_phone="+34600123456")
