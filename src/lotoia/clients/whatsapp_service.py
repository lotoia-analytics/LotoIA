from __future__ import annotations

import logging
import random
import re
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from lotoia.clients.client_guard import ValidationResult, validate_request
from lotoia.clients.phone_utils import canonical_brazil_phone, phone_lookup_candidates
from lotoia.clients.evolution_client import (
    WHATSAPP_GAMES_FOOTER_LINES,
    EvolutionApiClient,
    GENERATION_ERROR_MESSAGE,
)
from lotoia.clients.game_expansion import expand_generation_games_for_format
from lotoia.clients.interactive_menu import (
    HELP_MESSAGE,
    UNREGISTERED_MESSAGE,
    build_custom_quantity_prompt,
    build_format_more_menu_bundle,
    build_quantity_menu_bundle,
    build_quantity_more_menu_bundle,
    clear_awaiting_custom_quantity,
    get_awaiting_custom_quantity_limit,
    is_awaiting_custom_quantity,
    is_greeting,
    is_resultado_request,
    parse_custom_quantity,
    parse_menu_selection,
    plan_generation_targets,
    set_awaiting_custom_quantity,
)
from lotoia.clients.message_parser import parse_whatsapp_message
from lotoia.clients.conference_utils import resolve_next_target_contest
from lotoia.clients.result_conference_service import ResultConferenceService, parse_contest_number
from lotoia.clients.whatsapp_state_repository import WhatsAppStateRepository
from lotoia.clients.repository import ClientRepository
from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.generator.engine import generate_ranked_games
from lotoia.public.persistence import GenerationEventRepository, LeadRepository
from lotoia.public.services import normalize_whatsapp

logger = logging.getLogger(__name__)

_PROCESSED_MESSAGE_IDS: dict[str, datetime] = {}
_IDEMPOTENCY_TTL = timedelta(hours=6)


def _cleanup_processed_message_ids() -> None:
    cutoff = datetime.now(UTC) - _IDEMPOTENCY_TTL
    expired = [message_id for message_id, seen_at in _PROCESSED_MESSAGE_IDS.items() if seen_at < cutoff]
    for message_id in expired:
        _PROCESSED_MESSAGE_IDS.pop(message_id, None)


def _remember_message_id(message_id: str, *, phone: str = "", text: str = "") -> bool:
    if not message_id:
        return False
    _cleanup_processed_message_ids()
    dedupe_key = f"{phone}:{message_id}" if phone else message_id
    if dedupe_key in _PROCESSED_MESSAGE_IDS:
        return True
    _PROCESSED_MESSAGE_IDS[dedupe_key] = datetime.now(UTC)
    return False


def _resolve_evolution_sender_jid(
    key: dict[str, Any],
    data: dict[str, Any],
    payload: dict[str, Any],
) -> str:
    """Prefer real @s.whatsapp.net JID over WhatsApp @lid identifiers."""
    remote_jid = str(key.get("remoteJid") or "")
    remote_jid_alt = str(key.get("remoteJidAlt") or "")
    if "@lid" in remote_jid and remote_jid_alt:
        return remote_jid_alt
    if "@s.whatsapp.net" in remote_jid:
        return remote_jid
    if remote_jid_alt:
        return remote_jid_alt
    for candidate in (data.get("remoteJid"), payload.get("sender"), data.get("sender")):
        if candidate:
            candidate_jid = str(candidate)
            if "@lid" not in candidate_jid or remote_jid_alt:
                return remote_jid_alt or candidate_jid
    return remote_jid


def _normalize_evolution_data(payload: dict[str, Any]) -> dict[str, Any]:
    raw_data = payload.get("data")
    if isinstance(raw_data, list) and raw_data:
        first = raw_data[0]
        return dict(first) if isinstance(first, dict) else {}
    if isinstance(raw_data, dict):
        return dict(raw_data)
    return dict(payload)


def _unwrap_message_dict(message: dict[str, Any]) -> dict[str, Any]:
    current = dict(message or {})
    for _ in range(4):
        nested = current.get("message")
        if isinstance(nested, dict):
            current = dict(nested)
            continue
        for wrapper in ("ephemeralMessage", "viewOnceMessage", "editedMessage", "documentWithCaptionMessage"):
            wrapped = current.get(wrapper)
            if isinstance(wrapped, dict) and isinstance(wrapped.get("message"), dict):
                current = dict(wrapped["message"])
                break
        else:
            break
    return current


