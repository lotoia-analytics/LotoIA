from __future__ import annotations

from lotoia.clients.interactive_menu import (
    build_confirm_menu_bundle,
    build_quantity_menu_bundle,
    is_greeting,
    parse_menu_selection,
    register_quick_options,
    remember_pending_quantity,
)


def test_build_quantity_menu_bundle_uses_buttons_only() -> None:
    bundle = build_quantity_menu_bundle(
        client_status={
            "plan": "pro",
            "formato_maximo": 18,
            "saldo_hoje": 30,
        }
    )
    assert "poll_payload" not in bundle
    assert bundle["buttons_payload"]["buttons"][0]["id"] == "qty:5"


def test_build_confirm_menu_bundle_has_gerar_jogos() -> None:
    bundle = build_confirm_menu_bundle(
        quantidade=10,
        client_status={"plan": "pro", "formato_maximo": 18, "saldo_hoje": 30},
    )
    buttons = bundle["buttons_payload"]["buttons"]
    assert buttons[0]["displayText"] == "Gerar Jogos"
    assert buttons[0]["id"] == "gen:10:15"


def test_is_greeting() -> None:
    assert is_greeting("olá")
    assert is_greeting("ola")
    assert is_greeting("Oi!")
    assert not is_greeting("5 jogos de 15D")


def test_numeric_quick_option_selection() -> None:
    register_quick_options("5511999999999", [("5 jogos", "qty:5"), ("10 jogos", "qty:10")])
    assert parse_menu_selection("", text="2", phone="5511999999999") == {
        "quantidade": 10,
        "formato": None,
        "next_menu": "confirm",
    }


def test_parse_menu_selection() -> None:
    assert parse_menu_selection("qty:10", phone="5511999999999") == {
        "quantidade": 10,
        "formato": None,
        "next_menu": "confirm",
    }
    assert parse_menu_selection("gen:5:15", phone="5511999999999") == {"quantidade": 5, "formato": 15}
    remember_pending_quantity("5511999999999", 10)
    assert parse_menu_selection("", text="Gerar Jogos", phone="5511999999999") == {"quantidade": 10, "formato": 15}
