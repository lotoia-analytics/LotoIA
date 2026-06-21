import logging
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH, get_session
from lotoia.database.contest_repository import ContestRepository
from lotoia.public.operational_lifecycle import OperationalLifecycleEngine
from sqlalchemy import text

logger = logging.getLogger(__name__)

def run_institutional_conference(*, db_path: Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """Reconcile institutional games (generated_games) against the latest official contest."""
    contest_repository = ContestRepository(db_path)
    contest_number = int(contest_repository.get_official_history_max_contest() or 0)
    
    if contest_number <= 0:
        return {
            "status": "skipped",
            "reason": "no_official_contest",
            "contest_number": None,
        }

    official_contest = contest_repository.get_official_history_contest(contest_number)
    if not official_contest:
        return {
            "status": "skipped",
            "reason": "official_contest_missing",
            "contest_number": contest_number,
        }
    
    official_numbers = [int(n) for n in official_contest["dezenas"]]
    
    engine = OperationalLifecycleEngine(db_path)
    processed_events = 0
    total_prizes = 0
    
    with get_session(db_path) as session:
        # Encontrar eventos de geração pendentes para este concurso
        # Um evento é pendente se tem jogos em generated_games para o contest_id
        # mas não tem entrada em reconciliation_runs
        pending_events_query = text("""
            SELECT DISTINCT g.generation_event_id 
            FROM generated_games g
            LEFT JOIN reconciliation_runs r ON g.generation_event_id = r.generation_event_id
            WHERE g.target_contest = :contest_id AND r.id IS NULL
        """)
        
        event_ids = [row[0] for row in session.execute(pending_events_query, {"contest_id": contest_number}).all()]
        
        for ev_id in event_ids:
            # Carregar jogos do evento
            games_query = text("""
                SELECT numbers, lead_id FROM generated_games 
                WHERE generation_event_id = :ev_id
            """)
            rows = session.execute(games_query, {"ev_id": ev_id}).all()
            
            if not rows:
                continue
                
            games = [{"numbers": row[0]} for row in rows]
            lead_id = rows[0][1]
            
            try:
                report = engine.close_day(
                    contest_id=contest_number,
                    generated_games=games,
                    official_numbers=official_numbers,
                    generation_event_id=ev_id,
                    lead_id=lead_id,
                    cleanup=False
                )
                processed_events += 1
                total_prizes += report.prize_count
                logger.info(f"Evento {ev_id} reconciliado. Prêmios: {report.prize_count}")
            except Exception as e:
                logger.error(f"Erro ao reconciliar evento {ev_id}: {e}")
                
    return {
        "status": "completed",
        "contest_number": contest_number,
        "processed_events": processed_events,
        "total_prizes": total_prizes,
    }
