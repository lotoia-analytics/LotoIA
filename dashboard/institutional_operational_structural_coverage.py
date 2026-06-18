"""Cobertura Operacional CORE_002 — fonte generation_events + generated_games (M-VIS-DADOS-052)."""

from __future__ import annotations

from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH, GeneratedGame, GenerationEvent, get_session
from lotoia.governance.lei15_core_002_sovereign import core_002_batch_label_game_size, is_sovereign_core_label

from dashboard.institutional_operational_generation import (
    build_operational_generation_index,
    format_operational_generation_number,
)

MISSION_ID = "M-VIS-DADOS-052"
OPERATIONAL_COVERAGE_TITLE = "Cobertura Operacional CORE_002"
OPERATIONAL_SOURCE_CAPTION = "Fonte: PostgreSQL / generation_events / generated_games"
HISTORICAL_SECTION_TITLE = "Histórico / evidência legada — não é geração operacional atual"
HISTORICAL_SOURCE_CAPTION = "Reconciliação histórica — reconciliation_runs / reconciliation_games"
EMPTY_OPERATIONAL_MESSAGE = (
    "Nenhuma geração operacional CORE_002 persistida encontrada. "
    "Gere um lote no Gerador ADM CORE_002 para habilitar a Cobertura Estrutural operacional."
)


def _resolve_card_format_from_event(event: GenerationEvent, game_rows: list[GeneratedGame]) -> int:
    label_size = core_002_batch_label_game_size(str(getattr(event, "analysis_batch_label", "") or ""))
    if label_size is not None:
        return int(label_size)
    if game_rows:
        context = dict(getattr(game_rows[0], "context_json", {}) or {})
        for key in ("selected_card_format", "card_format", "format_cartao", "formato_cartao", "quantidade_final"):
            raw = context.get(key)
            if raw is not None and str(raw).strip().isdigit():
                return int(raw)
        numbers = list(getattr(game_rows[0], "numbers", []) or [])
        final_card = list(context.get("final_card_numbers") or numbers or [])
        if final_card:
            return len(final_card)
        if numbers:
            return len(numbers)
    return 15


def load_operational_core_002_generations(db_path: Any = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """Lista gerações operacionais CORE_002 persistidas (generation_events + generated_games)."""
    generations: list[dict[str, Any]] = []
    with get_session(db_path) as session:
        events = (
            session.query(GenerationEvent)
            .order_by(GenerationEvent.created_at.asc(), GenerationEvent.id.asc())
            .all()
        )
        event_dicts = [
            {
                "id": int(event.id or 0),
                "generation_event_id": int(event.id or 0),
                "analysis_batch_label": str(getattr(event, "analysis_batch_label", "") or ""),
                "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else "",
            }
            for event in events
            if is_sovereign_core_label(str(getattr(event, "analysis_batch_label", "") or ""))
        ]
        index_map = build_operational_generation_index(event_dicts)

        for event in events:
            batch_label = str(getattr(event, "analysis_batch_label", "") or "")
            if not is_sovereign_core_label(batch_label):
                continue
            ge_id = int(event.id or 0)
            if ge_id <= 0:
                continue
            game_rows = (
                session.query(GeneratedGame)
                .filter(GeneratedGame.generation_event_id == ge_id)
                .order_by(GeneratedGame.game_index.asc())
                .all()
            )
            if not game_rows:
                continue
            card_format = _resolve_card_format_from_event(event, game_rows)
            op_index = int(index_map.get(ge_id, 0) or 0)
            op_label = format_operational_generation_number(op_index)
            games_count = len(game_rows)
            generations.append(
                {
                    "generation_event_id": ge_id,
                    "operational_generation_index": op_index,
                    "operational_generation_label": op_label,
                    "analysis_batch_label": batch_label,
                    "card_format": card_format,
                    "games_count": games_count,
                    "ml_enabled": bool(getattr(event, "ml_enabled", False)),
                    "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else "",
                    "origin": str(getattr(event, "strategy", "") or "institutional"),
                    "persistence_status": "Persistido",
                    "dropdown_label": (
                        f"Geração {op_label} — GE {ge_id} — {card_format}D — CORE_002 — {games_count} jogos"
                    ),
                }
            )
    return generations


def resolve_operational_generation_by_id(
    generations: list[dict[str, Any]],
    generation_event_id: int | None,
) -> dict[str, Any] | None:
    selected = int(generation_event_id or 0)
    if selected <= 0:
        return generations[-1] if generations else None
    for row in generations:
        if int(row.get("generation_event_id", 0) or 0) == selected:
            return row
    return None
