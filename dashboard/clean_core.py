from __future__ import annotations

import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
from sqlalchemy import text

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
for candidate in (str(CURRENT_DIR), str(ROOT_DIR)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from lotoia.database.database import (  # noqa: E402
    DEFAULT_DATABASE_PATH,
    GeneratedGame,
    GenerationEvent,
    InstitutionalOutputSignature,
    ReconciliationRun,
    create_database,
    get_session,
)
from lotoia.generator.engine import generate_ranked_games  # noqa: E402
from lotoia.governance.output_commander import load_all_output_signatures, output_commander_validate_games  # noqa: E402


OFFICIAL_CARD_FORMATS = (15, 17, 18)
AUDITED_RESERVE_PRIORITY = (7, 22, 4, 11, 12, 15, 16, 19, 21, 2, 17, 23, 13, 1, 9, 5, 6, 8, 14, 18, 20, 24, 25)
DB_PATH = DEFAULT_DATABASE_PATH


def _to_int_list(values: Sequence[int] | None) -> list[int]:
    return [int(value) for value in (values or []) if 1 <= int(value) <= 25]


def _format_numbers_for_history(values: Sequence[int] | None) -> str:
    return " ".join(f"{number:02d}" for number in _to_int_list(values))


def _parse_numbers_text(value: str | None) -> list[int]:
    if not value:
        return []
    numbers: list[int] = []
    for token in str(value).replace(",", " ").split():
        try:
            number = int(token)
        except Exception:
            continue
        if 1 <= number <= 25:
            numbers.append(number)
    return numbers


def _database_snapshot() -> dict[str, Any]:
    create_database(DB_PATH)
    counts: dict[str, int] = {}
    latest: dict[str, Any] = {}
    with get_session(DB_PATH) as session:
        counts["generation_events"] = int(session.query(GenerationEvent).count())
        counts["generated_games"] = int(session.query(GeneratedGame).count())
        counts["reconciliation_runs"] = int(session.query(ReconciliationRun).count())
        try:
            counts["imported_contests"] = int(session.execute(text("SELECT COUNT(*) FROM imported_contests")).scalar() or 0)
        except Exception:
            counts["imported_contests"] = 0
        try:
            counts["lotofacil_official_history"] = int(session.execute(text("SELECT COUNT(*) FROM lotofacil_official_history")).scalar() or 0)
        except Exception:
            counts["lotofacil_official_history"] = 0
        latest_generation = session.query(GenerationEvent).order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc()).first()
        latest["generation_events"] = int(latest_generation.id) if latest_generation else "-"
        latest["generated_games"] = int(latest_generation.id) if latest_generation else "-"
        latest["reconciliation_runs"] = int(session.query(ReconciliationRun).order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc()).first().id) if session.query(ReconciliationRun).count() else "-"
        try:
            latest["imported_contests"] = int(session.execute(text("SELECT COALESCE(MAX(contest_number), 0) FROM imported_contests")).scalar() or 0) or "-"
        except Exception:
            latest["imported_contests"] = "-"
        try:
            latest["lotofacil_official_history"] = int(session.execute(text("SELECT COALESCE(MAX(contest_number), 0) FROM lotofacil_official_history")).scalar() or 0) or "-"
        except Exception:
            latest["lotofacil_official_history"] = "-"
    return {"counts": counts, "latest": latest, "backend": "sqlite", "source": "clean_core"}


