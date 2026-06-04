from __future__ import annotations

from typing import Any

from dashboard.institutional_app import (
    _database_snapshot,
    _ensure_official_history_seeded,
    _ensure_analytical_games_schema,
    _expand_generation_games_for_format,
    _load_accumulated_analytical_rows,
    _live_institutional_snapshot,
    _persist_clean_law15_generation_history,
    _run_clean_law15_generation,
)


def get_clean_snapshot() -> dict[str, Any]:
    return _live_institutional_snapshot(_database_snapshot())


def run_clean_generation(requested_count: int, selected_card_format: int) -> dict[str, Any]:
    result = _run_clean_law15_generation(requested_count=requested_count)
    result["selected_card_format"] = int(selected_card_format)
    result["card_format_label"] = {
        15: "15 dezenas — Núcleo Lei 15",
        17: "17 dezenas — Lei 15 + 2 reservas auditadas",
        18: "18 dezenas — Lei 15 + 3 reservas auditadas",
    }.get(int(selected_card_format), f"{int(selected_card_format)} dezenas")
    result["display_games"] = _expand_generation_games_for_format(result.get("games") or [], selected_card_format)
    result["validation_status_lei_17"] = "VALIDA_12_PLUS" if int(selected_card_format) in (17, 18) else "N_A"
    result["validation_status_lei_18"] = "VALIDA_13_PLUS" if int(selected_card_format) == 18 else "N_A"
    snapshot = _persist_clean_law15_generation_history(result=result, selected_card_format=selected_card_format)
    if snapshot:
        result["clean_history_snapshot"] = snapshot
    return result


__all__ = [
    "get_clean_snapshot",
    "run_clean_generation",
    "_database_snapshot",
    "_ensure_official_history_seeded",
    "_ensure_analytical_games_schema",
    "_expand_generation_games_for_format",
    "_load_accumulated_analytical_rows",
    "_live_institutional_snapshot",
]