def _extract_message_text(message: dict[str, Any], data: dict[str, Any], payload: dict[str, Any]) -> str:
    unwrapped = _unwrap_message_dict(message)
    candidates = [
        unwrapped.get("conversation"),
        dict(unwrapped.get("extendedTextMessage") or {}).get("text"),
        dict(unwrapped.get("imageMessage") or {}).get("caption"),
        dict(unwrapped.get("videoMessage") or {}).get("caption"),
        dict(unwrapped.get("listResponseMessage") or {}).get("title"),
        dict(unwrapped.get("buttonsResponseMessage") or {}).get("selectedDisplayText"),
        dict(unwrapped.get("templateButtonReplyMessage") or {}).get("selectedDisplayText"),
        data.get("text"),
        data.get("messageText"),
        data.get("content"),
        data.get("body"),
        payload.get("text"),
        payload.get("content"),
    ]
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text:
            return text
    return ""


def extract_evolution_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = _normalize_evolution_data(payload)
    key = dict(data.get("key") or {})
    from_me = bool(key.get("fromMe") or data.get("fromMe") or payload.get("fromMe"))
    remote_jid = _resolve_evolution_sender_jid(key, data, payload)
    phone = re.sub(r"\D", "", remote_jid.split("@", maxsplit=1)[0])
    if not phone:
        phone = re.sub(r"\D", "", str(payload.get("sender") or data.get("sender") or data.get("number") or ""))
    message = dict(data.get("message") or {})
    is_poll_update = bool(message.get("pollUpdateMessage"))
    list_reply = dict(message.get("listResponseMessage") or {})
    button_reply = dict(message.get("buttonsResponseMessage") or {})
    template_reply = dict(message.get("templateButtonReplyMessage") or {})
    single_select = dict(list_reply.get("singleSelectReply") or {})
    selection_id = str(
        single_select.get("selectedRowId")
        or button_reply.get("selectedButtonId")
        or template_reply.get("selectedId")
        or ""
    )
    text = _extract_message_text(message, data, payload)
    message_id = str(
        key.get("id")
        or data.get("id")
        or data.get("messageId")
        or payload.get("message_id")
        or ""
    )
    return {
        "phone": phone,
        "text": str(text).strip(),
        "selection_id": selection_id,
        "message_id": message_id,
        "from_me": from_me,
        "is_poll_update": is_poll_update,
    }


def format_games_whatsapp_message(
    *,
    quantidade: int,
    games: list[dict[str, Any]],
    targets: list[tuple[int, int]],
) -> str:
    if len(targets) > 1:
        formats_label = " e ".join(f"{formato}D" for formato, _ in targets)
        lines = [f"🎯 *Seus jogos LotoIA — {formats_label}*", ""]
    else:
        formato = int(targets[0][0])
        lines = [f"🎯 *Seus jogos LotoIA — {formato}D*", ""]

    for index, game in enumerate(games, start=1):
        numbers = sorted(
            int(number)
            for number in game.get("cartao_validado_lei15a", [])
            or game.get("numbers", [])
            or game.get("final_card_numbers", [])
        )
        formatted_numbers = " ".join(f"{number:02d}" for number in numbers)
        formato_label = int(game.get("formato_cartao") or targets[0][0])
        if len(targets) > 1:
            lines.append(f"Jogo {index:02d} ({formato_label}D): {formatted_numbers}")
        else:
            lines.append(f"Jogo {index:02d}: {formatted_numbers}")
    lines.extend(["", *WHATSAPP_GAMES_FOOTER_LINES])
    return "\n".join(lines)


