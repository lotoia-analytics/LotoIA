from __future__ import annotations

from typing import Any

from dashboard.institutional_app import (
    _database_snapshot,
    _ensure_official_history_seeded,
    _live_institutional_snapshot,
    _render_analytical_page,
    _render_clean_law15_generation_page,
)


def get_clean_snapshot() -> dict[str, Any]:
    return _live_institutional_snapshot(_database_snapshot())


__all__ = [
    "get_clean_snapshot",
    "_database_snapshot",
    "_ensure_official_history_seeded",
    "_live_institutional_snapshot",
    "_render_analytical_page",
    "_render_clean_law15_generation_page",
]
