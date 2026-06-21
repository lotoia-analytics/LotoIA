"""Unidade operacional de bateria — M-OPS-289 / M-OPS-289A.

Camada read-only/code-only: agrupa generation_events existentes por batch_id
sem alterar schema nem dados.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

MISSION_ID = "M-OPS-289"
BATTERY_CONFERENCE_MISSION_ID = "M-OPS-289A"
OPERATIONAL_BATTERY_ALL_ID = "ALL"
OPERATIONAL_BATTERY_ALL_LABEL = "Todos — baterias operacionais CORE_002"


def normalize_generation_event_ids(values: Sequence[Any] | None) -> list[int]:
    ids: list[int] = []
    seen: set[int] = set()
    for value in list(values or []):
        try:
            ge_id = int(value)
        except (TypeError, ValueError):
            continue
        if ge_id <= 0 or ge_id in seen:
            continue
        ids.append(ge_id)
        seen.add(ge_id)
    return ids


def generation_ids_from_group(group: Mapping[str, Any]) -> list[int]:
    explicit = normalize_generation_event_ids(group.get("generation_event_ids"))
    if explicit:
        return explicit
    return normalize_generation_event_ids([group.get("generation_event_id")])


def resolve_operational_battery_id(group: Mapping[str, Any]) -> str:
    for key in ("battery_id", "operational_battery_id", "batch_id"):
        value = str(group.get(key) or "").strip()
        if value and value not in {"-", "None", "null"}:
            return value
    ge_ids = generation_ids_from_group(group)
    return f"GE:{ge_ids[0]}" if ge_ids else "unresolved"


def build_operational_battery_groups(groups: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group in groups:
        payload = dict(group or {})
        if not generation_ids_from_group(payload):
            continue
        buckets[resolve_operational_battery_id(payload)].append(payload)

    batteries: list[dict[str, Any]] = []
    for battery_id, rows in buckets.items():
        generation_event_ids: list[int] = []
        games: list[dict[str, Any]] = []
        statuses: list[str] = []
        created_values: list[str] = []
        for row in rows:
            generation_event_ids.extend(generation_ids_from_group(row))
            games.extend(list(row.get("games") or []))
            status = str(row.get("lot_operational_status") or row.get("conference_status") or "").strip()
            if status:
                statuses.append(status)
            created = str(row.get("created_at") or "").strip()
            if created:
                created_values.append(created)
        ge_ids = normalize_generation_event_ids(generation_event_ids)
        if not ge_ids:
            continue
        total_games = sum(int(row.get("total_games", 0) or len(row.get("games") or [])) for row in rows)
        batteries.append(
            {
                "battery_id": battery_id,
                "batch_id": battery_id,
                "generation_event_id": ge_ids[-1],
                "generation_event_ids": ge_ids,
                "total_generation_events": len(ge_ids),
                "generations_count": len(ge_ids),
                "total_games": total_games,
                "games": games,
                "groups": [dict(row) for row in rows],
                "lot_operational_status": ", ".join(sorted(set(statuses))) if statuses else "—",
                "conference_status": ", ".join(sorted(set(statuses))) if statuses else "—",
                "created_at": max(created_values) if created_values else "",
                "battery_scope": "operational_battery",
                "mission_id": MISSION_ID,
            }
        )
    batteries.sort(key=lambda row: max(row.get("generation_event_ids") or [0]), reverse=True)
    return batteries


def build_operational_battery_aggregate(battery_groups: list[dict[str, Any]]) -> dict[str, Any]:
    """Consolida todas as baterias ativas para leitura agregada (Todos)."""
    if not battery_groups:
        return {}
    generation_event_ids = normalize_generation_event_ids(
        [
            ge_id
            for battery in battery_groups
            for ge_id in list(battery.get("generation_event_ids") or [])
        ]
    )
    total_games = sum(int(battery.get("total_games", 0) or 0) for battery in battery_groups)
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
        "total_generation_events": len(generation_event_ids),
        "total_games": int(total_games),
        "lot_operational_status": OPERATIONAL_BATTERY_ALL_LABEL,
        "created_at": str(battery_groups[0].get("created_at") or ""),
        "is_aggregate": True,
        "battery_scope": "operational_battery",
        "mission_id": BATTERY_CONFERENCE_MISSION_ID,
    }


def format_operational_battery_label(battery: Mapping[str, Any]) -> str:
    if str(battery.get("battery_id") or "") == OPERATIONAL_BATTERY_ALL_ID:
        return OPERATIONAL_BATTERY_ALL_LABEL
    ge_ids = generation_ids_from_group(battery)
    battery_id = str(battery.get("battery_id") or battery.get("batch_id") or "—")
    total_games = int(battery.get("total_games", 0) or len(battery.get("games") or []))
    status = str(battery.get("lot_operational_status") or battery.get("conference_status") or "—")
    created = str(battery.get("created_at") or "")[:10]
    return f"Bateria {battery_id} — {len(ge_ids)} gerações — {total_games} jogos — {status} — {created}"


def merge_battery_conference_results(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in results if isinstance(row, Mapping)]
    all_games: list[dict[str, Any]] = []
    generation_event_ids: list[int] = []
    for row in rows:
        all_games.extend(list(row.get("results") or []))
        generation_event_ids.extend(generation_ids_from_group(row))
        if row.get("generation_event_id"):
            generation_event_ids.append(row.get("generation_event_id"))
    normalized_ids = normalize_generation_event_ids(generation_event_ids)
    total_games_checked = sum(int(row.get("total_games", 0) or 0) for row in rows)
    return {
        "status": "checked" if rows else "waiting_lot",
        "scope": "operational_battery",
        "mission_id": MISSION_ID,
        "battery_id": str(rows[0].get("battery_id") or "") if rows else "",
        "batch_id": str(rows[0].get("batch_id") or "") if rows else "",
        "generation_event_ids": normalized_ids,
        "generation_results": rows,
        "results": all_games,
        "total_games": len(all_games),
        "total_games_checked": int(total_games_checked or len(all_games)),
        "best_hits": max((int(game.get("hits", 0) or 0) for game in all_games), default=0),
        "total_hits": sum(int(game.get("hits", 0) or 0) for game in all_games),
        "prize_count": sum(1 for game in all_games if int(game.get("hits", 0) or 0) >= 11),
        "generations_conferred": len(rows),
        "contest_number": int(rows[0].get("contest_number", 0) or 0) if rows else 0,
        "contest_date": str(rows[0].get("contest_date") or "") if rows else "",
    }
