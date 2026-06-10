"""Painéis ML diagnósticos observacionais (PostgreSQL / reconciliation_runs)."""

from __future__ import annotations

from collections import Counter
from typing import Any, Sequence

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    LotofacilOfficialHistory,
    ReconciliationGame,
    ReconciliationRun,
    get_session,
)
from lotoia.observability.observational_leftover import ML_ROLE_DIAGNOSTIC_ONLY

NUCLEO_LEI15_15D_CONGELADO: frozenset[int] = frozenset(
    {1, 2, 3, 4, 9, 10, 11, 12, 13, 18, 20, 22, 23, 24, 25}
)
SIDE_LEAK_ALERT_THRESHOLD = 0.50
SOURCE_POSTGRESQL = "postgresql"
RECONCILIATION_TABLES = "reconciliation_runs / reconciliation_games"
CANDIDATE_FLAG_13_14 = "candidata_conversao_13_14"
CANDIDATE_FLAG_14_15 = "candidata_conversao_14_15"
ALERT_SIDE_LEAK = "vazamento_lateral_detectado"


def _parse_dezenas(values: Sequence[int | str] | str | None) -> list[int]:
    if not values:
        return []
    if isinstance(values, str):
        raw_items = values.replace(",", " ").replace(";", " ").split()
    else:
        raw_items = list(values)
    numbers: list[int] = []
    for item in raw_items:
        try:
            number = int(str(item).strip().lstrip("+"))
        except (TypeError, ValueError):
            continue
        if 1 <= number <= 25:
            numbers.append(number)
    return sorted(set(numbers))


def _load_official_numbers(session: Any, contest_id: int) -> list[int]:
    if contest_id <= 0:
        return []
    row = (
        session.query(LotofacilOfficialHistory)
        .filter(LotofacilOfficialHistory.contest_number == int(contest_id))
        .limit(1)
        .one_or_none()
    )
    if row is None:
        return []
    numbers = _parse_dezenas(getattr(row, "numbers", "") or "")
    return numbers if len(numbers) == 15 else []


def _empty_context() -> dict[str, Any]:
    return {
        "available": False,
        "source": SOURCE_POSTGRESQL,
        "tables": RECONCILIATION_TABLES,
        "reconciliation_run_id": 0,
        "contest_id": 0,
        "resultado_oficial": [],
        "games": [],
        "ml_role": ML_ROLE_DIAGNOSTIC_ONLY,
        "generation_command": False,
        "recalibration_command": False,
    }


