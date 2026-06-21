from __future__ import annotations

from lotoia.clients.interactive_menu import (
    allowed_formats_for_client,
    build_confirm_menu_bundle,
    build_quantity_menu_bundle,
    build_welcome_text,
    clear_awaiting_custom_quantity,
    distribute_quantidade_across_formats,
    is_awaiting_custom_quantity,
    is_greeting,
    parse_custom_quantity,
    parse_menu_selection,
    plan_generation_targets,
    set_awaiting_custom_quantity,
)


def test_build_quantity_menu_bundle_is_text_only() -> None:
    bundle = build_quantity_menu_bundle(
        client_status={
            "plan": "basico",
            "formato_maximo": 15,
            "saldo_hoje": 30,
        }
    )
    assert bundle["text_only"] is True
    assert "Digite: 5, 10, 20" in bundle["text_fallback"]
    assert "Toque" not in bundle["text_fallback"]


def test_build_welcome_text_is_clean() -> None:
    text = build_welcome_text(
        client_status={
            "plan": "completo",
            "formato_maximo_efetivo": 15,
            "formatos_disponiveis": "15D (fase inicial — 7 dias)",
            "dias_trial_restantes": 7,
            "saldo_hoje": 30,
        }
    )
    assert "Plano Completo" in text
    assert "15D" in text
    assert "Fase inicial" in text


def test_build_welcome_text_for_full_phase() -> None:
    text = build_welcome_text(
        client_status={
            "plan": "completo",
            "formato_maximo_efetivo": 20,
            "formatos_disponiveis": "15D (7 dias) → 15D + 20D",
            "dias_trial_restantes": 0,
            "saldo_hoje": 30,
        }
    )
    assert "15D + 20D" in text
    assert "Jogos gerados em 15D e 20D (metade de cada)." in text
    assert "2x20D" in text


def test_allowed_formats_for_client() -> None:
    assert allowed_formats_for_client({"formato_maximo_efetivo": 15}) == [15]
    assert allowed_formats_for_client({"formato_maximo_efetivo": 20}) == [15, 20]
    assert allowed_formats_for_client({"formato_maximo": 18}) == [15, 18]
    assert allowed_formats_for_client(None) == [15]


def test_distribute_quantidade_across_formats() -> None:
    assert distribute_quantidade_across_formats(5, [15]) == [(15, 5)]
    assert distribute_quantidade_across_formats(5, [15, 18]) == [(15, 3), (18, 2)]
    assert distribute_quantidade_across_formats(10, [15, 16]) == [(15, 5), (16, 5)]


def test_plan_generation_targets_splits_by_plan() -> None:
    assert plan_generation_targets(
        {"quantidade": 5, "formato": None},
        client_status={"formato_maximo": 18},
    ) == [(15, 3), (18, 2)]
    assert plan_generation_targets(
        {"quantidade": 5, "formato": 15},
        client_status={"formato_maximo": 18},
    ) == [(15, 5)]
    assert plan_generation_targets(
        {"quantidade": 4, "formato": None},
        client_status={"formato_maximo": 16},
    ) == [(15, 2), (16, 2)]


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


def test_selection_id_from_text_accepts_flexible_format_messages() -> None:
    assert parse_menu_selection("", text="2x18D", phone="5511999999999") == {
        "quantidade": 2,
        "formato": 18,
    }
    assert parse_menu_selection("", text="03", phone="5511999999999") == {
        "quantidade": 3,
        "formato": None,
    }
    assert parse_menu_selection("", text="3 Jogo 18D", phone="5511999999999") == {
        "quantidade": 3,
        "formato": 18,
    }


def test_parse_menu_selection_fixed_and_custom() -> None:
    assert parse_menu_selection("qty:10", phone="5511999999999") == {
        "quantidade": 10,
        "formato": None,
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
