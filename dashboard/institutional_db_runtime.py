"""Fail-safe PostgreSQL runtime helpers — Painel ADM (M-PLAT-050)."""

from __future__ import annotations

from typing import Any

DB_UNAVAILABLE_LABEL = "Indisponível — PostgreSQL não respondeu"


def imported_contests_summary_unavailable(*, error: str = "") -> dict[str, Any]:
    return {
        "count": 0,
        "first_contest": None,
        "last_contest": None,
        "latest_contest": {},
        "window": [],
        "rows": [],
        "source": "imported_contests",
        "status": "UNAVAILABLE",
        "error": error or DB_UNAVAILABLE_LABEL,
    }


def official_history_diagnostics_unavailable(*, error: str = "") -> dict[str, Any]:
    return {
        "total_lotofacil_official_history": 0,
        "contest_number_min": None,
        "contest_number_max": None,
        "concursos_faltantes": [],
        "total_concursos_faltantes": 0,
        "ultimo_concurso_imported_contests": None,
        "ultimo_concurso_lotofacil_official_history": None,
        "status_base_oficial": "INDISPONIVEL",
        "imported_contests_count": 0,
        "imported_contests_window": [],
        "db_status": "UNAVAILABLE",
        "db_error": error or DB_UNAVAILABLE_LABEL,
    }