def load_latest_reconciliation_diagnostic_context(
    db_path: str = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    """Carrega última reconciliation_run e jogos do PostgreSQL (Lei 001)."""
    with get_session(db_path) as session:
        run = (
            session.query(ReconciliationRun)
            .order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
            .first()
        )
        if run is None:
            return _empty_context()
        contest_id = int(getattr(run, "contest_id", 0) or 0)
        games_rows = (
            session.query(ReconciliationGame)
            .filter(ReconciliationGame.reconciliation_run_id == run.id)
            .order_by(ReconciliationGame.game_index.asc())
            .all()
        )
        resultado_oficial = _load_official_numbers(session, contest_id)
        games = [
            {
                "game_index": int(row.game_index or 0),
                "numbers": [int(number) for number in (row.numbers or [])],
                "hits": int(row.hits or 0),
                "matched_numbers": [int(number) for number in (row.matched_numbers or [])],
                "contest_id": int(row.contest_id or 0),
            }
            for row in games_rows
        ]
        return {
            "available": bool(games and resultado_oficial),
            "source": SOURCE_POSTGRESQL,
            "tables": RECONCILIATION_TABLES,
            "reconciliation_run_id": int(run.id or 0),
            "contest_id": contest_id,
            "resultado_oficial": resultado_oficial,
            "games": games,
            "ml_role": ML_ROLE_DIAGNOSTIC_ONLY,
            "generation_command": False,
            "recalibration_command": False,
        }


def build_side_leak_panel_payload(context: dict[str, Any]) -> dict[str, Any]:
    games = list(context.get("games") or [])
    nucleo = set(NUCLEO_LEI15_15D_CONGELADO)
    total_games = len(games)
    dezena_game_counts: Counter[int] = Counter()
    for game in games:
        cartao = set(int(number) for number in (game.get("numbers") or []))
        for dezena in sorted(cartao - nucleo):
            dezena_game_counts[dezena] += 1
    rows: list[dict[str, Any]] = []
    alert_dezenas: list[int] = []
    for dezena, frequencia in sorted(dezena_game_counts.items()):
        percentual = round((frequencia / total_games) * 100.0, 2) if total_games else 0.0
        rows.append(
            {
                "dezena": f"{dezena:02d}",
                "frequencia_vazamento": int(frequencia),
                "percentual_vazamento": percentual,
            }
        )
        if total_games and (frequencia / total_games) > SIDE_LEAK_ALERT_THRESHOLD:
            alert_dezenas.append(int(dezena))
    return {
        "available": bool(context.get("available")),
        "source": SOURCE_POSTGRESQL,
        "tables": RECONCILIATION_TABLES,
        "reconciliation_run_id": int(context.get("reconciliation_run_id", 0) or 0),
        "ml_role": ML_ROLE_DIAGNOSTIC_ONLY,
        "generation_command": False,
        "recalibration_command": False,
        "rows": rows,
        "total_games": total_games,
        "alert": ALERT_SIDE_LEAK if alert_dezenas else None,
        "alert_dezenas": [f"{dezena:02d}" for dezena in alert_dezenas],
        "nucleo_lei15_15d": sorted(nucleo),
    }


def _build_evolution_panel_payload(
    context: dict[str, Any],
    *,
    target_hits: int,
    candidate_flag: str,
) -> dict[str, Any]:
    games = [game for game in (context.get("games") or []) if int(game.get("hits", 0) or 0) == target_hits]
    resultado_oficial = set(int(number) for number in (context.get("resultado_oficial") or []))
    dezena_counts: Counter[int] = Counter()
    for game in games:
        cartao = set(int(number) for number in (game.get("numbers") or []))
        for dezena in sorted(resultado_oficial - cartao):
            dezena_counts[dezena] += 1
    total_games = len(games)
    rows: list[dict[str, Any]] = []
    for dezena, frequencia in dezena_counts.most_common():
        percentual = round((frequencia / total_games) * 100.0, 2) if total_games else 0.0
        rows.append(
            {
                "dezena_faltante": f"{dezena:02d}",
                "frequencia": int(frequencia),
                "percentual": percentual,
            }
        )
    top_row = rows[0] if rows else None
    return {
        "available": bool(context.get("available") and total_games > 0),
        "source": SOURCE_POSTGRESQL,
        "tables": RECONCILIATION_TABLES,
        "reconciliation_run_id": int(context.get("reconciliation_run_id", 0) or 0),
        "ml_role": ML_ROLE_DIAGNOSTIC_ONLY,
        "generation_command": False,
        "recalibration_command": False,
        "target_hits": target_hits,
        "games_analyzed": total_games,
        "rows": rows,
        "candidate_flag": candidate_flag if top_row else None,
        "candidata_conversao": top_row["dezena_faltante"] if top_row else None,
    }


def build_evolution_13_14_panel_payload(context: dict[str, Any]) -> dict[str, Any]:
    return _build_evolution_panel_payload(
        context,
        target_hits=13,
        candidate_flag=CANDIDATE_FLAG_13_14,
    )


def build_evolution_14_15_panel_payload(context: dict[str, Any]) -> dict[str, Any]:
    return _build_evolution_panel_payload(
        context,
        target_hits=14,
        candidate_flag=CANDIDATE_FLAG_14_15,
    )
