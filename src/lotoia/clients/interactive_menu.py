from __future__ import annotations

from typing import Any

from lotoia.clients.constants import VALID_QUANTITIES

MENU_QUANTITIES = (5, 10, 20, 30)

HELP_MESSAGE = (
    "Olá! Para gerar jogos, use o menu abaixo.\n"
    "Toque em *Escolher* e selecione quantidade e formato."
)

UNREGISTERED_MESSAGE = (
    "Número não cadastrado.\n"
    "Acesse lotoia.chat para assinar."
)


def _available_quantities(*, saldo_hoje: int) -> list[int]:
    return [
        quantidade
        for quantidade in MENU_QUANTITIES
        if quantidade in VALID_QUANTITIES and quantidade <= saldo_hoje
    ]


def build_quantity_list_payload(*, client_status: dict[str, Any]) -> dict[str, Any]:
    saldo_hoje = int(client_status.get("saldo_hoje", 0) or 0)
    plan = str(client_status.get("plan", "basico") or "basico")
    formato_maximo = int(client_status.get("formato_maximo", 15) or 15)
    quantities = _available_quantities(saldo_hoje=saldo_hoje)
    rows = [
        {
            "title": f"{quantidade} jogos",
            "description": f"Gerar {quantidade} cartões",
            "rowId": f"qty:{quantidade}",
        }
        for quantidade in quantities
    ]
    if not rows:
        rows = [
            {
                "title": "Limite diário atingido",
                "description": "Volte amanhã às 00h",
                "rowId": "noop:limit",
            }
        ]
    return {
        "title": "LotoIA",
        "description": (
            f"Plano {plan} — até {formato_maximo}D\n"
            f"Saldo hoje: {saldo_hoje} jogos\n\n"
            "Quantos jogos você quer gerar?"
        ),
        "buttonText": "Escolher quantidade",
        "footerText": "Toque para selecionar",
        "sections": [{"title": "Quantidade", "rows": rows}],
    }


def build_format_list_payload(*, quantidade: int, client_status: dict[str, Any]) -> dict[str, Any]:
    formato_maximo = int(client_status.get("formato_maximo", 15) or 15)
    plan = str(client_status.get("plan", "basico") or "basico")
    rows = [
        {
            "title": f"{formato} dezenas ({formato}D)",
            "description": f"{quantidade} jogos no formato {formato}D",
            "rowId": f"gen:{quantidade}:{formato}",
        }
        for formato in range(15, formato_maximo + 1)
    ]
    return {
        "title": "LotoIA",
        "description": f"Você escolheu *{quantidade} jogos*.\nAgora selecione o formato:",
        "buttonText": "Escolher formato",
        "footerText": f"Plano {plan}",
        "sections": [{"title": "Formato", "rows": rows}],
    }


def parse_menu_selection(selection_id: str) -> dict[str, Any] | None:
    normalized = str(selection_id or "").strip().lower()
    if not normalized or normalized.startswith("noop:"):
        return None
    if normalized.startswith("gen:"):
        _, quantidade_raw, formato_raw = normalized.split(":", maxsplit=2)
        return {"quantidade": int(quantidade_raw), "formato": int(formato_raw)}
    if normalized.startswith("qty:"):
        return {"quantidade": int(normalized.split(":", maxsplit=1)[1]), "formato": None, "next_menu": "format"}
    return None
