from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.public.persistence import ReconciliationRepository


@dataclass(frozen=True)
class ReconciledGame:
    game_index: int
    numbers: list[int]
    hits: int
    matched_numbers: list[int]
    prize_status: str
    prize_tier: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_index": self.game_index,
            "numbers": self.numbers,
            "hits": self.hits,
            "matched_numbers": self.matched_numbers,
            "prize_status": self.prize_status,
            "prize_tier": self.prize_tier,
        }


@dataclass(frozen=True)
class ReconciliationSummary:
    generation_event_id: int
    lead_id: int | None
    contest_id: int
    reconciled_games: list[ReconciledGame]
    prize_count: int
    total_hits: int
    best_hits: int
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_event_id": self.generation_event_id,
            "lead_id": self.lead_id,
            "contest_id": self.contest_id,
            "reconciled_games": [game.to_dict() for game in self.reconciled_games],
            "prize_count": self.prize_count,
            "total_hits": self.total_hits,
            "best_hits": self.best_hits,
            "status": self.status,
        }


class ReconciliationEngine:
    """Compare generated games against official draw results and persist closure."""

    PRIZE_THRESHOLDS = {
        15: "faixa_15",
        14: "faixa_14",
        13: "faixa_13",
        12: "faixa_12",
        11: "faixa_11",
    }

    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path
        self.repository = ReconciliationRepository(db_path)

    def reconcile_generation(
        self,
        *,
        generation_event_id: int,
        contest_id: int,
        generated_games: list[dict[str, Any]],
        official_numbers: list[int],
        lead_id: int | None = None,
        source: str = "official_result",
    ) -> ReconciliationSummary:
        reconciled_games: list[ReconciledGame] = []
        total_hits = 0
        best_hits = 0
        prize_count = 0

        for index, game in enumerate(generated_games, start=1):
            numbers = [int(number) for number in game.get("numbers", [])]
            matched_numbers = sorted(set(numbers) & set(official_numbers))
            hits = len(matched_numbers)
            prize_tier = self.PRIZE_THRESHOLDS.get(hits, "")
            prize_status = "premiado" if prize_tier else "nao_premiado"
            total_hits += hits
            best_hits = max(best_hits, hits)
            if prize_tier:
                prize_count += 1
            reconciled_games.append(
                ReconciledGame(
                    game_index=index,
                    numbers=numbers,
                    hits=hits,
                    matched_numbers=matched_numbers,
                    prize_status=prize_status,
                    prize_tier=prize_tier,
                )
            )

        status = "reconciliado" if reconciled_games else "sem_jogos"
        payload = {
            "source": source,
            "generation_event_id": generation_event_id,
            "contest_id": contest_id,
            "status": status,
            "prize_count": prize_count,
            "total_hits": total_hits,
            "best_hits": best_hits,
        }
        self.repository.insert(
            generation_event_id=generation_event_id,
            lead_id=lead_id,
            contest_id=contest_id,
            source=source,
            status=status,
            prize_count=prize_count,
            total_hits=total_hits,
            best_hits=best_hits,
            payload=payload,
            games=[game.to_dict() | {"context_json": {"official_numbers": official_numbers}} for game in reconciled_games],
        )
        return ReconciliationSummary(
            generation_event_id=generation_event_id,
            lead_id=lead_id,
            contest_id=contest_id,
            reconciled_games=reconciled_games,
            prize_count=prize_count,
            total_hits=total_hits,
            best_hits=best_hits,
            status=status,
        )


def reconcile_smoke_validation(
    *,
    generation_event_id: int,
    lead_id: int | None,
    generated_games: list[dict[str, Any]],
    baseline_numbers: list[int],
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    """Persist an operational smoke reconciliation against a fixed manual baseline."""
    engine = ReconciliationEngine(db_path)
    summary = engine.reconcile_generation(
        generation_event_id=generation_event_id,
        contest_id=0,
        generated_games=generated_games,
        official_numbers=baseline_numbers,
        lead_id=lead_id,
        source="smoke_validation_baseline",
    )
    return {
        **summary.to_dict(),
        "baseline_numbers": sorted(int(number) for number in baseline_numbers),
        "source": "smoke_validation_baseline",
    }
