"""Agrupamento operacional por bateria — conferência e leitura CORE_002 (M-OPS-289A)."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

MISSION_ID = "M-OPS-289A"
OPERATIONAL_BATTERY_ALL_ID = "ALL"
OPERATIONAL_BATTERY_ALL_LABEL = "Todos — baterias operacionais CORE_002"


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _resolve_group_batch_id(group: Mapping[str, Any]) -> str:
    batch_id = str(group.get("batch_id") or "").strip()
    if batch_id:
        return batch_id
    ge_id = _safe_int(group.get("generation_event_id"))
    return f"GE-{ge_id}" if ge_id > 0 else "unknown-batch"


def _resolve_group_status(group: Mapping[str, Any]) -> str:
    return str(
        group.get("lot_operational_status")
        or group.get("conference_status")
        or group.get("operational_status")
        or "—"
    ).strip() or "—"


def build_operational_battery_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Agrupa lotes persistidos por batch_id operacional."""
    buckets: dict[str, list[dict[str, Any]]] = {}
    for raw_group in groups:
        group = dict(raw_group or {})
        ge_id = _safe_int(group.get("generation_event_id"))
        if ge_id <= 0:
            continue
        batch_id = _resolve_group_batch_id(group)
        buckets.setdefault(batch_id, []).append(group)

    batteries: list[dict[str, Any]] = []
    ordered_batch_ids = sorted(
        buckets,
        key=lambda batch_id: max(
            _safe_int(row.get("generation_event_id")) for row in buckets[batch_id]
        ),
        reverse=True,
    )
    for index, batch_id in enumerate(ordered_batch_ids, start=1):
        batch_groups = sorted(
            buckets[batch_id],
            key=lambda row: _safe_int(row.get("generation_event_id")),
        )
        generation_event_ids = [
            _safe_int(row.get("generation_event_id"))
            for row in batch_groups
            if _safe_int(row.get("generation_event_id")) > 0
        ]
        total_games = sum(_safe_int(row.get("total_games")) for row in batch_groups)
        status_counter = Counter(_resolve_group_status(row) for row in batch_groups)
        lot_status = status_counter.most_common(1)[0][0] if status_counter else "—"
        created_values = [str(row.get("created_at") or "").strip() for row in batch_groups if row.get("created_at")]
        batteries.append(
            {
                "battery_id": f"BAT-{index:03d}",
                "batch_id": batch_id,
                "generation_event_ids": generation_event_ids,
                "groups": batch_groups,
                "generations_count": len(generation_event_ids),
                "total_games": int(total_games),
                "lot_operational_status": lot_status,
                "created_at": created_values[-1] if created_values else "",
                "created_at_range": (
                    f"{created_values[0]} → {created_values[-1]}"
                    if len(created_values) > 1
                    else (created_values[0] if created_values else "")
                ),
            }
        )
    return batteries


def build_operational_battery_aggregate(battery_groups: list[dict[str, Any]]) -> dict[str, Any]:
    """Consolida todas as baterias ativas para leitura agregada (Todos)."""
    if not battery_groups:
        return {}
    generation_event_ids = [
        ge_id
        for battery in battery_groups
        for ge_id in list(battery.get("generation_event_ids") or [])
        if _safe_int(ge_id) > 0
    ]
    total_games = sum(_safe_int(battery.get("total_games")) for battery in battery_groups)
    batch_ids = sorted(
        {
            str(battery.get("batch_id") or "").strip()
            for battery in battery_groups
            if str(battery.get("batch_id") or "").strip()
        }
    )
    return {
        "battery_id": OPERATIONAL_BATTERY_ALL_ID,
        "batch_id": batch_ids[0] if len(batch_ids) == 1 else "multiple",
        "batch_ids": batch_ids,
        "generation_event_ids": generation_event_ids,
        "groups": [dict(group) for battery in battery_groups for group in list(battery.get("groups") or [])],
        "generations_count": len(generation_event_ids),
        "total_games": int(total_games),
        "lot_operational_status": OPERATIONAL_BATTERY_ALL_LABEL,
        "created_at": str(battery_groups[0].get("created_at") or ""),
        "is_aggregate": True,
    }


def format_operational_battery_label(battery: Mapping[str, Any]) -> str:
    battery_id = str(battery.get("battery_id") or "BAT-000")
    if battery_id == OPERATIONAL_BATTERY_ALL_ID:
        return OPERATIONAL_BATTERY_ALL_LABEL
    generations_count = _safe_int(battery.get("generations_count"))
    total_games = _safe_int(battery.get("total_games"))
    status = _resolve_group_status(battery)
    return (
        f"Bateria {battery_id} | {generations_count} gerações | "
        f"{total_games} jogos | {status}"
    )


def merge_battery_conference_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Consolida conferências de múltiplas gerações da mesma bateria."""
    generation_results = [dict(item) for item in results if isinstance(item, Mapping)]
    generation_event_ids = [
        _safe_int(item.get("generation_event_id"))
        for item in generation_results
        if _safe_int(item.get("generation_event_id")) > 0
    ]
    flat_results: list[dict[str, Any]] = []
    total_hits = 0
    prize_count = 0
    best_hits = 0
    for item in generation_results:
        rows = [dict(row) for row in list(item.get("results") or []) if isinstance(row, Mapping)]
        flat_results.extend(rows)
        total_hits += _safe_int(item.get("total_hits"))
        prize_count += _safe_int(item.get("prize_count"))
        best_hits = max(best_hits, _safe_int(item.get("best_hits")))
    contest_number = _safe_int(generation_results[0].get("contest_number")) if generation_results else 0
    contest_date = str(generation_results[0].get("contest_date") or "") if generation_results else ""
    batch_id = str(generation_results[0].get("batch_id") or "") if generation_results else ""
    total_games_checked = sum(_safe_int(item.get("total_games")) for item in generation_results)
    return {
        "scope": "operational_battery",
        "battery_id": str(generation_results[0].get("battery_id") or "") if generation_results else "",
        "batch_id": batch_id,
        "generation_event_ids": generation_event_ids,
        "generation_results": generation_results,
        "results": flat_results,
        "best_hits": int(best_hits),
        "total_hits": int(total_hits),
        "prize_count": int(prize_count),
        "total_games_checked": int(total_games_checked),
        "contest_number": int(contest_number),
        "contest_date": contest_date,
        "generations_conferred": len(generation_results),
    }
