from __future__ import annotations

from pathlib import Path
from typing import Any

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    ExpansionEvent,
    InstitutionalValidatedExpansion,
    GeneratedGame,
    CheckEvent,
    GenerationEvent,
    MlUsageEvent,
    ReportEvent,
    ReconciliationEvent,
    ReconciliationGame,
    ReconciliationRun,
    Lead,
    get_session,
)


def _model_to_dict(model) -> dict[str, Any]:
    return {column.name: getattr(model, column.name) for column in model.__table__.columns}


class LeadRepository:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def insert(
        self,
        *,
        first_name: str,
        whatsapp: str,
        source: str,
        ip_hash: str,
        user_agent: str,
        messenger_psid: str | None = None,
    ) -> dict[str, Any]:
        with get_session(self.db_path) as session:
            lead = Lead(
                first_name=first_name,
                whatsapp=whatsapp,
                source=source,
                ip_hash=ip_hash,
                user_agent=user_agent,
                messenger_psid=str(messenger_psid).strip() if messenger_psid else None,
            )
            session.add(lead)
            session.commit()
            return _model_to_dict(lead)

    def get(self, lead_id: int) -> dict[str, Any] | None:
        with get_session(self.db_path) as session:
            lead = session.get(Lead, lead_id)
            return _model_to_dict(lead) if lead else None

    def find_by_first_name_and_whatsapp(self, first_name: str, whatsapp: str) -> dict[str, Any] | None:
        with get_session(self.db_path) as session:
            lead = (
                session.query(Lead)
                .filter(Lead.first_name == first_name, Lead.whatsapp == whatsapp)
                .order_by(Lead.created_at.desc())
                .first()
            )
            return _model_to_dict(lead) if lead else None


class GenerationEventRepository:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def insert(
        self,
        *,
        lead_id: int,
        generated_games: list[dict[str, Any]],
        ml_enabled: bool,
        seed: int,
        strategy: str,
        ranking_score: float,
        execution_time_ms: float,
        target_contest: int | None = None,
        origin: str = "public_api",
        generation_mode: str = "public_hybrid_statistical_v1",
        context: dict[str, Any] | None = None,
        first_name: str = "",
        whatsapp: str = "",
        channel: str = "whatsapp",
    ) -> dict[str, Any]:
        with get_session(self.db_path) as session:
            resolved_lead_id = int(lead_id) if lead_id is not None else 0
            event = GenerationEvent(
                lead_id=lead_id,
                first_name=first_name,
                whatsapp=whatsapp,
                generated_games=generated_games,
                context_json=dict(context or {}),
                ml_enabled=int(ml_enabled),
                seed=seed,
                strategy=strategy,
                ranking_score=ranking_score,
                execution_time_ms=execution_time_ms,
                channel=str(channel or "whatsapp").strip().lower(),
            )
            session.add(event)
            session.commit()
            for index, game in enumerate(generated_games, start=1):
                session.add(
                    GeneratedGame(
                        generation_event_id=event.id,
                        lead_id=resolved_lead_id,
                        target_contest=target_contest,
                        origin=origin,
                        generation_mode=generation_mode,
                        game_index=index,
                        numbers=game.get("numbers", []),
                        profile_type=str(game.get("profile_type", "")),
                        final_score=dict(game.get("final_score", {})) if isinstance(game.get("final_score"), dict) else {},
                        quadra_score=dict(game.get("quadra_score", {})) if isinstance(game.get("quadra_score"), dict) else {},
                        context_json=context or {},
                    )
                )
            if ml_enabled:
                session.add(
                    MlUsageEvent(
                        lead_id=lead_id,
                        generation_event_id=event.id,
                        source=origin,
                        strategy=strategy,
                        execution_time_ms=execution_time_ms,
                        payload=context or {},
                    )
                )
            session.commit()
            return _model_to_dict(event)

    def list_by_lead(self, lead_id: int) -> list[dict[str, Any]]:
        with get_session(self.db_path) as session:
            rows = (
                session.query(GenerationEvent)
                .filter(GenerationEvent.lead_id == lead_id)
                .order_by(GenerationEvent.created_at.desc())
                .all()
            )
            return [_model_to_dict(row) for row in rows]

    def get(self, event_id: int) -> dict[str, Any] | None:
        with get_session(self.db_path) as session:
            event = session.get(GenerationEvent, event_id)
            return _model_to_dict(event) if event else None


