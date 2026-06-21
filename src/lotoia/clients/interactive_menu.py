from __future__ import annotations

import re
from typing import Any

from lotoia.clients.constants import DEFAULT_PLAN_ID, LEGACY_PLANS, OFFICIAL_LANDING_HOST, PLANS, VALID_QUANTITIES
from lotoia.clients.message_parser import parse_whatsapp_message

MENU_QUANTITIES = (5, 10, 20, 30)
FIXED_MENU_QUANTITIES = (5, 10, 20)

HELP_MESSAGE = "Quantos jogos você quer gerar hoje?"

UNREGISTERED_MESSAGE = (
    "Número não cadastrado.\n"
    f"Acesse {OFFICIAL_LANDING_HOST} para assinar."
)

_PENDING_QUANTITY: dict[str, int] = {}
_PENDING_QUICK_OPTIONS: dict[str, list[tuple[str, str]]] = {}
_AWAITING_CUSTOM_QUANTITY: dict[str, int] = {}

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

_PLAN_LABELS = {
    DEFAULT_PLAN_ID: "Completo",
    **{plan_id: plan_id.capitalize() for plan_id in LEGACY_PLANS},
}


def _available_quantities(*, saldo_hoje: int) -> list[int]:
    return [
        quantidade
        for quantidade in MENU_QUANTITIES
        if quantidade in VALID_QUANTITIES and quantidade <= saldo_hoje
    ]


def _plan_label(plan: str) -> str:
    key = str(plan or DEFAULT_PLAN_ID).strip().lower()
    return _PLAN_LABELS.get(key, key.capitalize())


def _client_formato_maximo(client_status: dict[str, Any] | None) -> int:
    if not client_status:
        return 15
    if client_status.get("formato_maximo_efetivo") is not None:
        return int(client_status["formato_maximo_efetivo"])
    return int(client_status.get("formato_maximo", 15) or 15)


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
    return build_welcome_text_from_options(button_options=button_options)


def plan_formats_label(plan_key: str) -> str:
    key = str(plan_key or DEFAULT_PLAN_ID).strip().lower()
    if key in PLANS:
        return str(PLANS[key].get("formats") or "")
    legacy = LEGACY_PLANS.get(key, {})
    return str(legacy.get("formats") or f"até {legacy.get('formato_max', 15)}D")


def allowed_formats_for_client(client_status: dict[str, Any] | None) -> list[int]:
    if not client_status:
        return [15]
    formato_maximo = _client_formato_maximo(client_status)
    if formato_maximo <= 15:
        return [15]
    return [15, formato_maximo]


def is_format_allowed_for_client(formato: int, *, formato_maximo: int) -> bool:
    if int(formato_maximo) <= 15:
        return int(formato) == 15
    return int(formato) in {15, int(formato_maximo)}


def distribute_quantidade_across_formats(quantidade: int, formats: list[int]) -> list[tuple[int, int]]:
    if not formats:
        return [(15, quantidade)]
    if len(formats) == 1:
        return [(int(formats[0]), quantidade)]
    first_format, second_format = int(formats[0]), int(formats[1])
    first_count = (quantidade + 1) // 2
    second_count = quantidade // 2
    targets: list[tuple[int, int]] = []
    if first_count > 0:
        targets.append((first_format, first_count))
    if second_count > 0:
        targets.append((second_format, second_count))
    return targets


def plan_generation_targets(
    parsed: dict[str, Any],
    *,
    client_status: dict[str, Any] | None,
) -> list[tuple[int, int]]:
    quantidade = int(parsed["quantidade"])
    if parsed.get("formato") is not None:
        return [(int(parsed["formato"]), quantidade)]
    return distribute_quantidade_across_formats(
        quantidade,
        allowed_formats_for_client(client_status),
    )


def _welcome_plan_title(client_status: dict[str, Any]) -> str:
    return "LotoIA Completo"


def _build_generation_examples(*, formato_maximo: int, trial_days: int) -> str:
    lines = [
        "Como pedir:",
        "• 5, 10 ou 20",
        "• 1015D ou 10x15D → 10 jogos 15D",
    ]
    if trial_days > 0 or formato_maximo <= 15:
        lines.append("• 515D ou 5x15D → 5 jogos 15D")
    else:
        lines.extend(
            [
                f"• 520D ou 5x{formato_maximo}D → 5 jogos {formato_maximo}D",
                f"• Só a quantidade → metade 15D + metade {formato_maximo}D",
            ]
        )
    return "\n".join(lines)


