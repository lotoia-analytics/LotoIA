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

_PENDING_QUANTITY: dict[str, int] = {}


def _available_quantities(*, saldo_hoje: int) -> list[int]:
    return [
        quantidade
        for quantidade in MENU_QUANTITIES
        if quantidade in VALID_QUANTITIES and quantidade <= saldo_hoje
    ]


def _reply_buttons(options: list[tuple[str, str]]) -> list[dict[str, str]]:
    return [
        {"type": "reply", "displayText": label, "id": selection_id}
        for label, selection_id in options[:3]
    ]


def build_quantity_menu_bundle(*, client_status: dict[str, Any]) -> dict[str, Any]:
    saldo_hoje = int(client_status.get("saldo_hoje", 0) or 0)
    plan = str(client_status.get("plan", "basico") or "basico")
    formato_maximo = int(client_status.get("formato_maximo", 15) or 15)
    quantities = _available_quantities(saldo_hoje=saldo_hoje)
    description = (
        f"Plano {plan} — até {formato_maximo}D\n"
        f"Saldo hoje: {saldo_hoje} jogos\n\n"
        "Quantos jogos você quer gerar?"
    )
    rows = [
        {
            "title": f"{quantidade} jogos",
            "description": f"Gerar {quantidade} cartões",
            "rowId": f"qty:{quantidade}",
        }
        for quantidade in quantities
    ] or [
        {
            "title": "Limite diário atingido",
            "description": "Volte amanhã às 00h",
            "rowId": "noop:limit",
        }
    ]
    button_options: list[tuple[str, str]] = [(f"{quantidade} jogos", f"qty:{quantidade}") for quantidade in quantities]
    if len(button_options) > 3:
        button_options = button_options[:2] + [("Outras quantidades", "qty:more")]
    poll_values = [label for label, _ in button_options if not _.endswith(":more")]
    if any(selection_id == "qty:more" for _, selection_id in button_options):
        poll_values.extend(f"{quantidade} jogos" for quantidade in quantities[2:])
    return {
        "list_payload": {
            "title": "LotoIA",
            "description": description,
            "buttonText": "Escolher quantidade",
            "footerText": "Toque para selecionar",
            "sections": [{"title": "Quantidade", "rows": rows}],
        },
        "buttons_payload": {
            "title": "LotoIA",
            "description": description,
            "footer": "LotoIA",
            "buttons": _reply_buttons(button_options),
        },
        "poll_payload": {
            "name": "Quantos jogos você quer gerar?",
            "selectableCount": 1,
            "values": poll_values or ["Limite diário atingido"],
        },
        "text_fallback": _build_quantity_text_fallback(quantities=quantities, client_status=client_status),
    }


def build_quantity_more_menu_bundle(*, client_status: dict[str, Any]) -> dict[str, Any]:
    saldo_hoje = int(client_status.get("saldo_hoje", 0) or 0)
    quantities = _available_quantities(saldo_hoje=saldo_hoje)[2:]
    description = "Escolha outra quantidade de jogos:"
    rows = [
        {"title": f"{quantidade} jogos", "description": "Gerar cartões", "rowId": f"qty:{quantidade}"}
        for quantidade in quantities
    ]
    button_options = [(f"{quantidade} jogos", f"qty:{quantidade}") for quantidade in quantities]
    return {
        "list_payload": {
            "title": "LotoIA",
            "description": description,
            "buttonText": "Escolher",
            "footerText": "LotoIA",
            "sections": [{"title": "Quantidade", "rows": rows}],
        },
        "buttons_payload": {
            "title": "LotoIA",
            "description": description,
            "footer": "LotoIA",
            "buttons": _reply_buttons(button_options),
        },
        "poll_payload": {
            "name": description,
            "selectableCount": 1,
            "values": [f"{quantidade} jogos" for quantidade in quantities],
        },
        "text_fallback": _build_quantity_text_fallback(quantities=quantities, client_status=client_status),
    }


def build_format_menu_bundle(*, quantidade: int, client_status: dict[str, Any]) -> dict[str, Any]:
    formato_maximo = int(client_status.get("formato_maximo", 15) or 15)
    plan = str(client_status.get("plan", "basico") or "basico")
    description = f"Você escolheu *{quantidade} jogos*.\nAgora selecione o formato:"
    rows = [
        {
            "title": f"{formato} dezenas ({formato}D)",
            "description": f"{quantidade} jogos no formato {formato}D",
            "rowId": f"gen:{quantidade}:{formato}",
        }
        for formato in range(15, formato_maximo + 1)
    ]
    button_options = [(f"{formato}D", f"gen:{quantidade}:{formato}") for formato in range(15, formato_maximo + 1)]
    if len(button_options) > 3:
        button_options = button_options[:2] + [("Mais formatos", f"fmtmore:{quantidade}")]
    poll_values = [f"{formato}D" for formato in range(15, formato_maximo + 1)]
    return {
        "list_payload": {
            "title": "LotoIA",
            "description": description,
            "buttonText": "Escolher formato",
            "footerText": f"Plano {plan}",
            "sections": [{"title": "Formato", "rows": rows}],
        },
        "buttons_payload": {
            "title": "LotoIA",
            "description": description,
            "footer": f"Plano {plan}",
            "buttons": _reply_buttons(button_options),
        },
        "poll_payload": {
            "name": f"Formato para {quantidade} jogos",
            "selectableCount": 1,
            "values": poll_values,
        },
        "text_fallback": _build_format_text_fallback(quantidade=quantidade, client_status=client_status),
    }


