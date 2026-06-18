from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from sqlalchemy.exc import IntegrityError

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    InstitutionalOutputSignature,
    get_session,
)


def _raw_numbers(numbers: Any) -> list[int]:
    values: list[int] = []
    if numbers is None:
        return values
    if isinstance(numbers, Mapping):
        numbers = numbers.get("numbers", [])
    for raw in numbers if isinstance(numbers, Iterable) and not isinstance(numbers, (str, bytes)) else []:
        try:
            number = int(raw)
        except Exception:
            continue
        if 1 <= number <= 25:
            values.append(number)
    return values


def _normalized_numbers(numbers: Any) -> list[int]:
    values: list[int] = []
    if numbers is None:
        return values
    if isinstance(numbers, Mapping):
        numbers = numbers.get("numbers", [])
    for raw in numbers if isinstance(numbers, Iterable) and not isinstance(numbers, (str, bytes)) else []:
        try:
            number = int(raw)
        except Exception:
            continue
        if 1 <= number <= 25:
            values.append(number)
    return sorted(dict.fromkeys(values))


def game_signature(numbers: Sequence[int] | Iterable[int]) -> str:
    normalized = sorted({int(number) for number in numbers if 1 <= int(number) <= 25})
    return "-".join(f"{number:02d}" for number in normalized)


def load_batch_output_signatures(batch_id: str | None, db_path: Any = DEFAULT_DATABASE_PATH) -> set[str]:
    resolved_batch_id = str(batch_id or "").strip()
    if not resolved_batch_id:
        return set()
    with get_session(db_path) as session:
        rows = (
            session.query(InstitutionalOutputSignature.game_signature)
            .filter(InstitutionalOutputSignature.batch_id == resolved_batch_id)
            .all()
        )
        return {str(row[0] or "") for row in rows if str(row[0] or "")}


def load_all_output_signatures(db_path: Any = DEFAULT_DATABASE_PATH) -> set[str]:
    with get_session(db_path) as session:
        rows = session.query(InstitutionalOutputSignature.game_signature).all()
        return {str(row[0] or "") for row in rows if str(row[0] or "")}