def _build_phase_summary(*, formato_maximo: int, formats: str, trial_days: int) -> str:
    if trial_days > 0:
        return (
            f"📌 Fase inicial — {trial_days} dia(s) restante(s)\n"
            "Formatos: 15D (30 jogos/dia)\n"
            "Depois libera 15D + 20D por 12 meses."
        )
    if formato_maximo > 15:
        return f"Formatos: {formats}\nAté 30 jogos por dia."
    return f"Formatos: {formats}\nAté 30 jogos por dia."


def build_welcome_text(*, client_status: dict[str, Any]) -> str:
    formato_maximo = _client_formato_maximo(client_status)
    formats = str(client_status.get("formatos_disponiveis") or plan_formats_label(DEFAULT_PLAN_ID))
    saldo_hoje = int(client_status.get("saldo_hoje", 0) or 0)
    trial_days = int(client_status.get("dias_trial_restantes", 0) or 0)
    title = _welcome_plan_title(client_status)
    phase_summary = _build_phase_summary(
        formato_maximo=formato_maximo,
        formats=formats,
        trial_days=trial_days,
    )
    examples = _build_generation_examples(formato_maximo=formato_maximo, trial_days=trial_days)
    return (
        f"👋 Olá! *{title}*\n\n"
        f"Saldo hoje: {saldo_hoje} jogos\n\n"
        f"{phase_summary}\n\n"
        f"{examples}\n\n"
        "Digite sua quantidade 👇"
    )


def build_welcome_text_from_options(*, button_options: list[tuple[str, str]]) -> str:
    labels = " · ".join(label for label, _ in button_options[:3])
    return (
        "👋 *Olá! LotoIA Completo*\n\n"
        "Até 30 jogos por dia no WhatsApp.\n\n"
        "*Quantos jogos quer gerar?*\n\n"
        f"Opções: {labels}\n\n"
        "Toque nos botões abaixo ou digite, ex.: 1015D"
    )


def _menu_bundle(
    *,
    description: str,
    button_options: list[tuple[str, str]],
    list_rows: list[dict[str, str]],
    list_button_text: str,
    footer: str = "LotoIA",
    text_fallback: str = "",
    prefer_list: bool = False,
) -> dict[str, Any]:
    return {
        "prefer_list": prefer_list,
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
            "sections": [{"title": "Quantidade de jogos", "rows": list_rows}],
        },
        "text_fallback": text_fallback or description,
    }


def build_quantity_menu_bundle(*, client_status: dict[str, Any]) -> dict[str, Any]:
    saldo_hoje = int(client_status.get("saldo_hoje", 0) or 0)
    if saldo_hoje <= 0:
        return {
            "text_only": True,
            "text_fallback": (
                "👋 Olá! *LotoIA Completo*\n\n"
                "Você já usou os 30 jogos de hoje.\n"
                "Volte amanhã às 00h para gerar novos cartões."
            ),
        }

    return {
        "text_only": True,
        "text_fallback": build_welcome_text(client_status=client_status),
    }


def build_quantity_more_menu_bundle(*, client_status: dict[str, Any]) -> dict[str, Any]:
    saldo_hoje = int(client_status.get("saldo_hoje", 0) or 0)
    quantities = _available_quantities(saldo_hoje=saldo_hoje)[2:]
    description = "Escolha outra quantidade de jogos:"
    button_options = [(f"{quantidade:02d} Jogos", f"qty:{quantidade}") for quantidade in quantities]
    rows = [{"title": label, "description": "Selecionar", "rowId": selection_id} for label, selection_id in button_options]
    return _menu_bundle(
        description=description,
        button_options=button_options,
        list_rows=rows,
        list_button_text="Escolher",
        prefer_list=True,
    )


