from __future__ import annotations

from lotoia.clients.interactive_menu import (
    build_confirm_menu_bundle,
    build_quantity_menu_bundle,
    build_welcome_text,
    clear_awaiting_custom_quantity,
    is_awaiting_custom_quantity,
    is_greeting,
    parse_custom_quantity,
    parse_menu_selection,
    set_awaiting_custom_quantity,
)


def test_build_quantity_menu_bundle_uses_professional_list() -> None:
    bundle = build_quantity_menu_bundle(
        client_status={
            "plan": "basico",
            "formato_maximo": 15,
            "saldo_hoje": 30,
        }
    )
    assert bundle["prefer_list"] is True
    rows = bundle["list_payload"]["sections"][0]["rows"]
    assert [row["title"] for row in rows] == ["05 Jogos", "10 Jogos", "20 Jogos", "Outra quantidade"]
    assert bundle["buttons_payload"]["buttons"][0]["displayText"] == "05 Jogos"
    assert "1 —" not in bundle["text_fallback"]


def test_build_welcome_text_is_clean() -> None:
    text = build_welcome_text(
        client_status={"plan": "basico", "formato_maximo": 15, "saldo_hoje": 30}
    )
    assert "Escolher quantidade" in text
    assert "1 —" not in text


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


def test_parse_menu_selection_fixed_and_custom() -> None:
    assert parse_menu_selection("qty:10", phone="5511999999999") == {
        "quantidade": 10,
        "formato": 15,
    }
    assert parse_menu_selection("qty:custom", phone="5511999999999") == {
        "next_menu": "await_custom_quantity",
    }
    assert parse_menu_selection("gen:5:15", phone="5511999999999") == {"quantidade": 5, "formato": 15}


def test_parse_custom_quantity() -> None:
    assert parse_custom_quantity("3") == 3
    assert parse_custom_quantity("3 jogos") == 3
    assert parse_custom_quantity("olá") is None


def test_awaiting_custom_quantity_state() -> None:
    set_awaiting_custom_quantity("5511999999999", 30)
    assert is_awaiting_custom_quantity("5511999999999") is True
    clear_awaiting_custom_quantity("5511999999999")
    assert is_awaiting_custom_quantity("5511999999999") is False
