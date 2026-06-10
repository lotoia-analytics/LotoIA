"""Métricas HB observacionais a partir de reconciliation_runs / reconciliation_games."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Sequence

from sqlalchemy.orm import Session

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    ImportedContest,
    LotofacilOfficialHistory,
    ReconciliationGame,
    ReconciliationRun,
    get_session,
)

SOURCE_POSTGRESQL = "postgresql"
RECONCILIATION_TABLES = "reconciliation_runs / reconciliation_games"


def _extract_int_numbers(raw: str | Sequence[int] | None) -> list[int]:
    if isinstance(raw, (list, tuple)):
        return [int(number) for number in raw if str(number).strip().isdigit() or isinstance(number, int)]
    values: list[int] = []
    for token in str(raw or "").replace(",", " ").split():
        cleaned = str(token).strip()
        if cleaned.isdigit():
            values.append(int(cleaned.lstrip("0") or "0"))
    return values


def resolve_official_numbers_for_contest(session: Session, contest_id: int) -> tuple[list[int], str]:
    """Resolve dezenas oficiais com o mesmo fallback da conferência institucional."""
    selected_contest = int(contest_id or 0)
    if selected_contest <= 0:
        return [], "indisponivel"

    row = (
        session.query(LotofacilOfficialHistory)
        .filter(LotofacilOfficialHistory.contest_number == selected_contest)
        .limit(1)
        .one_or_none()
    )
    if row is not None:
        numbers = _extract_int_numbers(str(getattr(row, "numbers", "") or ""))
        if numbers:
            return numbers, "lotofacil_official_history"

    imported = (
        session.query(ImportedContest)
        .filter(ImportedContest.contest_number == selected_contest)
        .limit(1)
        .one_or_none()
    )
    if imported is not None:
        numbers = _extract_int_numbers(str(getattr(imported, "dezenas", "") or ""))
        if numbers:
            return numbers, "imported_contests"

    return [], "indisponivel"


def resolve_reconciliation_game_hits(
    *,
    hits: int | None,
    matched_numbers: Sequence[int] | None,
    numbers: Sequence[int] | None = None,
    official_numbers: Sequence[int] | None = None,
    prize_tier: str | None = None,
) -> int:
    candidates: list[int] = []
    stored_hits = int(hits or 0)
    if stored_hits > 0:
        candidates.append(stored_hits)
    matched_count = len([int(number) for number in (matched_numbers or [])])
    if matched_count > 0:
        candidates.append(matched_count)
    card_numbers = [int(number) for number in (numbers or [])]
    official = [int(number) for number in (official_numbers or [])]
    if card_numbers and official:
        candidates.append(len(set(card_numbers) & set(official)))
    tier = str(prize_tier or "").strip().lower()
    if tier.startswith("faixa_"):
        try:
            candidates.append(int(tier.split("_", 1)[1]))
        except (ValueError, IndexError):
            pass
    return max(candidates) if candidates else 0


def count_reconciliation_games_with_min_hits(
    games_rows: Sequence[dict[str, Any]],
    *,
    minimum_hits: int,
    official_numbers: Sequence[int] | None = None,
) -> int:
    return sum(
        1
        for row in games_rows
        if resolve_reconciliation_game_hits(
            hits=row.get("hits"),
            matched_numbers=row.get("matched_numbers"),
            numbers=row.get("numbers"),
            official_numbers=official_numbers,
            prize_tier=row.get("prize_tier"),
        )
        >= minimum_hits
    )


def summarize_games_structurally(games: list[Any]) -> dict[str, Any]:
    normalized_games: list[list[int]] = []
    for game in games:
        if isinstance(game, dict):
            raw_numbers = game.get("numbers", [])
        else:
            raw_numbers = game
        numbers = [int(number) for number in raw_numbers or [] if str(number).isdigit() or isinstance(number, int)]
        if numbers:
            normalized_games.append(sorted(numbers))
    if not normalized_games:
        return {
            "games": 0,
            "average_overlap": 0.0,
            "average_unique_numbers": 0.0,
            "dominant_numbers": [],
            "number_frequency": {},
        }
    frequencies: dict[int, int] = {}
    total_unique = 0
    pairwise_overlap = 0
    pair_count = 0
    for numbers in normalized_games:
        total_unique += len(set(numbers))
        for number in numbers:
            frequencies[number] = frequencies.get(number, 0) + 1
    for index, left in enumerate(normalized_games):
        left_set = set(left)
        for right in normalized_games[index + 1 :]:
            pairwise_overlap += len(left_set & set(right))
            pair_count += 1
    dominant_numbers = [
        {"number": number, "frequency": frequency}
        for number, frequency in sorted(frequencies.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]
    return {
        "games": len(normalized_games),
        "average_overlap": round(pairwise_overlap / pair_count, 4) if pair_count else 0.0,
        "average_unique_numbers": round(total_unique / len(normalized_games), 4),
        "dominant_numbers": dominant_numbers,
        "number_frequency": {str(number): frequency for number, frequency in sorted(frequencies.items())},
    }


def compute_structural_entropy_from_dezenas(games: Sequence[Sequence[int]]) -> float:
    frequencies: dict[int, int] = {}
    total = 0
    for numbers in games:
        for number in numbers:
            value = int(number)
            if 1 <= value <= 25:
                frequencies[value] = frequencies.get(value, 0) + 1
                total += 1
    if total <= 0 or not frequencies:
        return 0.0
    entropy = 0.0
    for count in frequencies.values():
        share = count / total
        entropy -= share * math.log2(share)
    max_entropy = math.log2(len(frequencies)) if len(frequencies) > 1 else 1.0
    return round((entropy / max_entropy) if max_entropy else 0.0, 4)


def format_hb_dominant_numbers(dominant_numbers: Sequence[dict[str, Any]], *, limit: int = 5) -> str:
    formatted = [
        f"{int(item['number']):02d}({int(item['frequency'])}x)"
        for item in dominant_numbers[:limit]
        if item.get("number") is not None and item.get("frequency") is not None
    ]
    return " ".join(formatted) or "-"


def empty_hb_metrics_payload() -> dict[str, Any]:
    return {
        "available": False,
        "source": SOURCE_POSTGRESQL,
        "tables": RECONCILIATION_TABLES,
        "reconciliation_run_id": 0,
        "media_acertos": 0.0,
        "jogos_11_mais": 0,
        "jogos_12_mais": 0,
        "entropia_estrutural": 0.0,
        "media_sobreposicao": 0.0,
        "dezenas_dominantes": [],
        "concursos_analisados": 0,
        "jogos_analisados": 0,
        "tamanho_conjunto": 0,
        "prize_count": 0,
        "best_hits": 0,
        "official_source": "indisponivel",
    }


def build_hb_metrics_payload_from_reconciliation(
    *,
    reconciliation_run_id: int,
    contest_id: int,
    games_rows: Sequence[dict[str, Any]],
    official_numbers: Sequence[int] | None = None,
    run_prize_count: int | None = None,
    run_total_hits: int | None = None,
    run_best_hits: int | None = None,
    official_source: str = "indisponivel",
) -> dict[str, Any]:
    games_numbers = [[int(number) for number in (row.get("numbers") or [])] for row in games_rows]
    hits = [
        resolve_reconciliation_game_hits(
            hits=row.get("hits"),
            matched_numbers=row.get("matched_numbers"),
            numbers=row.get("numbers"),
            official_numbers=official_numbers,
            prize_tier=row.get("prize_tier"),
        )
        for row in games_rows
    ]
    contest_ids = {
        int(row.get("contest_id", 0) or 0)
        for row in games_rows
        if int(row.get("contest_id", 0) or 0) > 0
    }
    if not contest_ids and int(contest_id or 0) > 0:
        contest_ids = {int(contest_id)}
    structural = summarize_games_structurally(games_numbers)
    pool_numbers: set[int] = set()
    for numbers in games_numbers:
        pool_numbers.update(numbers)

    counted_11 = count_reconciliation_games_with_min_hits(
        games_rows,
        minimum_hits=11,
        official_numbers=official_numbers,
    )
    counted_12 = count_reconciliation_games_with_min_hits(
        games_rows,
        minimum_hits=12,
        official_numbers=official_numbers,
    )
    persisted_prize_count = int(run_prize_count or 0)
    media_from_games = round(sum(hits) / len(hits), 4) if hits else 0.0
    media_from_run = (
        round(int(run_total_hits or 0) / len(games_rows), 4)
        if games_rows and int(run_total_hits or 0) > 0
        else 0.0
    )
    media_acertos = media_from_games if hits and any(value > 0 for value in hits) else media_from_run

    return {
        "available": bool(games_rows),
        "source": SOURCE_POSTGRESQL,
        "tables": RECONCILIATION_TABLES,
        "reconciliation_run_id": int(reconciliation_run_id or 0),
        "media_acertos": media_acertos,
        "jogos_11_mais": max(persisted_prize_count, counted_11),
        "jogos_12_mais": counted_12,
        "entropia_estrutural": compute_structural_entropy_from_dezenas(games_numbers),
        "media_sobreposicao": float(structural.get("average_overlap", 0.0) or 0.0),
        "dezenas_dominantes": list(structural.get("dominant_numbers", []) or []),
        "concursos_analisados": len(contest_ids),
        "jogos_analisados": len(games_rows),
        "tamanho_conjunto": len(pool_numbers),
        "prize_count": persisted_prize_count,
        "best_hits": int(run_best_hits or 0),
        "official_source": official_source,
    }


def load_hb_metrics_from_reconciliation_db(db_path: Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """Carrega métricas HB da última reconciliation_run persistida (Lei 001)."""
    with get_session(db_path) as session:
        run = (
            session.query(ReconciliationRun)
            .order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
            .first()
        )
        if run is None:
            return empty_hb_metrics_payload()

        contest_id = int(run.contest_id or 0)
        official_numbers, official_source = resolve_official_numbers_for_contest(session, contest_id)
        games_rows = (
            session.query(ReconciliationGame)
            .filter(ReconciliationGame.reconciliation_run_id == run.id)
            .order_by(ReconciliationGame.game_index.asc())
            .all()
        )
        row_payloads = [
            {
                "numbers": list(row.numbers or []),
                "hits": int(row.hits or 0),
                "matched_numbers": list(row.matched_numbers or []),
                "prize_tier": str(row.prize_tier or ""),
                "contest_id": int(row.contest_id or 0),
            }
            for row in games_rows
        ]
        return build_hb_metrics_payload_from_reconciliation(
            reconciliation_run_id=int(run.id or 0),
            contest_id=contest_id,
            games_rows=row_payloads,
            official_numbers=official_numbers,
            run_prize_count=int(run.prize_count or 0),
            run_total_hits=int(run.total_hits or 0),
            run_best_hits=int(run.best_hits or 0),
            official_source=official_source,
        )
