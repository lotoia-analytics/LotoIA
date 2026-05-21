from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text

from lotoia.database.database import DEFAULT_DATABASE_PATH, GeneratedGame, ReconciliationGame, get_session
from lotoia.public.persistence import ReconciliationRepository


PRIZE_PRIORITY = {
    "faixa_15": 5,
    "faixa_14": 4,
    "faixa_13": 3,
    "faixa_12": 2,
    "faixa_11": 1,
}


@dataclass(frozen=True)
class PrizeDetection:
    game_index: int
    hits: int
    prize_status: str
    prize_tier: str
    matched_numbers: list[int]


@dataclass(frozen=True)
class RetentionDecision:
    game_index: int
    keep: bool
    reason: str


@dataclass(frozen=True)
class OperationalDashboardSummary:
    total_runs: int
    total_games: int
    prize_count: int
    best_hits: int
    latest_contest: int | None
    status: str
    prize_tiers: dict[str, int]
    post_draw_notes: list[str]


@dataclass(frozen=True)
class OperationalClosureReport:
    created_at: datetime
    contest_id: int
    prize_count: int
    retained_games: int
    removed_games: int
    telemetry: dict[str, Any]
    dashboard: OperationalDashboardSummary
    detections: list[PrizeDetection]
    decisions: list[RetentionDecision]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "contest_id": self.contest_id,
            "prize_count": self.prize_count,
            "retained_games": self.retained_games,
            "removed_games": self.removed_games,
            "telemetry": self.telemetry,
            "dashboard": asdict(self.dashboard),
            "detections": [asdict(item) for item in self.detections],
            "decisions": [asdict(item) for item in self.decisions],
        }


class PrizeDetectionEngine:
    def detect(self, games: list[dict[str, Any]]) -> list[PrizeDetection]:
        detections: list[PrizeDetection] = []
        for index, game in enumerate(games, start=1):
            hits = int(game.get("hits", 0))
            matched_numbers = [int(number) for number in game.get("matched_numbers", [])]
            prize_tier = self._tier_for_hits(hits)
            detections.append(
                PrizeDetection(
                    game_index=index,
                    hits=hits,
                    prize_status="premiado" if prize_tier else "nao_premiado",
                    prize_tier=prize_tier,
                    matched_numbers=matched_numbers,
                )
            )
        return detections

    @staticmethod
    def _tier_for_hits(hits: int) -> str:
        return {
            15: "faixa_15",
            14: "faixa_14",
            13: "faixa_13",
            12: "faixa_12",
            11: "faixa_11",
        }.get(hits, "")


class RetentionPolicyEngine:
    def decide(self, detections: list[PrizeDetection], *, strategic_games: set[int] | None = None) -> list[RetentionDecision]:
        strategic_games = strategic_games or set()
        decisions: list[RetentionDecision] = []
        for detection in detections:
            keep = detection.prize_status == "premiado" or detection.game_index in strategic_games
            reason = "premiado" if detection.prize_status == "premiado" else ("estrategico" if detection.game_index in strategic_games else "abaixo_da_premiacao_minima")
            decisions.append(
                RetentionDecision(
                    game_index=detection.game_index,
                    keep=keep,
                    reason=reason,
                )
            )
        return decisions


