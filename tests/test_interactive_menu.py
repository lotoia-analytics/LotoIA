from __future__ import annotations

from lotoia.clients.interactive_menu import (
    build_format_list_payload,
    build_quantity_list_payload,
    parse_menu_selection,
)


def test_build_quantity_list_payload_respects_plan_and_balance() -> None:
    payload = build_quantity_list_payload(
        client_status={
            "plan": "pro",
            "formato_maximo": 18,
            "saldo_hoje": 30,
        }
    )
    rows = payload["sections"][0]["rows"]
    assert rows[0]["rowId"] == "qty:5"
    assert rows[-1]["rowId"] == "qty:30"


def test_build_format_list_payload_uses_plan_limit() -> None:
    payload = build_format_list_payload(
        quantidade=5,
        client_status={"plan": "pro", "formato_maximo": 18, "saldo_hoje": 30},
    )
    rows = payload["sections"][0]["rows"]
    assert rows[0]["rowId"] == "gen:5:15"
    assert rows[-1]["rowId"] == "gen:5:18"


def test_parse_menu_selection() -> None:
    assert parse_menu_selection("qty:10") == {"quantidade": 10, "formato": None, "next_menu": "format"}
    assert parse_menu_selection("gen:5:15") == {"quantidade": 5, "formato": 15}