def _live_institutional_snapshot(snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    return _database_snapshot() if snapshot is None else snapshot


def _ensure_official_history_seeded() -> dict[str, Any]:
    return {"status": "ok", "seeded": False, "source": "clean_core"}


def get_clean_snapshot() -> dict[str, Any]:
    return _live_institutional_snapshot(_database_snapshot())


def _expand_official_card(
    core_numbers: Sequence[int],
    card_format: int,
    *,
    game_index: int = 0,
) -> tuple[list[int], list[int], list[int]]:
    core = sorted(set(_to_int_list(core_numbers)))
    target_size = int(card_format or 15)
    if target_size <= len(core):
        return core, [], core[:target_size]
    needed = target_size - len(core)
    reserves: list[int] = []
    priority = list(AUDITED_RESERVE_PRIORITY)
    if priority and game_index:
        offset = int(game_index - 1) % len(priority)
        priority = priority[offset:] + priority[:offset]
    for number in priority:
        if number in core or number in reserves:
            continue
        reserves.append(int(number))
        if len(reserves) >= needed:
            break
    if len(reserves) < needed:
        for number in range(1, 26):
            if number in core or number in reserves:
                continue
            reserves.append(int(number))
            if len(reserves) >= needed:
                break
    final_card = sorted(core + reserves[:needed])
    return core, reserves[:needed], final_card


def _expand_generation_games_for_format(
    games: Sequence[dict[str, Any]],
    card_format: int,
) -> list[dict[str, Any]]:
    expanded_games: list[dict[str, Any]] = []
    for index, game in enumerate(games, start=1):
        core_numbers = list(game.get("numbers", []) or [])
        core, reserves, final_card = _expand_official_card(core_numbers, card_format, game_index=index)
        expanded_games.append(
            {
                **dict(game),
                "card_format": int(card_format or 15),
                "core_numbers": core,
                "audited_reserve_numbers": reserves,
                "final_card_numbers": final_card,
            }
        )
    return expanded_games


def _persist_clean_law15_generation_history(
    *,
    result: dict[str, Any],
    selected_card_format: int,
) -> dict[str, Any]:
    games = list(result.get("games") or [])
    if not games:
        return {}
    formatted_games = _expand_generation_games_for_format(games, selected_card_format)
    payload_games: list[dict[str, Any]] = []
    for game in formatted_games:
        core_numbers = list(game.get("core_numbers", game.get("numbers", [])) or [])
        reserves = list(game.get("audited_reserve_numbers", []) or [])
        final_card = list(game.get("final_card_numbers", game.get("numbers", [])) or [])
        payload_games.append(
            {
                **dict(game),
                "numbers": core_numbers,
                "card_format": int(selected_card_format),
                "selected_card_format": int(selected_card_format),
                "core_numbers": core_numbers,
                "audited_reserve_numbers": reserves,
                "final_card_numbers": final_card,
                "display_core_numbers": _format_numbers_for_history(core_numbers),
                "display_audited_reserve_numbers": _format_numbers_for_history(reserves),
                "display_final_card_numbers": _format_numbers_for_history(final_card),
            }
        )
    generation_context = {
        "generation_mode": "CLEAN_LAW15_ISOLATED_PAGE",
        "policy_mode": "CLEAN_LAW15_ISOLATED_PAGE",
        "selected_card_format": int(selected_card_format),
        "format_cartao": int(selected_card_format),
        "selected_quantity": int(result.get("requested_count", 0) or 0),
        "quantidade_nucleo": 15,
        "quantidade_reservas": 0 if int(selected_card_format) == 15 else 2 if int(selected_card_format) == 17 else 3,
        "quantidade_final": int(selected_card_format),
        "núcleo_lei_15": _format_numbers_for_history(payload_games[0].get("core_numbers", [])),
        "reservas_auditadas": _format_numbers_for_history(payload_games[0].get("audited_reserve_numbers", [])),
        "cartão_final": _format_numbers_for_history(payload_games[0].get("final_card_numbers", [])),
        "format_label": str(result.get("card_format_label", "")),
        "scientific_law_role": "COMMANDER",
        "clean_adm_runtime_role": "EXECUTOR",
        "output_commander_role": "AUDITOR",
        "legacy_calibrator_role": "REMOVED_FROM_RUNTIME",
        "calibration_engine_role": "DISABLED",
        "historical_deduplication_mode": str(result.get("historical_deduplication_mode", "AUDIT_ONLY") or "AUDIT_ONLY"),
        "validation_status_lei_17": str(result.get("validation_status_lei_17", "") or ""),
        "validation_status_lei_18": str(result.get("validation_status_lei_18", "") or ""),
        "card_format": int(selected_card_format),
    }
    target_contest = None
    with get_session(DB_PATH) as session:
        try:
            latest_imported = session.execute(text("SELECT COALESCE(MAX(contest_number), NULL) FROM imported_contests")).scalar()
        except Exception:
            latest_imported = None
        if latest_imported:
            target_contest = int(latest_imported)
    return _persist_generation_snapshot(
        games=payload_games,
        seed=int(result.get("seed", 0) or 0),
        target_contest=target_contest,
        batch_id=str(result.get("batch_id", "") or f"clean-law15-{selected_card_format}"),
        generation_context=generation_context,
    )


def _persist_generation_snapshot(
    *,
    games: list[dict[str, Any]],
    seed: int,
    target_contest: int | None,
    batch_id: str | None = None,
    generation_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started_at = time.monotonic()
    context_payload = {
        "source": "clean_core",
        "target_contest": target_contest,
        "build_marker": "clean-zero",
        "batch_id": batch_id,
    }
    if generation_context:
        context_payload.update({str(key): value for key, value in generation_context.items()})
    with get_session(DB_PATH) as session:
        event = GenerationEvent(
            lead_id=None,
            first_name="clean",
            whatsapp="",
            generated_games=games,
            context_json={**context_payload},
            ml_enabled=0,
            seed=seed,
            strategy="clean_law15_isolated",
            ranking_score=0.0,
            execution_time_ms=0.0,
        )
        session.add(event)
        session.flush()
        generation_event_id = int(event.id)
        event.context_json = {**context_payload, "generation_event_id": generation_event_id, "game_signatures": []}
        game_signatures: list[str] = []
        for index, game in enumerate(games, start=1):
            numbers = list(game.get("numbers", []))
            signature = "-".join(f"{number:02d}" for number in numbers)
            game_signatures.append(signature)
            per_game_context = {
                "card_format": int(game.get("card_format", 15) or 15),
                "selected_card_format": int(game.get("selected_card_format", game.get("card_format", 15)) or 15),
                "format_cartao": int(game.get("card_format", 15) or 15),
                "quantidade_nucleo": 15,
                "quantidade_reservas": len(game.get("audited_reserve_numbers", []) or []),
                "quantidade_final": len(game.get("final_card_numbers", numbers) or numbers),
                "core_numbers": list(game.get("core_numbers", numbers) or numbers),
                "audited_reserve_numbers": list(game.get("audited_reserve_numbers", []) or []),
                "final_card_numbers": list(game.get("final_card_numbers", numbers) or numbers),
                "display_core_numbers": str(game.get("display_core_numbers", "") or ""),
                "display_audited_reserve_numbers": str(game.get("display_audited_reserve_numbers", "") or ""),
                "display_final_card_numbers": str(game.get("display_final_card_numbers", "") or ""),
                "validation_status_lei_17": str(game.get("validation_status_lei_17", "") or ""),
                "validation_status_lei_18": str(game.get("validation_status_lei_18", "") or ""),
            }
            session.add(
                GeneratedGame(
                    generation_event_id=generation_event_id,
                    lead_id=None,
                    target_contest=target_contest,
                    origin="clean_app",
                    generation_mode="clean_law15_isolated",
                    game_index=index,
                    numbers=numbers,
                    profile_type=str(game.get("profile_type", "")),
                    final_score=dict(game.get("final_score", {})) if isinstance(game.get("final_score"), dict) else {},
                    quadra_score=dict(game.get("quadra_score", {})) if isinstance(game.get("quadra_score"), dict) else {},
                    context_json={**context_payload, **per_game_context, "game_signature": signature, "game_index": index},
                )
            )
            session.add(
                InstitutionalOutputSignature(
                    batch_id=str(batch_id or "").strip() or "global",
                    generation_event_id=generation_event_id,
                    game_signature=signature,
                    payload={
                        "game_index": index,
                        "numbers": numbers,
                        **per_game_context,
                        "source": "clean_core",
                        "build_marker": "clean-zero",
                        "generation_hierarchy": "LOTOIA_LAW_ONLY",
                        "scientific_law_role": "COMMANDER",
                        "legacy_calibrator_role": "REMOVED_FROM_RUNTIME",
                        "calibration_engine_role": "DISABLED",
                        "geometric_filters_role": "SAFETY_GUARDRAIL",
                        "output_commander_role": "AUDITOR",
                        "memory_registry_role": "REGISTRY",
                        "legacy_removed_from_runtime": True,
                        "legacy_runtime_access": False,
                        "legacy_reason": "historical_compatibility_or_tests_only",
                    },
                )
            )
        event.context_json = {**context_payload, "generation_event_id": generation_event_id, "game_signatures": list(game_signatures)}
        event.execution_time_ms = round((time.monotonic() - started_at) * 1000, 2)
        session.commit()
    return {"generation_event_id": generation_event_id, "seed": seed, "games_count": len(games), "target_contest": target_contest, "batch_id": batch_id}


def _run_clean_law15_generation(*, requested_count: int, selected_card_format: int = 15) -> dict[str, Any]:
    fill_diagnostics: dict[str, Any] = {}
    total_games = int(requested_count)
    seed = int(time.time()) % 1_000_000
    latest_numbers: set[int] = set()
    batch_number_usage: dict[int, int] = {}
    batch_profile_usage: dict[tuple[int, int], int] = {}
    games = generate_ranked_games(total_games, seed=seed, ml_enabled=False, pool_size=max(total_games, 30))
    games = [
        {
            **dict(game),
            "numbers": _to_int_list(game.get("numbers", [])),
            "profile_type": str(game.get("profile_type", "HYBRID") or "HYBRID"),
        }
        for game in games[:total_games]
    ]
    for game in games:
        key = tuple(game["numbers"])
        batch_number_usage[key[0] if key else 0] = batch_number_usage.get(key[0] if key else 0, 0) + 1
        batch_profile_usage[(0, 0)] = batch_profile_usage.get((0, 0), 0) + 1
    commander_report = output_commander_validate_games(
        games,
        batch_id=f"clean-law15-{seed}",
        generation_event_id=None,
        target_size=15,
        required_total=total_games,
        candidate_total=total_games,
        persisted_signatures=set(load_all_output_signatures(DB_PATH)),
        historical_deduplication_mode="AUDIT_ONLY",
    )
    if len(games) < total_games:
        commander_report = {
            **commander_report,
            "status_comandante_saida": "BLOQUEADO",
            "motivo_bloqueio": "INSUFFICIENT_VALID_CANDIDATES",
            "error_message": "INSUFFICIENT_VALID_CANDIDATES",
        }
    fill_diagnostics["rejected_by_output_commander"] = int(commander_report.get("quantidade_jogos_rejeitados", 0) or 0)
    fill_diagnostics["fill_completed"] = len(games) >= total_games
    fill_diagnostics["insufficient_reason"] = "none" if len(games) >= total_games else "INSUFFICIENT_VALID_CANDIDATES"
    return {
        "seed": seed,
        "batch_id": f"clean-law15-{seed}",
        "requested_count": total_games,
        "games": games,
        "commander_report": commander_report,
        "fill_diagnostics": fill_diagnostics,
        "batch_fill_strategy": "FILL_UNTIL_REQUESTED_QUANTITY",
        "generation_mode": "CLEAN_LAW15_ISOLATED_PAGE",
        "policy_mode": "CLEAN_LAW15_ISOLATED_PAGE",
        "selected_quantity": total_games,
        "dezenas_por_jogo": 15,
        "scientific_law_role": "COMMANDER",
        "clean_adm_runtime_role": "EXECUTOR",
        "output_commander_role": "AUDITOR",
        "historical_deduplication_mode": "AUDIT_ONLY",
        "historical_duplicates_removed": 0,
        "legacy_generation_flow": "ARCHIVED",
        "legacy_dashboard_generation": "BYPASSED",
        "legacy_calibrator_role": "REMOVED_FROM_RUNTIME",
        "calibration_engine_role": "DISABLED",
        "automatic_law_mutation_allowed": False,
        "silent_recalibration_allowed": False,
        "law_evolution_requires_audit": True,
        "selected_card_format": int(selected_card_format or 15),
    }


def run_clean_generation(*, requested_count: int, selected_card_format: int = 15) -> dict[str, Any]:
    base_result = _run_clean_law15_generation(requested_count=requested_count, selected_card_format=selected_card_format)
    games = list(base_result.get("games") or [])
    expanded_games = _expand_generation_games_for_format(games, int(selected_card_format or 15))
    persisted_result = _persist_clean_law15_generation_history(
        result={**base_result, "games": expanded_games, "selected_card_format": int(selected_card_format or 15)},
        selected_card_format=int(selected_card_format or 15),
    )
    if isinstance(persisted_result, dict) and persisted_result:
        return {
            **base_result,
            **persisted_result,
            "selected_card_format": int(selected_card_format or 15),
            "games": expanded_games,
            "display_games": expanded_games,
        }
    return {
        **base_result,
        "selected_card_format": int(selected_card_format or 15),
        "games": expanded_games,
        "display_games": expanded_games,
    }


def _load_accumulated_analytical_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with get_session(DB_PATH) as session:
        events = (
            session.query(GenerationEvent)
            .order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
            .all()
        )
        for event in events:
            games_rows = (
                session.query(GeneratedGame)
                .filter(GeneratedGame.generation_event_id == event.id)
                .order_by(GeneratedGame.game_index.asc())
                .all()
            )
            for row in games_rows:
                context_json = dict(row.context_json or {})
                core_numbers = list(context_json.get("core_numbers") or row.numbers or [])
                reserve_numbers = list(context_json.get("audited_reserve_numbers") or [])
                final_card_numbers = list(context_json.get("final_card_numbers") or row.numbers or [])
                card_format = int(context_json.get("selected_card_format", context_json.get("card_format", 15)) or 15)
                rows.append(
                    {
                        "geração": f"Geração {event.id}",
                        "generation_event_id": int(event.id or 0),
                        "batch_id": str(context_json.get("batch_id", "") or ""),
                        "data/hora": event.created_at.isoformat() if getattr(event, "created_at", None) else "",
                        "jogo n°": int(row.game_index or 0),
                        "dezenas": " ".join(f"{number:02d}" for number in row.numbers or []),
                        "formato_cartao": card_format,
                        "núcleo_lei_15": " ".join(f"{number:02d}" for number in core_numbers),
                        "reservas_auditadas": " ".join(f"+{number:02d}" for number in reserve_numbers) or "-",
                        "cartão_final": " ".join(f"{number:02d}" for number in final_card_numbers),
                        "quantidade_nucleo": int(context_json.get("quantidade_nucleo", len(core_numbers)) or len(core_numbers)),
                        "quantidade_reservas": int(context_json.get("quantidade_reservas", len(reserve_numbers)) or len(reserve_numbers)),
                        "quantidade_final": int(context_json.get("quantidade_final", len(final_card_numbers)) or len(final_card_numbers)),
                        "estratégia": str(event.strategy or "-"),
                        "score": round(float((row.final_score or {}).get("final_score", 0.0) or 0.0), 4),
                        "origem/modelo": str(row.origin or "clean_app"),
                        "status de conferência": "Nao conferido",
                        "concurso conferido": None,
                        "acertos": None,
                        "premiação": "—",
                        "observações": "-",
                    }
                )
    return rows


def _ensure_analytical_games_schema(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "geração",
                "generation_event_id",
                "batch_id",
                "data/hora",
                "jogo n°",
                "dezenas",
                "formato_cartao",
                "núcleo_lei_15",
                "reservas_auditadas",
                "cartão_final",
                "quantidade_nucleo",
                "quantidade_reservas",
                "quantidade_final",
                "estratégia",
                "score",
                "origem/modelo",
                "status de conferência",
                "concurso conferido",
                "acertos",
                "premiação",
                "observações",
            ]
    )
    return df


def _load_clean_generated_rows() -> list[dict[str, Any]]:
    return _load_accumulated_analytical_rows()


def _load_official_history_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with get_session(DB_PATH) as session:
            for contest_number, created_at, data, dezenas in session.execute(
                text(
                    "SELECT contest_number, created_at, data, dezenas "
                    "FROM imported_contests ORDER BY contest_number ASC"
                )
            ).fetchall():
                parsed_numbers = _parse_numbers_text(dezenas)
                rows.append(
                    {
                        "contest_number": int(contest_number or 0),
                        "created_at": created_at.isoformat() if getattr(created_at, "isoformat", None) else str(created_at or ""),
                        "data": str(data or ""),
                        "dezenas": " ".join(f"{number:02d}" for number in parsed_numbers),
                        "numbers": parsed_numbers,
                        "source": "imported_contests",
                    }
                )
    except Exception:
        pass
    if rows:
        return rows
    try:
        with get_session(DB_PATH) as session:
            for contest_number, created_at, draw_date, numbers, source in session.execute(
                text(
                    "SELECT contest_number, created_at, draw_date, numbers, source "
                    "FROM lotofacil_official_history ORDER BY contest_number ASC"
                )
            ).fetchall():
                parsed_numbers = _parse_numbers_text(numbers)
                rows.append(
                    {
                        "contest_number": int(contest_number or 0),
                        "created_at": created_at.isoformat() if getattr(created_at, "isoformat", None) else str(created_at or ""),
                        "data": str(draw_date or ""),
                        "dezenas": " ".join(f"{number:02d}" for number in parsed_numbers),
                        "numbers": parsed_numbers,
                        "source": str(source or "lotofacil_official_history"),
                    }
                )
    except Exception:
        return []
    return rows


def _load_clean_institutional_events() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    try:
        with get_session(DB_PATH) as session:
            generation_events = (
                session.query(GenerationEvent)
                .order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
                .limit(20)
                .all()
            )
            for event in generation_events:
                context = dict(event.context_json or {})
                events.append(
                    {
                        "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else "",
                        "event_type": "Geração Clean Zero",
                        "headline": f"Geração #{event.id}",
                        "details": f"Formato {context.get('selected_card_format', context.get('format_cartao', 15))} | Jogos {len(event.generated_games or [])}",
                    }
                )
            reconciliation_runs = (
                session.query(ReconciliationRun)
                .order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
                .limit(20)
                .all()
            )
            for run in reconciliation_runs:
                payload = dict(run.payload or {})
                events.append(
                    {
                        "created_at": run.created_at.isoformat() if getattr(run, "created_at", None) else "",
                        "event_type": "Conferência institucional",
                        "headline": f"Reconciliação #{run.id}",
                        "details": f"Concurso {payload.get('contest_number', '-')}",
                    }
                )
    except Exception:
        return []
    return events


def _load_generated_games_for_reconciliation() -> list[dict[str, Any]]:
    rows = _load_clean_generated_rows()
    games: list[dict[str, Any]] = []
    for row in rows:
        games.append(
            {
                "generation_event_id": int(row.get("generation_event_id", 0) or 0),
                "game_index": int(row.get("jogo n°", 0) or 0),
                "numbers": _parse_numbers_text(str(row.get("cartão_final", "") or "")),
                "core_numbers": _parse_numbers_text(str(row.get("núcleo_lei_15", "") or "")),
                "audited_reserve_numbers": _parse_numbers_text(str(row.get("reservas_auditadas", "") or "")),
                "final_card_numbers": _parse_numbers_text(str(row.get("cartão_final", "") or "")),
                "formato_cartao": int(row.get("formato_cartao", 15) or 15),
            }
        )
    return games
