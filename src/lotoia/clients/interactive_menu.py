from __future__ import annotations

from typing import Any

from lotoia.clients.constants import VALID_QUANTITIES

MENU_QUANTITIES = (5, 10, 20, 30)

DEFAULT_GAME_FORMAT = 15

HELP_MESSAGE = "Quantos jogos você quer gerar hoje?"

UNREGISTERED_MESSAGE = (
    "Número não cadastrado.\n"
    "Acesse lotoia.chat para assinar."
)

_PENDING_QUANTITY: dict[str, int] = {}
_PENDING_QUICK_OPTIONS: dict[str, list[tuple[str, str]]] = {}

_GREETINGS = {
    "oi",
    "ola",
    "olá",
    "oie",
    "bom dia",
    "boa tarde",
    "boa noite",
    "eai",
    "e aí",
    "hey",
    "hello",
    "hi",
}


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


def is_greeting(text: str) -> bool:
    normalized = " ".join(str(text or "").strip().lower().split())
    normalized = normalized.strip("!?.")
    return normalized in _GREETINGS


def register_quick_options(phone: str, button_options: list[tuple[str, str]]) -> str:
    _PENDING_QUICK_OPTIONS[str(phone)] = list(button_options[:3])
    lines = ["👋 *Olá! Bem-vindo à LotoIA*", "", "*Quantos jogos quer gerar?*", ""]
    for index, (label, _) in enumerate(button_options[:3], start=1):
        lines.append(f"*{index}* — {label}")
    lines.extend(
        [
            "",
            "Toque nos botões abaixo ou responda só o número (1, 2 ou 3).",
        ]
    )
    return "\n".join(lines)


def _menu_bundle(
    *,
    description: str,
    button_options: list[tuple[str, str]],
    list_rows: list[dict[str, str]],
    list_button_text: str,
    footer: str = "LotoIA",
    text_fallback: str = "",
) -> dict[str, Any]:
    return {
        "button_options": button_options,
        "buttons_payload": {
            "title": "LotoIA",
            "description": description,
            "footer": footer,
            "buttons": _reply_buttons(button_options),
        },
        "list_payload": {
            "title": "LotoIA",
            "description": description,
            "buttonText": list_button_text,
            "footerText": footer,
            "sections": [{"title": "Opções", "rows": list_rows}],
        },
        "text_fallback": text_fallback or description,
    }


def build_quantity_menu_bundle(*, client_status: dict[str, Any]) -> dict[str, Any]:
    saldo_hoje = int(client_status.get("saldo_hoje", 0) or 0)
    plan = str(client_status.get("plan", "basico") or "basico")
    formato_maximo = int(client_status.get("formato_maximo", 15) or 15)
    quantities = _available_quantities(saldo_hoje=saldo_hoje)
    description = (
        f"Plano {plan} — até {formato_maximo}D\n"
        f"Saldo hoje: {saldo_hoje} jogos\n\n"
        "Quantos jogos quer gerar?"
    )
    button_options: list[tuple[str, str]] = [(f"{quantidade} jogos", f"qty:{quantidade}") for quantidade in quantities]
    if len(button_options) > 3:
        button_options = button_options[:2] + [("Outras quantidades", "qty:more")]
    rows = [
        {"title": label, "description": "Selecionar", "rowId": selection_id}
        for label, selection_id in button_options
    ] or [{"title": "Limite diário atingido", "description": "Volte amanhã", "rowId": "noop:limit"}]
    bundle = _menu_bundle(
        description=description,
        button_options=button_options,
        list_rows=rows,
        list_button_text="Escolher quantidade",
    )
    bundle["text_fallback"] = _build_quantity_text_intro(
        button_options=button_options,
        client_status=client_status,
    )
    return bundle


def build_quantity_more_menu_bundle(*, client_status: dict[str, Any]) -> dict[str, Any]:
    saldo_hoje = int(client_status.get("saldo_hoje", 0) or 0)
    quantities = _available_quantities(saldo_hoje=saldo_hoje)[2:]
    description = "Escolha outra quantidade de jogos:"
    button_options = [(f"{quantidade} jogos", f"qty:{quantidade}") for quantidade in quantities]
    rows = [{"title": label, "description": "Selecionar", "rowId": selection_id} for label, selection_id in button_options]
    return _menu_bundle(
        description=description,
        button_options=button_options,
        list_rows=rows,
        list_button_text="Escolher",
    )