def build_format_more_menu_bundle(*, quantidade: int, client_status: dict[str, Any]) -> dict[str, Any]:
    formato_maximo = int(client_status.get("formato_maximo", 15) or 15)
    formatos = list(range(17, formato_maximo + 1))
    description = f"Mais formatos para {quantidade} jogos:"
    rows = [
        {
            "title": f"{formato}D",
            "description": f"{quantidade} jogos de {formato}D",
            "rowId": f"gen:{quantidade}:{formato}",
        }
        for formato in formatos
    ]
    button_options = [(f"{formato}D", f"gen:{quantidade}:{formato}") for formato in formatos]
    return {
        "list_payload": {
            "title": "LotoIA",
            "description": description,
            "buttonText": "Escolher",
            "footerText": "LotoIA",
            "sections": [{"title": "Formato", "rows": rows}],
        },
        "buttons_payload": {
            "title": "LotoIA",
            "description": description,
            "footer": "LotoIA",
            "buttons": _reply_buttons(button_options),
        },
        "poll_payload": {
            "name": description,
            "selectableCount": 1,
            "values": [f"{formato}D" for formato in formatos],
        },
        "text_fallback": _build_format_text_fallback(quantidade=quantidade, client_status=client_status, formatos=formatos),
    }


def _build_quantity_text_fallback(*, quantities: list[int], client_status: dict[str, Any]) -> str:
    formato_maximo = int(client_status.get("formato_maximo", 15) or 15)
    lines = ["🎰 *LotoIA*", "", "Escolha uma opção abaixo (toque para votar).", ""]
    for quantidade in quantities:
        lines.append(f"• {quantidade} jogos (até {formato_maximo}D)")
    return "\n".join(lines)


def _build_format_text_fallback(
    *,
    quantidade: int,
    client_status: dict[str, Any],
    formatos: list[int] | None = None,
) -> str:
    formato_maximo = int(client_status.get("formato_maximo", 15) or 15)
    target_formatos = formatos or list(range(15, formato_maximo + 1))
    lines = [f"🎰 *{quantidade} jogos*", "", "Escolha o formato:", ""]
    for formato in target_formatos:
        lines.append(f"• {formato}D")
    return "\n".join(lines)


def remember_pending_quantity(phone: str, quantidade: int) -> None:
    _PENDING_QUANTITY[str(phone)] = int(quantidade)


def pop_pending_quantity(phone: str) -> int | None:
    return _PENDING_QUANTITY.pop(str(phone), None)


def parse_menu_selection(selection_id: str, *, text: str = "", phone: str = "") -> dict[str, Any] | None:
    normalized = str(selection_id or "").strip().lower()
    if not normalized:
        normalized = _selection_id_from_text(text, phone=phone)
    if not normalized or normalized.startswith("noop:"):
        return None
    if normalized.startswith("gen:"):
        _, quantidade_raw, formato_raw = normalized.split(":", maxsplit=2)
        pop_pending_quantity(phone)
        return {"quantidade": int(quantidade_raw), "formato": int(formato_raw)}
    if normalized.startswith("fmtmore:"):
        return {"quantidade": int(normalized.split(":", maxsplit=1)[1]), "next_menu": "format_more"}
    if normalized.startswith("qty:"):
        value = normalized.split(":", maxsplit=1)[1]
        if value == "more":
            return {"next_menu": "quantity_more"}
        remember_pending_quantity(phone, int(value))
        return {"quantidade": int(value), "formato": None, "next_menu": "format"}
    return None


def _selection_id_from_text(text: str, *, phone: str) -> str:
    normalized = " ".join(str(text or "").strip().split()).lower()
    if not normalized:
        return ""
    for quantidade in MENU_QUANTITIES:
        if normalized in {f"{quantidade} jogos", f"{quantidade} jogo"}:
            return f"qty:{quantidade}"
    pending = _PENDING_QUANTITY.get(str(phone))
    if pending and normalized.endswith("d") and normalized[:-1].isdigit():
        return f"gen:{pending}:{int(normalized[:-1])}"
    return ""


# Backward-compatible helpers used in tests/imports
def build_quantity_list_payload(*, client_status: dict[str, Any]) -> dict[str, Any]:
    return dict(build_quantity_menu_bundle(client_status=client_status)["list_payload"])


def build_format_list_payload(*, quantidade: int, client_status: dict[str, Any]) -> dict[str, Any]:
    return dict(build_format_menu_bundle(quantidade=quantidade, client_status=client_status)["list_payload"])