def generate_whatsapp_games(
    *,
    targets: list[tuple[int, int]],
    phone: str,
    client_name: str = "Cliente",
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    quantidade = sum(qty for _, qty in targets)
    seed = random.randint(1, 999999)
    started_at = time.time()
    base_games = generate_ranked_games(total_games=int(quantidade), seed=seed, ml_enabled=False)
    games: list[dict[str, Any]] = []
    offset = 0
    for formato, qty in targets:
        chunk = list(base_games[offset : offset + int(qty)])
        offset += int(qty)
        expanded = expand_generation_games_for_format(chunk, int(formato))
        for game in expanded:
            tagged = dict(game)
            tagged["formato_cartao"] = int(formato)
            games.append(tagged)
    execution_time_ms = (time.time() - started_at) * 1000
    ranking_score = float(
        sum(float(game.get("final_score", {}).get("final_score", 0) or 0) for game in games) / max(len(games), 1)
        if games
        else 0.0
    )
    normalized_phone = normalize_whatsapp(phone)
    lead_repo = LeadRepository(db_path)
    lead = lead_repo.find_by_first_name_and_whatsapp(client_name, normalized_phone)
    if lead is None:
        lead = lead_repo.insert(
            first_name=client_name,
            whatsapp=normalized_phone,
            source="whatsapp_bot",
            ip_hash="",
            user_agent="whatsapp_bot",
        )
    generation_repo = GenerationEventRepository(db_path)
    generation_event = generation_repo.insert(
        lead_id=int(lead["id"]),
        generated_games=games,
        ml_enabled=False,
        seed=seed,
        strategy="whatsapp_statistical_v1",
        ranking_score=ranking_score,
        execution_time_ms=execution_time_ms,
        origin="whatsapp_bot",
        generation_mode="whatsapp_hybrid_statistical_v1",
        context={
            "targets": [{"formato": int(formato), "quantidade": int(qty)} for formato, qty in targets],
            "quantidade": int(quantidade),
            "source": "whatsapp_bot",
        },
        first_name=client_name,
        whatsapp=normalized_phone,
    )
    return games, generation_event


def _resolve_reply_phone(repository: ClientRepository, phone: str) -> str:
    client = repository.get_by_phone(phone)
    if client:
        return str(client.get("phone") or phone)
    try:
        return canonical_brazil_phone(phone)
    except ValueError:
        return re.sub(r"\D", "", str(phone or ""))


def process_whatsapp_webhook(
    payload: dict[str, Any],
    *,
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    extracted = extract_evolution_payload(payload)
    phone = str(extracted.get("phone") or "")
    text = str(extracted.get("text") or "")
    message_id = str(extracted.get("message_id") or "")

    if extracted.get("from_me"):
        return {
            "status": "ignored",
            "reason": "from_me",
            "phone": phone,
        }

    if extracted.get("is_poll_update"):
        return {
            "status": "ignored",
            "reason": "poll_update",
            "phone": phone,
        }

    if message_id and _remember_message_id(message_id, phone=phone, text=text):
        return {
            "status": "ignored",
            "reason": "duplicate_message",
            "message_id": message_id,
            "phone": phone,
        }

    if not phone:
        return {"status": "error", "error_code": "INVALID_PAYLOAD", "message": "Telefone não identificado no payload."}

    repository = ClientRepository(db_path)
    reply_phone = _resolve_reply_phone(repository, phone)
    client_status = repository.get_client_status(phone)
    selection_id = str(extracted.get("selection_id") or "")
    result_conference = ResultConferenceService(db_path)
    state_repo = WhatsAppStateRepository(db_path)
    contest_number = parse_contest_number(text)
    awaiting_concurso = state_repo.is_awaiting_concurso(reply_phone)

    if awaiting_concurso or (contest_number is not None and contest_number >= 1000):
        if contest_number is None:
            if is_resultado_request(text):
                return {
                    "status": "prompt",
                    "phone": reply_phone,
                    "message": result_conference.get_prompt(),
                }
            return {
                "status": "prompt",
                "phone": reply_phone,
                "message": (
                    "Não entendi o número do concurso.\n\n"
                    + result_conference.get_prompt()
                ),
            }
        try:
            message = result_conference.build_message_for_phone(contest_number=contest_number, phone=phone)
        except Exception as exc:  # noqa: BLE001 - user-facing WhatsApp boundary
            logger.exception(
                "WHATSAPP_RESULTADO_ERROR phone=%s contest=%s error=%s",
                reply_phone,
                contest_number,
                exc,
            )
            message = (
                f"⚠️ Não foi possível consultar o concurso {contest_number} agora.\n\n"
                "Tente novamente em instantes ou digite RESULTADO."
            )
        state_repo.clear_awaiting_concurso(reply_phone)
        logger.info(
            "WHATSAPP_RESULTADO_CONFERENCIA phone=%s contest=%s chars=%s",
            reply_phone,
            contest_number,
            len(message),
        )
        return {"status": "ok", "phone": reply_phone, "message": message}

    if is_resultado_request(text):
        try:
            state_repo.set_awaiting_concurso(reply_phone)
        except Exception as exc:  # noqa: BLE001 - prompt must not fail on state persistence
            logger.exception("WHATSAPP_STATE_SAVE_ERROR phone=%s error=%s", reply_phone, exc)
        logger.info("WHATSAPP_RESULTADO_PROMPT phone=%s text=%r", reply_phone, text)
        return {
            "status": "prompt",
            "phone": reply_phone,
            "message": result_conference.get_prompt(),
        }

    menu_parsed = parse_menu_selection(selection_id, text=text, phone=phone)
    parsed = parse_whatsapp_message(text)

    if is_awaiting_custom_quantity(phone):
        saldo_hoje = int(get_awaiting_custom_quantity_limit(phone) or 0)
        quantidade = parse_custom_quantity(text)
        if quantidade is None:
            return {
                "status": "error",
                "error_code": "INVALID_CUSTOM_QUANTITY",
                "phone": phone,
                "message": build_custom_quantity_prompt(saldo_hoje=saldo_hoje),
            }
        clear_awaiting_custom_quantity(phone)
        parsed = {"quantidade": quantidade, "formato": None}

    if menu_parsed and menu_parsed.get("next_menu") == "await_custom_quantity":
        if not client_status:
            return {
                "status": "error",
                "error_code": "CLIENT_NOT_FOUND",
                "phone": phone,
                "message": UNREGISTERED_MESSAGE,
            }
        saldo_hoje = int(client_status.get("saldo_hoje", 0) or 0)
        set_awaiting_custom_quantity(phone, saldo_hoje)
        return {
            "status": "prompt",
            "phone": phone,
            "message": build_custom_quantity_prompt(saldo_hoje=saldo_hoje),
        }

    if menu_parsed and menu_parsed.get("next_menu") == "quantity_more":
        if not client_status:
            return {
                "status": "error",
                "error_code": "CLIENT_NOT_FOUND",
                "phone": phone,
                "message": UNREGISTERED_MESSAGE,
            }
        return {
            "status": "menu",
            "phone": phone,
            "menu_bundle": build_quantity_more_menu_bundle(client_status=client_status),
            "message": HELP_MESSAGE,
        }

    if menu_parsed and menu_parsed.get("next_menu") == "format_more":
        if not client_status:
            return {
                "status": "error",
                "error_code": "CLIENT_NOT_FOUND",
                "phone": phone,
                "message": UNREGISTERED_MESSAGE,
            }
        quantidade = int(menu_parsed["quantidade"])
        return {
            "status": "menu_format",
            "phone": phone,
            "quantidade": quantidade,
            "menu_bundle": build_format_more_menu_bundle(quantidade=quantidade, client_status=client_status),
            "message": HELP_MESSAGE,
        }

    if menu_parsed and menu_parsed.get("quantidade") is not None:
        parsed = menu_parsed
    elif menu_parsed and menu_parsed.get("formato") is not None:
        parsed = menu_parsed

    if not parsed:
        if client_status:
            logger.info("MENU_REQUEST phone=%s text=%r greeting=%s", phone, text, is_greeting(text))
            return {
                "status": "menu",
                "phone": phone,
                "menu_bundle": build_quantity_menu_bundle(client_status=client_status),
                "message": HELP_MESSAGE,
            }
        return {
            "status": "error",
            "error_code": "CLIENT_NOT_FOUND",
            "phone": phone,
            "message": UNREGISTERED_MESSAGE,
        }

    quantidade = int(parsed["quantidade"])
    targets = plan_generation_targets(parsed, client_status=client_status)
    validation_formato = int(targets[0][0]) if len(targets) == 1 else int(parsed.get("formato") or 15)
    validation = validate_request(phone, validation_formato, quantidade, db_path=db_path)
    if not validation.ok:
        if validation.error_code == "CLIENT_NOT_FOUND":
            logger.warning("CLIENT_NOT_FOUND extracted_phone=%s message=%r", phone, text)
        return {
            "status": "error",
            "error_code": validation.error_code,
            "phone": phone,
            "message": validation.message,
        }

    try:
        return _execute_valid_generation(
            phone=phone,
            validation=validation,
            targets=targets,
            db_path=db_path,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced to WhatsApp delivery layer
        logger.exception("GENERATION_ERROR for phone=%s: %s", phone, exc)
        return {
            "status": "error",
            "error_code": "GENERATION_ERROR",
            "phone": phone,
            "message": GENERATION_ERROR_MESSAGE,
        }


def _execute_valid_generation(
    *,
    phone: str,
    validation: ValidationResult,
    targets: list[tuple[int, int]],
    db_path: Path,
) -> dict[str, Any]:
    client = dict(validation.client or {})
    quantidade = int(validation.quantidade or 0)
    games, generation_event = generate_whatsapp_games(
        targets=targets,
        phone=phone,
        client_name=str(client.get("name") or "Cliente"),
        db_path=db_path,
    )
    log_formato = max(formato for formato, _ in targets)
    repository = ClientRepository(db_path)
    concurso_alvo = resolve_next_target_contest(db_path)
    client_generation = repository.log_client_generation(
        client_id=int(client["id"]),
        phone=phone,
        formato=log_formato,
        quantidade=quantidade,
        jogos=games,
        generation_event_id=int(generation_event.get("id") or 0) or None,
        concurso_alvo=concurso_alvo,
    )
    repository.increment_daily_usage(int(client["id"]), quantidade=quantidade)
    response_message = format_games_whatsapp_message(
        quantidade=quantidade,
        games=games,
        targets=targets,
    )
    return {
        "status": "ok",
        "phone": normalize_whatsapp(phone),
        "message": response_message,
        "games": games,
        "quantidade": quantidade,
        "formato": log_formato if len(targets) == 1 else None,
        "formatos": [formato for formato, _ in targets],
        "targets": [{"formato": formato, "quantidade": qty} for formato, qty in targets],
        "generation_event_id": generation_event.get("id"),
        "client_generation_id": client_generation.get("id"),
        "trace_id": f"wa-{uuid4().hex[:12]}",
    }


def activate_client(
    *,
    phone: str,
    plan: str,
    valor_pago: float,
    name: str = "",
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    repository = ClientRepository(db_path)
    client = repository.activate_client(phone=phone, plan=plan, valor_pago=valor_pago, name=name)
    return {
        "status": "ok",
        "client": {
            "id": client.get("id"),
            "phone": client.get("phone"),
            "name": client.get("name"),
            "plan": client.get("plan"),
            "formato_maximo": client.get("formato_maximo"),
            "data_expiracao": client.get("data_expiracao").isoformat()
            if isinstance(client.get("data_expiracao"), datetime)
            else str(client.get("data_expiracao") or ""),
            "status": client.get("status"),
        },
    }


def get_client_status(phone: str, *, db_path: Path = DEFAULT_DATABASE_PATH) -> dict[str, Any] | None:
    repository = ClientRepository(db_path)
    return repository.get_client_status(phone)


def _send_text_with_phone_fallback(client: EvolutionApiClient, phone: str, message: str) -> bool:
    candidates = phone_lookup_candidates(phone) if phone else []
    ordered = list(dict.fromkeys([*candidates, phone]))
    for candidate in ordered:
        if candidate and client.send_text(str(candidate), message):
            return True
    return False


def deliver_whatsapp_webhook(
    payload: dict[str, Any],
    *,
    db_path: Path = DEFAULT_DATABASE_PATH,
    evolution_client: EvolutionApiClient | None = None,
) -> dict[str, Any]:
    """Process webhook payload and deliver the response via Evolution API."""
    result = dict(process_whatsapp_webhook(payload, db_path=db_path))
    status = str(result.get("status", "") or "")
    phone = str(result.get("phone") or "")
    client = evolution_client or EvolutionApiClient()
    delivered = False
    delivery_error = ""

    if status == "ignored":
        result["delivered"] = False
        result["delivery_skipped"] = True
        return result

    try:
        response_message = str(result.get("message") or "").strip()
        if status == "ok" and phone and result.get("games"):
            if response_message:
                delivered = _send_text_with_phone_fallback(client, phone, response_message)
            else:
                delivered = client.send_games(
                    phone,
                    list(result.get("games") or []),
                    int(result.get("formato") or 15),
                )
        elif status == "ok" and phone and response_message:
            delivered = _send_text_with_phone_fallback(client, phone, response_message)
        elif status in {"menu", "menu_confirm", "menu_format"} and phone and result.get("menu_bundle"):
            delivered = client.send_menu_bundle(phone, dict(result.get("menu_bundle") or {}))
            if not delivered and str(result.get("message") or "").strip():
                delivered = _send_text_with_phone_fallback(client, phone, str(result.get("message") or ""))
        elif phone and str(result.get("message") or "").strip():
            delivered = _send_text_with_phone_fallback(client, phone, str(result.get("message") or ""))
        if not delivered and phone and status in {"ok", "menu", "menu_confirm", "menu_format", "error", "prompt"}:
            delivery_error = client.last_error_message or "EVOLUTION_DELIVERY_FAILED"
            logger.error(
                "EVOLUTION_DELIVERY_FAILED phone=%s status=%s text=%r error=%s",
                phone,
                status,
                response_message[:120],
                delivery_error,
            )
            if status == "ok" and result.get("games"):
                logger.error(
                    "EVOLUTION_ERROR: jogos gerados mas não entregues para %s (%s)",
                    phone,
                    delivery_error,
                )
    except Exception as exc:  # noqa: BLE001 - webhook must remain stable
        delivery_error = str(exc)
        logger.exception("EVOLUTION_ERROR during delivery for phone=%s: %s", phone, exc)

    result["delivered"] = delivered
    if delivery_error:
        result["delivery_error"] = delivery_error
    return result