def build_confirm_menu_bundle(*, quantidade: int, client_status: dict[str, Any]) -> dict[str, Any]:
    formato_maximo = _client_formato_maximo(client_status)
    description = (
        f"✅ *{quantidade} jogos* selecionados.\n"
        f"LotoIA Completo — até {formato_maximo}D\n\n"
        "Toque em *Gerar Jogos* para criar seus cartões."
    )
    button_options: list[tuple[str, str]] = [("Gerar Jogos", f"gen:{quantidade}:15")]
    if formato_maximo == 20:
        button_options.append((f"Gerar {quantidade} jogos 20D", f"gen:{quantidade}:20"))
    elif formato_maximo > 15:
        button_options.append((f"Gerar {quantidade} jogos {formato_maximo}D", f"gen:{quantidade}:{formato_maximo}"))
    if formato_maximo > 20:
        button_options = button_options[:2] + [("Mais formatos", f"fmtmore:{quantidade}")]
    button_options = button_options[:3]
    rows = [
        {"title": label, "description": "Confirmar geração", "rowId": selection_id}
        for label, selection_id in button_options
    ]
    return _menu_bundle(
        description=description,
        button_options=button_options,
        list_rows=rows,
        list_button_text="Gerar Jogos",
        footer="LotoIA Completo",
    )


def build_format_more_menu_bundle(*, quantidade: int, client_status: dict[str, Any]) -> dict[str, Any]:
    formato_maximo = _client_formato_maximo(client_status)
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


def build_custom_quantity_prompt(*, saldo_hoje: int) -> str:
    return (
        "✏️ *Outra quantidade*\n\n"
        f"Digite quantos jogos quer gerar (1 a {saldo_hoje}):\n"
        "Ex.: *3* ou *3 jogos*"
    )


def set_awaiting_custom_quantity(phone: str, saldo_hoje: int) -> None:
    _AWAITING_CUSTOM_QUANTITY[str(phone)] = int(saldo_hoje)


def is_awaiting_custom_quantity(phone: str) -> bool:
    return str(phone) in _AWAITING_CUSTOM_QUANTITY


def get_awaiting_custom_quantity_limit(phone: str) -> int | None:
    return _AWAITING_CUSTOM_QUANTITY.get(str(phone))


def clear_awaiting_custom_quantity(phone: str) -> None:
    _AWAITING_CUSTOM_QUANTITY.pop(str(phone), None)


import unicodedata

_RESULTADO_KEYWORDS = {
    "resultado",
    "esultado",
    "resutado",
    "resultdo",
    "resultao",
}


def is_resultado_request(text: str) -> bool:
    normalized = unicodedata.normalize("NFKC", str(text or "").strip().lower())
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Cf")
    normalized = " ".join(normalized.split()).strip("!?.")
    if not normalized:
        return False
    if normalized in _RESULTADO_KEYWORDS:
        return True
    return normalized.startswith("resultado ")


def parse_custom_quantity(text: str) -> int | None:
    normalized = " ".join(str(text or "").strip().split()).lower()
    if not normalized:
        return None
    match = re.search(r"\d{1,2}", normalized)
    if not match:
        return None
    return int(match.group())


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
        if value == "custom":
            return {"next_menu": "await_custom_quantity"}
        return {"quantidade": int(value), "formato": None}
    return None


def _selection_id_from_text(text: str, *, phone: str) -> str:
    parsed_message = parse_whatsapp_message(text)
    if parsed_message and parsed_message.get("formato") is not None:
        return f"gen:{int(parsed_message['quantidade'])}:{int(parsed_message['formato'])}"
    if parsed_message and parsed_message.get("quantidade") is not None:
        return f"qty:{int(parsed_message['quantidade'])}"

    normalized = " ".join(str(text or "").strip().split()).lower()
    normalized = normalized.strip("!?.")
    if not normalized:
        return ""
    if normalized in {"outra quantidade", "outra"}:
        return "qty:custom"
    if normalized.isdigit():
        quantidade = int(normalized)
        if quantidade in FIXED_MENU_QUANTITIES:
            return f"qty:{quantidade}"
        custom_limit = get_awaiting_custom_quantity_limit(phone)
        if custom_limit is not None:
            parsed = parse_custom_quantity(normalized)
            if parsed is not None:
                return f"qty:{parsed}"
    if normalized in {"gerar jogos", "gerar"}:
        pending = _PENDING_QUANTITY.get(str(phone))
        if pending:
            return f"gen:{pending}:15"
    for quantidade in MENU_QUANTITIES:
        if normalized in {f"{quantidade} jogos", f"{quantidade} jogo", f"{quantidade:02d} jogos"}:
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
