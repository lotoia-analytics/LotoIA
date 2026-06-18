"""Cobertura Operacional CORE_002 — fonte generation_events + generated_games (M-VIS-DADOS-052)."""

from __future__ import annotations

from typing import Any, Mapping

from lotoia.database.database import DEFAULT_DATABASE_PATH, GeneratedGame, GenerationEvent, get_session
from lotoia.governance.batch_operational_scope import (
    is_generation_event_active_reading,
    resolve_batch_operational_fields,
)
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
OPERATIONAL_GENERATION_ALL_LABEL = "Todos — gerações ativas CORE_002"


def is_all_operational_generations_selection(label: str | None) -> bool:
    return str(label or "").strip() == OPERATIONAL_GENERATION_ALL_LABEL


def build_operational_generation_dropdown_options(
    generations: list[dict[str, Any]],
) -> list[str]:
    if not generations:
        return []
    labels = [str(row.get("dropdown_label") or "") for row in generations]
    return [OPERATIONAL_GENERATION_ALL_LABEL, *labels]


def build_operational_generations_aggregate_summary(
    generations: list[dict[str, Any]],
) -> dict[str, Any]:
    if not generations:
        return {}
    total_games = sum(int(row.get("games_count", 0) or 0) for row in generations)
    card_formats = sorted({int(row.get("card_format", 15) or 15) for row in generations})
    generation_event_ids = [
        int(row.get("generation_event_id", 0) or 0)
        for row in generations
        if int(row.get("generation_event_id", 0) or 0) > 0
    ]
    batch_labels = sorted(
        {
            str(row.get("analysis_batch_label", "") or "").strip()
            for row in generations
            if str(row.get("analysis_batch_label", "") or "").strip()
        }
    )
    return {
        "operational_generation_label": "Todos",
        "generation_event_id": 0,
        "generation_event_ids": generation_event_ids,
        "generation_events_count": len(generations),
        "card_format": card_formats[0] if len(card_formats) == 1 else 0,
        "card_formats": card_formats,
        "card_format_label": ", ".join(f"{size}D" for size in card_formats) if card_formats else "-",
        "games_count": total_games,
        "analysis_batch_label": batch_labels[0] if len(batch_labels) == 1 else "múltiplos",
        "analysis_batch_labels": batch_labels,
        "ml_enabled": any(bool(row.get("ml_enabled", False)) for row in generations),
        "origin": "aggregate",
        "persistence_status": "Persistido",
        "created_at": (
            f"{generations[0].get('created_at', '-')} → {generations[-1].get('created_at', '-')}"
            if len(generations) > 1
            else str(generations[0].get("created_at", "-") or "-")
        ),
    }


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


def load_operational_core_002_generations(
    db_path: Any = DEFAULT_DATABASE_PATH,
    *,
    active_reading_only: bool = True,
) -> list[dict[str, Any]]:
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
            and (not active_reading_only or is_generation_event_active_reading(event))
        ]
        index_map = build_operational_generation_index(event_dicts)

        for event in events:
            batch_label = str(getattr(event, "analysis_batch_label", "") or "")
            if not is_sovereign_core_label(batch_label):
                continue
            if active_reading_only and not is_generation_event_active_reading(event):
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
            event_context = dict(getattr(event, "context_json", {}) or {})
            status_fields = resolve_batch_operational_fields(event_context)
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
                    "operational_status": status_fields["operational_status"],
                    "active_reading_scope": True,
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


def build_active_coverage_scope_summary(
    generations: list[dict[str, Any]],
    *,
    exclusions_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resumo do escopo ativo da Cobertura Estrutural (M-OPS-062-FIX-04)."""
    exclusions = dict(exclusions_summary or {})
    latest = generations[-1] if generations else {}
    latest_ge_id = int(latest.get("generation_event_id", 0) or 0)
    return {
        "mission_id": "M-OPS-062-FIX-04",
        "active_lots_count": len(generations),
        "excluded_lots_count": int(exclusions.get("excluded_batches_count", 0) or 0),
        "excluded_message": str(exclusions.get("message") or ""),
        "latest_generation_event_id": latest_ge_id,
        "latest_operational_generation_label": str(latest.get("operational_generation_label") or "-"),
        "latest_card_format": int(latest.get("card_format", 0) or 0),
        "latest_games_count": int(latest.get("games_count", 0) or 0),
        "latest_operational_status": str(latest.get("operational_status") or "-"),
        "latest_batch_label": str(latest.get("analysis_batch_label") or "-"),
        "latest_created_at": str(latest.get("created_at") or "-"),
        "latest_summary": (
            f"GE {latest_ge_id} — {int(latest.get('card_format', 0) or 0)}D — "
            f"{int(latest.get('games_count', 0) or 0)} jogos — "
            f"{str(latest.get('operational_status') or '-')}"
            if latest_ge_id > 0
            else ""
        ),
    }
