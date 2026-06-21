"""Unidade operacional de bateria — M-OPS-289.

Camada read-only/code-only: agrupa generation_events existentes por batch_id
sem alterar schema nem dados.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

MISSION_ID = "M-OPS-289"


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
                "total_games": total_games,
                "games": games,
                "lot_operational_status": ", ".join(sorted(set(statuses))) if statuses else "—",
                "conference_status": ", ".join(sorted(set(statuses))) if statuses else "—",
                "created_at": max(created_values) if created_values else "",
                "battery_scope": "operational_battery",
                "mission_id": MISSION_ID,
            }
        )
    batteries.sort(key=lambda row: max(row.get("generation_event_ids") or [0]), reverse=True)
    return batteries


def format_operational_battery_label(battery: Mapping[str, Any]) -> str:
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
    return {
        "status": "checked" if rows else "waiting_lot",
        "scope": "operational_battery",
        "mission_id": MISSION_ID,
        "generation_event_ids": normalize_generation_event_ids(generation_event_ids),
        "results": all_games,
        "total_games": len(all_games),
        "best_hits": max((int(game.get("hits", 0) or 0) for game in all_games), default=0),
        "total_hits": sum(int(game.get("hits", 0) or 0) for game in all_games),
        "prize_count": sum(1 for game in all_games if int(game.get("hits", 0) or 0) >= 11),
    }
