from __future__ import annotations

from lotoia.clients.interactive_menu import (
    build_format_menu_bundle,
    build_quantity_menu_bundle,
    parse_menu_selection,
    remember_pending_quantity,
)


def test_build_quantity_menu_bundle_respects_plan_and_balance() -> None:
    bundle = build_quantity_menu_bundle(
        client_status={
            "plan": "pro",
            "formato_maximo": 18,
            "saldo_hoje": 30,
        }
    )
    rows = bundle["list_payload"]["sections"][0]["rows"]
    assert rows[0]["rowId"] == "qty:5"
    assert rows[-1]["rowId"] == "qty:30"
    assert bundle["poll_payload"]["values"][0] == "5 jogos"


def test_build_format_menu_bundle_uses_plan_limit() -> None:
    bundle = build_format_menu_bundle(
        quantidade=5,
        client_status={"plan": "pro", "formato_maximo": 18, "saldo_hoje": 30},
    )
    rows = bundle["list_payload"]["sections"][0]["rows"]
    assert rows[0]["rowId"] == "gen:5:15"
    assert rows[-1]["rowId"] == "gen:5:18"


def test_parse_menu_selection() -> None:
    assert parse_menu_selection("qty:10", phone="5511999999999") == {
        "quantidade": 10,
        "formato": None,
        "next_menu": "format",
    }
    assert parse_menu_selection("gen:5:15", phone="5511999999999") == {"quantidade": 5, "formato": 15}
    assert parse_menu_selection("", text="20 jogos", phone="5511999999999") == {
        "quantidade": 20,
        "formato": None,
        "next_menu": "format",
    }
    remember_pending_quantity("5511999999999", 5)
    assert parse_menu_selection("", text="17D", phone="5511999999999") == {"quantidade": 5, "formato": 17}
