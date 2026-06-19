"""Runtime — lotes conferidos vs fila analítica (M-OPS-066)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from lotoia.database.database import GenerationEvent, get_session

MISSION_ID = "M-OPS-066"
CONFERENCE_STATUS_CHECKED = "checked"
SESSION_SIMULATION_SELECTED_GE = "institutional_simulation_selected_generation_event_id"


def is_lot_conferred(
    *,
    context_json: Mapping[str, Any] | None = None,
    reconciliation: Mapping[str, Any] | None = None,
) -> bool:
    """Lote conferido quando há reconciliação persistida ou marca soberana no context_json."""
    context = dict(context_json or {})
    status = str(context.get("conference_status") or "").strip().lower()
    if status == CONFERENCE_STATUS_CHECKED:
        return True
    reconciliation_payload = dict(reconciliation or {})
    if int(reconciliation_payload.get("id", 0) or 0) > 0:
        return True
    if int(reconciliation_payload.get("games_count", 0) or 0) > 0:
        return True
    if reconciliation_payload.get("games_by_index"):
        return True
    return False


def build_checked_result_summary(
    *,
    comparison: Mapping[str, Any],
    hit_distribution: Mapping[int, int] | None = None,
    batch_hit_decomposition: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resumo persistido da conferência oficial — acertos por faixa e totais."""
    decomposition = dict(batch_hit_decomposition or {})
    distribution = dict(hit_distribution or {})
    results = list(comparison.get("results") or [])
    return {
        "best_hits": int(comparison.get("best_hits", 0) or 0),
        "total_hits": int(comparison.get("total_hits", 0) or 0),
        "prize_count": int(comparison.get("prize_count", 0) or 0),
        "contest_number": int(comparison.get("contest_number", 0) or 0),
        "games_count": len(results),
        "hit_distribution": {str(key): int(value) for key, value in distribution.items()},
        "count_11_exact": int(decomposition.get("count_11_exact", 0) or 0),
        "count_12_exact": int(decomposition.get("count_12_exact", 0) or 0),
        "count_13_exact": int(decomposition.get("count_13_exact", 0) or 0),
        "count_14_exact": int(decomposition.get("count_14_exact", 0) or 0),
        "count_15_exact": int(decomposition.get("count_15_exact", 0) or 0),
        "count_11_plus": int(decomposition.get("count_11_plus", 0) or 0),
    }


def merge_conference_checked_context(
    context_json: Mapping[str, Any],
    *,
    checked_at: str,
    checked_against_contest: int,
    checked_result_summary: Mapping[str, Any],
) -> dict[str, Any]:
    merged = dict(context_json or {})
    merged["checked_at"] = str(checked_at or "")
    merged["checked_against_contest"] = int(checked_against_contest or 0)
    merged["checked_result_summary"] = dict(checked_result_summary or {})
    merged["conference_status"] = CONFERENCE_STATUS_CHECKED
    return merged


def persist_generation_event_conference_mark(
    *,
    db_path: str | Path,
    generation_event_id: int,
    checked_against_contest: int,
    checked_result_summary: Mapping[str, Any],
    checked_at: str | None = None,
) -> bool:
    """Marca lote como conferido no PostgreSQL (context_json soberano)."""
    event_id = int(generation_event_id or 0)
    if event_id <= 0:
        return False
    timestamp = str(checked_at or datetime.now(UTC).isoformat())
    with get_session(db_path) as session:
        event = session.query(GenerationEvent).filter(GenerationEvent.id == event_id).first()
        if event is None:
            return False
        context = dict(getattr(event, "context_json", {}) or {})
        event.context_json = merge_conference_checked_context(
            context,
            checked_at=timestamp,
            checked_against_contest=int(checked_against_contest or 0),
            checked_result_summary=checked_result_summary,
        )
        session.commit()
    return True


def summarize_conferred_lot(group: Mapping[str, Any]) -> dict[str, Any]:
    """Normaliza metadados de lote conferido para Simular Resultados."""
    context = dict(group.get("context_json") or {})
    reconciliation = dict(group.get("reconciliation") or {})
    checked_summary = dict(context.get("checked_result_summary") or {})
    contest_number = int(
        context.get("checked_against_contest")
        or reconciliation.get("contest_id", 0)
        or checked_summary.get("contest_number", 0)
        or 0
    )
    checked_at = str(context.get("checked_at") or reconciliation.get("created_at") or "")
    hit_distribution = dict(reconciliation.get("hit_distribution") or checked_summary.get("hit_distribution") or {})
    return {
        "generation_event_id": int(group.get("generation_event_id", 0) or 0),
        "total_games": int(group.get("total_games", 0) or 0),
        "checked_against_contest": contest_number,
        "checked_at": checked_at,
        "checked_result_summary": checked_summary,
        "conference_status": CONFERENCE_STATUS_CHECKED,
        "status_label": "conferido",
        "best_hits": int(checked_summary.get("best_hits") or reconciliation.get("best_hits", 0) or 0),
        "prize_count": int(checked_summary.get("prize_count") or reconciliation.get("prize_count", 0) or 0),
        "hit_distribution": hit_distribution,
        "batch_id": str(group.get("batch_id", "") or ""),
        "created_at": str(group.get("created_at", "") or ""),
        "games": list(group.get("games") or []),
        "reconciliation": reconciliation,
        "context_json": context,
    }


def filter_conferred_groups(groups: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        summarize_conferred_lot(group)
        for group in groups
        if is_lot_conferred(
            context_json=group.get("context_json"),
            reconciliation=group.get("reconciliation"),
        )
    ]


def filter_unconferred_groups(groups: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        dict(group)
        for group in groups
        if not is_lot_conferred(
            context_json=group.get("context_json"),
            reconciliation=group.get("reconciliation"),
        )
    ]


def format_conferred_lot_label(lot: Mapping[str, Any]) -> str:
    ge_id = int(lot.get("generation_event_id", 0) or 0)
    games = int(lot.get("total_games", 0) or 0)
    contest = int(lot.get("checked_against_contest", 0) or 0)
    checked_at = str(lot.get("checked_at") or "")[:10]
    best_hits = int(lot.get("best_hits", 0) or 0)
    return f"GE {ge_id} — {games} jogos — conferido × {contest} — best {best_hits} — {checked_at}"


def conferred_lots_runtime_trace() -> dict[str, Any]:
    return {
        "mission_id": MISSION_ID,
        "conference_status_checked": CONFERENCE_STATUS_CHECKED,
        "postgresql_sovereign": True,
        "simulation_generates": False,
    }