class MlUsageEventRepository:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def insert(
        self,
        *,
        lead_id: int,
        generation_event_id: int,
        source: str,
        strategy: str,
        execution_time_ms: float,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with get_session(self.db_path) as session:
            event = MlUsageEvent(
                lead_id=lead_id,
                generation_event_id=generation_event_id,
                source=source,
                strategy=strategy,
                execution_time_ms=execution_time_ms,
                payload=payload or {},
            )
            session.add(event)
            session.commit()
            return _model_to_dict(event)

    def count(self) -> int:
        with get_session(self.db_path) as session:
            return int(session.query(MlUsageEvent).count())


class ReportEventRepository:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def insert(
        self,
        *,
        lead_id: int | None,
        generation_event_id: int | None,
        report_type: str,
        generation_origin: str,
        runtime_origin: str,
        strategy_profile: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with get_session(self.db_path) as session:
            event = ReportEvent(
                lead_id=lead_id,
                generation_event_id=generation_event_id,
                report_type=report_type,
                generation_origin=generation_origin,
                runtime_origin=runtime_origin,
                strategy_profile=strategy_profile,
                payload=payload or {},
            )
            session.add(event)
            session.commit()
            return _model_to_dict(event)

    def count(self) -> int:
        with get_session(self.db_path) as session:
            return int(session.query(ReportEvent).count())


class ExpansionEventRepository:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def insert(
        self,
        *,
        lead_id: int | None,
        generation_event_id: int | None,
        expansion_type: str,
        expansion_size: int,
        runtime_origin: str,
        strategy_profile: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with get_session(self.db_path) as session:
            event = ExpansionEvent(
                lead_id=lead_id,
                generation_event_id=generation_event_id,
                expansion_type=expansion_type,
                expansion_size=expansion_size,
                runtime_origin=runtime_origin,
                strategy_profile=strategy_profile,
                payload=payload or {},
            )
            session.add(event)
            session.commit()
            return _model_to_dict(event)

    def count(self) -> int:
        with get_session(self.db_path) as session:
            return int(session.query(ExpansionEvent).count())


class InstitutionalValidatedExpansionRepository:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def insert(
        self,
        *,
        expansion_event_id: int | None,
        generation_event_id: int | None,
        contest_id: int | None,
        status: str,
        profile_type: str,
        scientific_score: float,
        diversity_score: float,
        overlap_score: float,
        hits: int,
        recurrence_score: float,
        proximity_score: float,
        efficiency_score: float,
        premium_rank: int,
        payload: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with get_session(self.db_path) as session:
            event = InstitutionalValidatedExpansion(
                expansion_event_id=expansion_event_id,
                generation_event_id=generation_event_id,
                contest_id=contest_id,
                status=status,
                profile_type=profile_type,
                scientific_score=scientific_score,
                diversity_score=diversity_score,
                overlap_score=overlap_score,
                hits=hits,
                recurrence_score=recurrence_score,
                proximity_score=proximity_score,
                efficiency_score=efficiency_score,
                premium_rank=premium_rank,
                payload=payload or {},
                metrics=metrics or {},
            )
            session.add(event)
            session.commit()
            return _model_to_dict(event)

    def list(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with get_session(self.db_path) as session:
            rows = (
                session.query(InstitutionalValidatedExpansion)
                .order_by(InstitutionalValidatedExpansion.created_at.desc(), InstitutionalValidatedExpansion.id.desc())
                .limit(limit)
                .all()
            )
            return [_model_to_dict(row) for row in rows]

    def cleanup(self, *, keep_limit: int = 50, keep_statuses: tuple[str, ...] = ("PREMIUM", "VALIDATED", "ARCHIVED")) -> int:
        with get_session(self.db_path) as session:
            rows = (
                session.query(InstitutionalValidatedExpansion)
                .order_by(InstitutionalValidatedExpansion.scientific_score.desc(), InstitutionalValidatedExpansion.created_at.desc())
                .all()
            )
            keep_ids: set[int] = set()
            for row in rows:
                if str(row.status or "") in keep_statuses and len(keep_ids) < keep_limit:
                    keep_ids.add(int(row.id))
            removed = 0
            for row in rows:
                if int(row.id) not in keep_ids:
                    session.delete(row)
                    removed += 1
            session.commit()
            return removed

    def count(self) -> int:
        with get_session(self.db_path) as session:
            return int(session.query(InstitutionalValidatedExpansion).count())


class ReconciliationEventRepository:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def insert(
        self,
        *,
        lead_id: int | None,
        generation_event_id: int | None,
        reconciliation_type: str,
        hits: int,
        matched_numbers: list[int],
        runtime_origin: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with get_session(self.db_path) as session:
            event = ReconciliationEvent(
                lead_id=lead_id,
                generation_event_id=generation_event_id,
                reconciliation_type=reconciliation_type,
                hits=hits,
                matched_numbers=matched_numbers,
                runtime_origin=runtime_origin,
                payload=payload or {},
            )
            session.add(event)
            session.commit()
            return _model_to_dict(event)

    def count(self) -> int:
        with get_session(self.db_path) as session:
            return int(session.query(ReconciliationEvent).count())


class CheckEventRepository:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def insert(
        self,
        *,
        lead_id: int,
        contest_id: int,
        selected_numbers: list[int],
        hits: int,
        result_payload: dict[str, Any],
    ) -> dict[str, Any]:
        with get_session(self.db_path) as session:
            event = CheckEvent(
                lead_id=lead_id,
                contest_id=contest_id,
                selected_numbers=selected_numbers,
                hits=hits,
                result_payload=result_payload,
            )
            session.add(event)
            session.commit()
            return _model_to_dict(event)

    def list_by_lead(self, lead_id: int) -> list[dict[str, Any]]:
        with get_session(self.db_path) as session:
            rows = (
                session.query(CheckEvent)
                .filter(CheckEvent.lead_id == lead_id)
                .order_by(CheckEvent.created_at.desc())
                .all()
            )
            return [_model_to_dict(row) for row in rows]


class ReconciliationRepository:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def insert(
        self,
        *,
        generation_event_id: int,
        lead_id: int | None,
        contest_id: int,
        source: str,
        status: str,
        prize_count: int,
        total_hits: int,
        best_hits: int,
        payload: dict[str, Any],
        games: list[dict[str, Any]],
    ) -> dict[str, Any]:
        with get_session(self.db_path) as session:
            run = ReconciliationRun(
                generation_event_id=generation_event_id,
                lead_id=lead_id,
                contest_id=contest_id,
                source=source,
                status=status,
                prize_count=prize_count,
                total_hits=total_hits,
                best_hits=best_hits,
                payload=payload,
            )
            session.add(run)
            session.commit()
            for game in games:
                session.add(
                    ReconciliationGame(
                        reconciliation_run_id=run.id,
                        generation_event_id=generation_event_id,
                        lead_id=lead_id,
                        contest_id=contest_id,
                        game_index=int(game["game_index"]),
                        numbers=game["numbers"],
                        hits=int(game["hits"]),
                        matched_numbers=game["matched_numbers"],
                        prize_status=str(game["prize_status"]),
                        prize_tier=str(game["prize_tier"]),
                        context_json=game.get("context_json", {}),
                    )
                )
            session.commit()
            return {
                "id": run.id,
                "generation_event_id": generation_event_id,
                "lead_id": lead_id,
                "contest_id": contest_id,
                "source": source,
                "status": status,
                "prize_count": prize_count,
                "total_hits": total_hits,
                "best_hits": best_hits,
                "payload": payload,
            }