def build_confirm_menu_bundle(*, quantidade: int, client_status: dict[str, Any]) -> dict[str, Any]:
    formato_maximo = int(client_status.get("formato_maximo", 15) or 15)
    plan = str(client_status.get("plan", "basico") or "basico")
    description = (
        f"✅ *{quantidade} jogos* selecionados.\n"
        f"Plano {plan} — até {formato_maximo}D\n\n"
        "Toque em *Gerar Jogos* para criar seus cartões."
    )
    button_options: list[tuple[str, str]] = [("Gerar Jogos", f"gen:{quantidade}:15")]
    if formato_maximo >= 17:
        button_options.append((f"Gerar {quantidade} jogos 17D", f"gen:{quantidade}:17"))
    if formato_maximo >= 18:
        button_options.append((f"Gerar {quantidade} jogos 18D", f"gen:{quantidade}:18"))
    if formato_maximo > 18 or (formato_maximo == 16 and len(button_options) < 3):
        if formato_maximo == 16:
            button_options = [("Gerar Jogos", f"gen:{quantidade}:15"), (f"Gerar {quantidade} jogos 16D", f"gen:{quantidade}:16")]
        elif formato_maximo > 18:
            button_options = button_options[:2] + [("Mais formatos", f"fmtmore:{quantidade}")]
    button_options = button_options[:3]
    rows = [{"title": label, "description": "Confirmar geração", "rowId": selection_id} for label, selection_id in button_options]
    return _menu_bundle(
        description=description,
        button_options=button_options,
        list_rows=rows,
        list_button_text="Gerar Jogos",
        footer=f"Plano {plan}",
    )


def build_format_more_menu_bundle(*, quantidade: int, client_status: dict[str, Any]) -> dict[str, Any]:
    formato_maximo = int(client_status.get("formato_maximo", 15) or 15)
    formatos = [formato for formato in range(16, formato_maximo + 1) if formato not in {16, 17, 18}]
    if not formatos:
        formatos = list(range(17, formato_maximo + 1))
    description = f"Escolha o formato para {quantidade} jogos:"
    button_options = [(f"Gerar Jogos {formato}D", f"gen:{quantidade}:{formato}") for formato in formatos[:3]]
    rows = [{"title": label, "description": "Gerar", "rowId": selection_id} for label, selection_id in button_options]
    return _menu_bundle(
        description=description,
        button_options=button_options,
        list_rows=rows,
        list_button_text="Gerar Jogos",
    )


def _build_quantity_text_intro(
    *,
    button_options: list[tuple[str, str]],
    client_status: dict[str, Any],
) -> str:
    plan = str(client_status.get("plan", "basico") or "basico")
    formato_maximo = int(client_status.get("formato_maximo", 15) or 15)
    saldo_hoje = int(client_status.get("saldo_hoje", 0) or 0)
    lines = [
        "👋 *Olá! Bem-vindo à LotoIA*",
        "",
        f"Plano *{plan}* — até *{formato_maximo}D*",
        f"Saldo hoje: *{saldo_hoje} jogos*",
        "",
        "*Quantos jogos quer gerar?*",
        "",
    ]
    for index, (label, _) in enumerate(button_options[:3], start=1):
        lines.append(f"*{index}* — {label}")
    lines.extend(
        [
            "",
            "Toque nos botões abaixo ou responda só o número (1, 2 ou 3).",
        ]
    )
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
        return {"quantidade": int(value), "formato": DEFAULT_GAME_FORMAT}
    return None


def _selection_id_from_text(text: str, *, phone: str) -> str:
    normalized = " ".join(str(text or "").strip().split()).lower()
    normalized = normalized.strip("!?.")
    if not normalized:
        return ""
    if normalized.isdigit():
        options = _PENDING_QUICK_OPTIONS.get(str(phone), [])
        index = int(normalized) - 1
        if 0 <= index < len(options):
            return str(options[index][1])
    if normalized in {"gerar jogos", "gerar"}:
        pending = _PENDING_QUANTITY.get(str(phone))
        if pending:
            return f"gen:{pending}:15"
    for quantidade in MENU_QUANTITIES:
        if normalized in {f"{quantidade} jogos", f"{quantidade} jogo"}:
            return f"qty:{quantidade}"
    pending = _PENDING_QUANTITY.get(str(phone))
    if pending and normalized.endswith("d") and normalized[:-1].isdigit():
        return f"gen:{pending}:{int(normalized[:-1])}"
    return ""


def build_format_menu_bundle(*, quantidade: int, client_status: dict[str, Any]) -> dict[str, Any]:
    return build_confirm_menu_bundle(quantidade=quantidade, client_status=client_status)


def build_quantity_list_payload(*, client_status: dict[str, Any]) -> dict[str, Any]:
    return dict(build_quantity_menu_bundle(client_status=client_status)["list_payload"])


def build_format_list_payload(*, quantidade: int, client_status: dict[str, Any]) -> dict[str, Any]:
    return dict(build_confirm_menu_bundle(quantidade=quantidade, client_status=client_status)["list_payload"])
