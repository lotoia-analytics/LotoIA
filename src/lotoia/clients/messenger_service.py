from __future__ import annotations

import logging
import random
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from lotoia.clients.client_guard import ValidationResult, validate_messenger_request
from lotoia.clients.conference_utils import resolve_next_target_contest
from lotoia.clients.constants import OFFICIAL_LANDING_URL
from lotoia.clients.game_expansion import expand_generation_games_for_format
from lotoia.clients.game_request_parser import parse_game_request
from lotoia.clients.interactive_menu import plan_generation_targets
from lotoia.clients.messenger_evolution_service import MessengerEvolutionService
from lotoia.clients.messenger_onboarding import handle_new_messenger_lead
from lotoia.clients.repository import ClientRepository
from lotoia.clients.whatsapp_service import GENERATION_ERROR_MESSAGE, format_games_whatsapp_message
from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.generator.engine import generate_ranked_games
from lotoia.public.persistence import GenerationEventRepository, LeadRepository

logger = logging.getLogger(__name__)

_PROCESSED_MESSAGE_IDS: dict[str, datetime] = {}
_IDEMPOTENCY_TTL = timedelta(hours=6)

INACTIVE_CLIENT_MESSAGE = (
    "Seu plano não está ativo.\n"
    f"Renove em {OFFICIAL_LANDING_URL} para continuar gerando jogos."
)


def _cleanup_processed_message_ids() -> None:
    cutoff = datetime.now(UTC) - _IDEMPOTENCY_TTL
    expired = [message_id for message_id, seen_at in _PROCESSED_MESSAGE_IDS.items() if seen_at < cutoff]
    for message_id in expired:
        _PROCESSED_MESSAGE_IDS.pop(message_id, None)


def _remember_message_id(message_id: str) -> bool:
    if not message_id:
        return False
    _cleanup_processed_message_ids()
    if message_id in _PROCESSED_MESSAGE_IDS:
        return True
    _PROCESSED_MESSAGE_IDS[message_id] = datetime.now(UTC)
    return False