def output_commander_validate_games(
    games: Sequence[Mapping[str, Any]] | Sequence[dict[str, Any]],
    batch_id: str | None = None,
    generation_event_id: int | None = None,
    *,
    target_size: int | None = None,
    required_total: int | None = None,
    candidate_total: int | None = None,
    db_path: Any = DEFAULT_DATABASE_PATH,
    persisted_signatures: Iterable[str] | None = None,
    historical_deduplication_mode: str = "BLOCK",
) -> dict[str, Any]:
    resolved_batch_id = str(batch_id or "").strip() or "global"
    historical_signatures = set(
        str(signature) for signature in (persisted_signatures or load_batch_output_signatures(batch_id, db_path))
    )
    batch_signatures: set[str] = set()
    accepted_games: list[dict[str, Any]] = []
    accepted_signatures: list[str] = []
    duplicate_hashes: list[str] = []
    invalid_games: list[dict[str, Any]] = []
    historical_duplicates_found = 0
    audit_only = str(historical_deduplication_mode or "BLOCK").upper() == "AUDIT_ONLY"

    for index, game in enumerate(games, start=1):
        raw_numbers = _raw_numbers(game.get("numbers", []))
        normalized_numbers = sorted(dict.fromkeys(raw_numbers))
        signature = game_signature(raw_numbers)
        game_errors: list[str] = []
        if target_size is not None and len(raw_numbers) != int(target_size):
            game_errors.append(f"quantidade_dezenas_invalida:{len(raw_numbers)}")
        if len(raw_numbers) != len(set(raw_numbers)):
            game_errors.append("dezenas_duplicadas")
        if any(number < 1 or number > 25 for number in raw_numbers):
            game_errors.append("dezenas_fora_do_intervalo")
        if not raw_numbers:
            game_errors.append("jogo_vazio")
        if signature in batch_signatures:
            duplicate_hashes.append(signature)
            game_errors.append("duplicado_na_bateria")
        elif signature in historical_signatures:
            duplicate_hashes.append(signature)
            historical_duplicates_found += 1
            if not audit_only:
                game_errors.append("duplicado_historico")
        if game_errors:
            invalid_games.append(
                {
                    "index": index,
                    "signature": signature,
                    "numbers": normalized_numbers,
                    "errors": game_errors,
                }
            )
            continue
        batch_signatures.add(signature)
        historical_signatures.add(signature)
        accepted_signatures.append(signature)
        accepted_games.append(dict(game, numbers=normalized_numbers, game_signature=signature))

    total_requested = len(games)
    total_unique = len(accepted_signatures)
    total_duplicates = total_requested - total_unique
    total_size = int(target_size or 0)
    requested_total = int(required_total if required_total is not None else total_requested)
    candidate_total_value = int(candidate_total if candidate_total is not None else total_requested)
    approved_total = len(accepted_games)
    rejected_total = max(0, candidate_total_value - approved_total)
    blocked_reasons: list[str] = []
    if invalid_games:
        blocked_reasons.append("jogos_invalidos_ou_duplicados")
    if total_duplicates:
        blocked_reasons.append("duplicidade_na_bateria")
    if historical_duplicates_found and not audit_only:
        blocked_reasons.append("duplicidade_historica")
    if approved_total < requested_total:
        blocked_reasons.append("nao_atingiu_quantidade_solicitada")
    status = "APROVADO" if not blocked_reasons and approved_total == requested_total else "BLOQUEADO"
    error_message = ""
    if blocked_reasons:
        error_message = " / ".join(blocked_reasons)
    natural_approvable_candidate = approved_total > 0 and approved_total < requested_total
    candidate_reason = "valid_individual_games_but_incomplete_requested_package" if natural_approvable_candidate else ""

    return {
        "batch_id": resolved_batch_id,
        "generation_event_id": generation_event_id,
        "quantidade_jogos_solicitada": requested_total,
        "requested_games": requested_total,
        "quantidade_jogos_candidatos": candidate_total_value,
        "generated_candidates": candidate_total_value,
        "quantidade_jogos_gerada": candidate_total_value,
        "quantidade_jogos_aprovados": approved_total,
        "approved_total": approved_total,
        "quantidade_jogos_persistidos": 0,
        "persisted_games": 0,
        "quantidade_jogos_unicos": total_unique,
        "quantidade_jogos_duplicados": total_duplicates,
        "quantidade_jogos_rejeitados": rejected_total,
        "quantidade_dezenas_por_jogo": total_size,
        "taxa_duplicidade": round(total_duplicates / max(1, total_requested), 4),
        "status_comandante_saida": status,
        "output_commander_status": status,
        "error_message": error_message,
        "motivo_bloqueio": error_message,
        "blocked_reason": error_message,
        "natural_approvable_candidate": natural_approvable_candidate,
        "candidate_reason": candidate_reason,
        "duplicate_hashes": duplicate_hashes,
        "historical_duplicates_found": historical_duplicates_found,
        "historical_duplicates_removed": 0 if str(historical_deduplication_mode or "BLOCK").upper() == "AUDIT_ONLY" else historical_duplicates_found,
        "historical_deduplication_mode": str(historical_deduplication_mode or "BLOCK").upper(),
        "official_package_preserved": str(historical_deduplication_mode or "BLOCK").upper() == "AUDIT_ONLY",
        "invalid_games": invalid_games,
        "accepted_games": accepted_games,
        "accepted_signatures": accepted_signatures,
    }


def register_output_signatures(
    games: Sequence[Mapping[str, Any]] | Sequence[dict[str, Any]],
    *,
    batch_id: str,
    generation_event_id: int | None,
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    resolved_batch_id = str(batch_id or "").strip()
    if not resolved_batch_id:
        raise ValueError("batch_id must be provided to register output signatures")
    inserted = 0
    with get_session(db_path) as session:
        try:
            for index, game in enumerate(games, start=1):
                numbers = _normalized_numbers(game.get("numbers", []))
                signature = str(game.get("game_signature") or game_signature(numbers))
                session.add(
                    InstitutionalOutputSignature(
                        batch_id=resolved_batch_id,
                        generation_event_id=generation_event_id,
                        game_signature=signature,
                        payload={
                            "game_index": index,
                            "numbers": numbers,
                            "source": "institutional_output_commander",
                        },
                    )
                )
                inserted += 1
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise RuntimeError(f"duplicate game signature blocked for batch {resolved_batch_id}: {exc}") from exc
    return {
        "batch_id": resolved_batch_id,
        "generation_event_id": generation_event_id,
        "inserted": inserted,
    }
