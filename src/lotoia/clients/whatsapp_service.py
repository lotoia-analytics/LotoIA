from __future__ import annotations

import random
import re
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from lotoia.clients.client_guard import ValidationResult, validate_request
from lotoia.clients.game_expansion import expand_generation_games_for_format
from lotoia.clients.message_parser import HELP_MESSAGE, parse_whatsapp_message
from lotoia.clients.repository import ClientRepository
from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.generator.engine import generate_ranked_games
from lotoia.public.persistence import GenerationEventRepository, LeadRepository
from lotoia.public.services import normalize_whatsapp

_PROCESSED_MESSAGE_IDS: dict[str, datetime] = {}
_IDEMPOTENCY_TTL = timedelta(hours=6)


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


def extract_evolution_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload.get("data") or payload)
    key = dict(data.get("key") or {})
    remote_jid = str(key.get("remoteJid") or data.get("remoteJid") or "")
    phone = re.sub(r"\D", "", remote_jid.split("@", maxsplit=1)[0])
    message = dict(data.get("message") or {})
    text = (
        message.get("conversation")
        or message.get("extendedTextMessage", {}).get("text")
        or data.get("text")
        or payload.get("text")
        or ""
    )
    message_id = str(key.get("id") or data.get("id") or payload.get("message_id") or "")
    return {
        "phone": phone,
        "text": str(text).strip(),
        "message_id": message_id,
    }


def format_games_whatsapp_message(*, quantidade: int, formato: int, games: list[dict[str, Any]]) -> str:
    lines = [f"✅ {quantidade} jogos de {formato}D gerados pela LotoIA:", ""]
    for index, game in enumerate(games, start=1):
        numbers = sorted(int(number) for number in game.get("numbers", []) or game.get("final_card_numbers", []))
        formatted_numbers = " - ".join(f"{number:02d}" for number in numbers)
        lines.append(f"Jogo {index:02d}: {formatted_numbers}")
    lines.append("")
    lines.append("Boa sorte! 🍀")
    return "\n".join(lines)


def generate_whatsapp_games(
    *,
    quantidade: int,
    formato: int,
    phone: str,
    client_name: str = "Cliente",
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    seed = random.randint(1, 999999)
    started_at = time.time()
    base_games = generate_ranked_games(total_games=int(quantidade), seed=seed, ml_enabled=False)
    games = expand_generation_games_for_format(base_games, int(formato))
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
        context={"formato": int(formato), "quantidade": int(quantidade), "source": "whatsapp_bot"},
        first_name=client_name,
        whatsapp=normalized_phone,
    )
    return games, generation_event


def process_whatsapp_webhook(
    payload: dict[str, Any],
    *,
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    extracted = extract_evolution_payload(payload)
    phone = str(extracted.get("phone") or "")
    text = str(extracted.get("text") or "")
    message_id = str(extracted.get("message_id") or "")

    if message_id and _remember_message_id(message_id):
        return {
            "status": "ignored",
            "reason": "duplicate_message",
            "message_id": message_id,
            "phone": phone,
        }

    if not phone:
        return {"status": "error", "error_code": "INVALID_PAYLOAD", "message": "Telefone não identificado no payload."}

    parsed = parse_whatsapp_message(text)
    if not parsed:
        return {
            "status": "help",
            "phone": phone,
            "message": HELP_MESSAGE,
        }

    quantidade = int(parsed["quantidade"])
    formato = parsed.get("formato")
    validation = validate_request(phone, formato, quantidade, db_path=db_path)
    if not validation.ok:
        return {
            "status": "error",
            "error_code": validation.error_code,
            "phone": phone,
            "message": validation.message,
        }

    return _execute_valid_generation(phone=phone, validation=validation, db_path=db_path)


def _execute_valid_generation(
    *,
    phone: str,
    validation: ValidationResult,
    db_path: Path,
) -> dict[str, Any]:
    client = dict(validation.client or {})
    quantidade = int(validation.quantidade or 0)
    formato = int(validation.formato or 15)
    games, generation_event = generate_whatsapp_games(
        quantidade=quantidade,
        formato=formato,
        phone=phone,
        client_name=str(client.get("name") or "Cliente"),
        db_path=db_path,
    )
    repository = ClientRepository(db_path)
    client_generation = repository.log_client_generation(
        client_id=int(client["id"]),
        phone=phone,
        formato=formato,
        quantidade=quantidade,
        jogos=games,
        generation_event_id=int(generation_event.get("id") or 0) or None,
    )
    repository.increment_daily_usage(int(client["id"]), quantidade=quantidade)
    response_message = format_games_whatsapp_message(quantidade=quantidade, formato=formato, games=games)
    return {
        "status": "ok",
        "phone": normalize_whatsapp(phone),
        "message": response_message,
        "games": games,
        "quantidade": quantidade,
        "formato": formato,
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