class OperationalLifecycleEngine:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path
        self.reconciliation_repository = ReconciliationRepository(db_path)
        self.prize_detection = PrizeDetectionEngine()
        self.retention_policy = RetentionPolicyEngine()

    def build_dashboard(self) -> OperationalDashboardSummary:
        with get_session(self.db_path) as session:
            rows = session.execute(
                text(
                    """
                SELECT
                    COUNT(*) AS total_runs,
                    COALESCE(SUM(prize_count), 0) AS prize_count,
                    COALESCE(MAX(best_hits), 0) AS best_hits,
                    COALESCE(MAX(contest_id), NULL) AS latest_contest
                FROM reconciliation_runs
                    """
                )
            ).first()
            tier_rows = session.execute(
                text(
                    """
                SELECT prize_tier, COUNT(*)
                FROM reconciliation_games
                WHERE prize_tier != ''
                GROUP BY prize_tier
                    """
                )
            ).all()
            total_games = int(session.execute(text("SELECT COUNT(*) FROM reconciliation_games")).scalar() or 0)

        prize_tiers = {str(row[0]): int(row[1]) for row in tier_rows}
        prize_count = int(rows[1] or 0) if rows else 0
        best_hits = int(rows[2] or 0) if rows else 0
        latest_contest = int(rows[3]) if rows and rows[3] is not None else None
        status = "operational" if total_games else "idle"
        notes = []
        if prize_count:
            notes.append("há premiações registradas")
        if latest_contest is not None:
            notes.append(f"último concurso reconciliado {latest_contest}")
        return OperationalDashboardSummary(
            total_runs=int(rows[0] or 0) if rows else 0,
            total_games=total_games,
            prize_count=prize_count,
            best_hits=best_hits,
            latest_contest=latest_contest,
            status=status,
            prize_tiers=prize_tiers,
            post_draw_notes=notes,
        )

    def build_telemetry(self) -> dict[str, Any]:
        with get_session(self.db_path) as session:
            sync_runs = int(session.execute(text("SELECT COUNT(*) FROM imported_contests")).scalar() or 0)
            generated_games = int(session.execute(text("SELECT COUNT(*) FROM generated_games")).scalar() or 0)
            reconciliation_runs = int(session.execute(text("SELECT COUNT(*) FROM reconciliation_runs")).scalar() or 0)
            reconciliation_games = int(session.execute(text("SELECT COUNT(*) FROM reconciliation_games")).scalar() or 0)
            check_events = int(session.execute(text("SELECT COUNT(*) FROM check_events")).scalar() or 0)
        return {
            "sync_runs": sync_runs,
            "generated_games": generated_games,
            "reconciliation_runs": reconciliation_runs,
            "reconciliation_games": reconciliation_games,
            "check_events": check_events,
            "operational_status": "healthy" if reconciliation_runs else "idle",
        }

    def close_day(
        self,
        *,
        contest_id: int,
        generated_games: list[dict[str, Any]],
        official_numbers: list[int],
        generation_event_id: int,
        lead_id: int | None = None,
        strategic_games: set[int] | None = None,
        cleanup: bool = True,
    ) -> OperationalClosureReport:
        detections: list[PrizeDetection] = []
        for index, game in enumerate(generated_games, start=1):
            numbers = [int(number) for number in game.get("numbers", [])]
            matched_numbers = sorted(set(numbers) & set(official_numbers))
            hits = len(matched_numbers)
            prize_tier = PrizeDetectionEngine._tier_for_hits(hits)
            detections.append(
                PrizeDetection(
                    game_index=index,
                    hits=hits,
                    prize_status="premiado" if prize_tier else "nao_premiado",
                    prize_tier=prize_tier,
                    matched_numbers=matched_numbers,
                )
            )
        decisions = self.retention_policy.decide(detections, strategic_games=strategic_games)
        keep_indexes = {decision.game_index for decision in decisions if decision.keep}
        retained_games = [game for index, game in enumerate(generated_games, start=1) if index in keep_indexes]
        removed_games = len(generated_games) - len(retained_games)
        dashboard = self.build_dashboard()
        telemetry = self.build_telemetry()
        matched_games = []
        for index, game in enumerate(generated_games, start=1):
            numbers = [int(number) for number in game.get("numbers", [])]
            matched_numbers = sorted(set(numbers) & set(official_numbers))
            hits = len(matched_numbers)
            prize_tier = PrizeDetectionEngine._tier_for_hits(hits)
            matched_games.append(
                {
                    "game_index": index,
                    "numbers": numbers,
                    "hits": hits,
                    "matched_numbers": matched_numbers,
                    "prize_status": "premiado" if prize_tier else "nao_premiado",
                    "prize_tier": prize_tier,
                    "context_json": {"official_numbers": official_numbers},
                }
            )
        summary = self.reconciliation_repository.insert(
            generation_event_id=generation_event_id,
            lead_id=lead_id,
            contest_id=contest_id,
            source="official_result",
            status="reconciliado",
            prize_count=sum(1 for detection in detections if detection.prize_status == "premiado"),
            total_hits=sum(detection.hits for detection in detections),
            best_hits=max((detection.hits for detection in detections), default=0),
            payload={
                "contest_id": contest_id,
                "official_numbers": official_numbers,
                "status": "reconciliado",
            },
            games=matched_games,
        )
        if cleanup and removed_games:
            self._cleanup_non_prized(generation_event_id=generation_event_id, keep_indexes=keep_indexes)
        return OperationalClosureReport(
            created_at=datetime.now(UTC),
            contest_id=contest_id,
            prize_count=summary["prize_count"],
            retained_games=len(retained_games),
            removed_games=removed_games,
            telemetry=telemetry,
            dashboard=dashboard,
            detections=detections,
            decisions=decisions,
        )

    def _cleanup_non_prized(self, *, generation_event_id: int, keep_indexes: set[int]) -> None:
        with get_session(self.db_path) as session:
            if keep_indexes:
                session.query(GeneratedGame).filter(
                    GeneratedGame.generation_event_id == generation_event_id,
                    ~GeneratedGame.game_index.in_(sorted(keep_indexes)),
                ).delete(synchronize_session=False)
                session.query(ReconciliationGame).filter(
                    ReconciliationGame.generation_event_id == generation_event_id,
                    ~ReconciliationGame.game_index.in_(sorted(keep_indexes)),
                ).delete(synchronize_session=False)
            else:
                session.query(GeneratedGame).filter(GeneratedGame.generation_event_id == generation_event_id).delete(synchronize_session=False)
                session.query(ReconciliationGame).filter(ReconciliationGame.generation_event_id == generation_event_id).delete(synchronize_session=False)
            session.commit()