def extract_messenger_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize Meta Messenger or Evolution API payloads."""
    for entry in payload.get("entry", []) or []:
        if not isinstance(entry, dict):
            continue
        for messaging in entry.get("messaging", []) or []:
            if not isinstance(messaging, dict):
                continue
            sender = dict(messaging.get("sender") or {})
            message = dict(messaging.get("message") or {})
            psid = str(sender.get("id") or "").strip()
            text = str(message.get("text") or "").strip()
            message_id = str(message.get("mid") or messaging.get("timestamp") or "")
            if psid:
                return {
                    "psid": psid,
                    "text": text,
                    "message_id": message_id,
                    "from_me": False,
                }

    data = dict(payload.get("data") or payload)
    psid = str(
        data.get("sender")
        or payload.get("sender")
        or data.get("number")
        or payload.get("number")
        or ""
    ).strip()
    text = str(data.get("text") or payload.get("text") or "").strip()
    message_id = str(data.get("id") or payload.get("message_id") or "")
    from_me = bool(data.get("fromMe") or payload.get("fromMe"))
    return {
        "psid": psid,
        "text": text,
        "message_id": message_id,
        "from_me": from_me,
    }


def generate_messenger_games(
    *,
    targets: list[tuple[int, int]],
    psid: str,
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

    lead_repo = LeadRepository(db_path)
    lead = lead_repo.find_by_first_name_and_whatsapp(client_name, str(psid))
    if lead is None:
        lead = lead_repo.find_by_first_name_and_whatsapp("Messenger", str(psid))
    if lead is None:
        lead = lead_repo.insert(
            first_name=client_name or "Messenger",
            whatsapp=str(psid),
            source="messenger",
            ip_hash="",
            user_agent="messenger_bot",
        )

    generation_repo = GenerationEventRepository(db_path)
    generation_event = generation_repo.insert(
        lead_id=int(lead["id"]),
        generated_games=games,
        ml_enabled=False,
        seed=seed,
        strategy="messenger_statistical_v1",
        ranking_score=ranking_score,
        execution_time_ms=execution_time_ms,
        origin="messenger_bot",
        generation_mode="messenger_hybrid_statistical_v1",
        context={
            "targets": [{"formato": int(formato), "quantidade": int(qty)} for formato, qty in targets],
            "quantidade": int(quantidade),
            "source": "messenger",
            "messenger_psid": str(psid),
        },
        first_name=client_name,
        whatsapp=str(psid),
        channel="messenger",
    )
    return games, generation_event


def process_messenger_webhook(
    payload: dict[str, Any],
    *,
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    extracted = extract_messenger_payload(payload)
    psid = str(extracted.get("psid") or "")
    text = str(extracted.get("text") or "")
    message_id = str(extracted.get("message_id") or "")

    if extracted.get("from_me"):
        return {"status": "ignored", "reason": "from_me", "psid": psid}

    if message_id and _remember_message_id(message_id):
        return {
            "status": "ignored",
            "reason": "duplicate_message",
            "message_id": message_id,
            "psid": psid,
        }

    if not psid:
        return {
            "status": "error",
            "error_code": "INVALID_PAYLOAD",
            "message": "PSID não identificado no payload.",
        }

    repository = ClientRepository(db_path)
    client = repository.get_by_messenger_psid(psid)
    if client is None:
        onboarding = handle_new_messenger_lead(psid, db_path=db_path)
        return {
            "status": "onboarding",
            "psid": psid,
            "message": str(onboarding.get("message") or ""),
            "lead_id": onboarding.get("lead_id"),
            "duplicate": bool(onboarding.get("duplicate")),
        }

    client_status = repository.get_client_status_by_psid(psid)
    parsed = parse_game_request(text, channel="messenger")
    if not parsed:
        status = str(client.get("status", "") or "").strip().lower()
        if status != "ativo":
            return {
                "status": "error",
                "error_code": "PLAN_INACTIVE",
                "psid": psid,
                "message": INACTIVE_CLIENT_MESSAGE,
            }
        return {
            "status": "prompt",
            "psid": psid,
            "message": (
                "Digite quantos jogos deseja gerar.\n"
                "Exemplos: 3 | 2x15D | 5 jogos 18D"
            ),
        }

    quantidade = int(parsed["quantidade"])
    targets = plan_generation_targets(parsed, client_status=client_status)
    validation_formato = int(targets[0][0]) if len(targets) == 1 else int(parsed.get("formato") or 15)
    validation = validate_messenger_request(psid, validation_formato, quantidade, db_path=db_path)
    if not validation.ok:
        return {
            "status": "error",
            "error_code": validation.error_code,
            "psid": psid,
            "message": validation.message,
        }

    try:
        return _execute_valid_generation(
            psid=psid,
            validation=validation,
            targets=targets,
            db_path=db_path,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("MESSENGER_GENERATION_ERROR for psid=%s: %s", psid, exc)
        return {
            "status": "error",
            "error_code": "GENERATION_ERROR",
            "psid": psid,
            "message": GENERATION_ERROR_MESSAGE,
        }


def _execute_valid_generation(
    *,
    psid: str,
    validation: ValidationResult,
    targets: list[tuple[int, int]],
    db_path: Path,
) -> dict[str, Any]:
    client = dict(validation.client or {})
    quantidade = int(validation.quantidade or 0)
    games, generation_event = generate_messenger_games(
        targets=targets,
        psid=psid,
        client_name=str(client.get("name") or "Cliente"),
        db_path=db_path,
    )
    log_formato = max(formato for formato, _ in targets)
    repository = ClientRepository(db_path)
    concurso_alvo = resolve_next_target_contest(db_path)
    client_generation = repository.log_client_generation(
        client_id=int(client["id"]),
        phone=str(client.get("phone") or repository.messenger_phone(psid)),
        formato=log_formato,
        quantidade=quantidade,
        jogos=games,
        generation_event_id=int(generation_event.get("id") or 0) or None,
        concurso_alvo=concurso_alvo,
        channel="messenger",
    )
    repository.increment_daily_usage(int(client["id"]), quantidade=quantidade)
    response_message = format_games_whatsapp_message(
        quantidade=quantidade,
        games=games,
        targets=targets,
    )
    return {
        "status": "ok",
        "psid": psid,
        "channel": "messenger",
        "message": response_message,
        "games": games,
        "quantidade": quantidade,
        "formato": log_formato if len(targets) == 1 else None,
        "generation_event_id": generation_event.get("id"),
        "client_generation_id": client_generation.get("id"),
        "trace_id": f"ms-{uuid4().hex[:12]}",
    }


def deliver_messenger_webhook(
    payload: dict[str, Any],
    *,
    db_path: Path = DEFAULT_DATABASE_PATH,
    messenger_client: MessengerEvolutionService | None = None,
) -> dict[str, Any]:
    result = dict(process_messenger_webhook(payload, db_path=db_path))
    status = str(result.get("status", "") or "")
    psid = str(result.get("psid") or "")
    client = messenger_client or MessengerEvolutionService()
    delivered = False
    delivery_error = ""

    if status == "ignored":
        result["delivered"] = False
        result["delivery_skipped"] = True
        return result

    try:
        message = str(result.get("message") or "").strip()
        if psid and message:
            delivered = client.send_text_sync(psid, message)
        if not delivered and psid and status in {"ok", "onboarding", "error", "prompt"}:
            delivery_error = client.last_error_message or "MESSENGER_DELIVERY_FAILED"
    except Exception as exc:  # noqa: BLE001
        delivery_error = str(exc)
        logger.exception("MESSENGER_DELIVERY_ERROR for psid=%s: %s", psid, exc)

    result["delivered"] = delivered
    if delivery_error:
        result["delivery_error"] = delivery_error
    return result
