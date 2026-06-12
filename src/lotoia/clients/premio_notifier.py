from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from lotoia.clients.evolution_client import EvolutionApiClient
from lotoia.database.database import DEFAULT_DATABASE_PATH, LotoiaClientConferenceResult, create_database, get_session

logger = logging.getLogger(__name__)

WINNER_MIN_HITS = 11


def build_winner_message(*, contest_number: int, game_index: int, hits: int) -> str:
    return f"Concurso {int(contest_number)} — Jogo {int(game_index):02d}: {int(hits)} pontos ✅"


def notify_winners(
    contest_number: int,
    *,
    db_path: Path = DEFAULT_DATABASE_PATH,
    evolution_client: EvolutionApiClient | None = None,
) -> dict[str, Any]:
    create_database(db_path)
    client = evolution_client or EvolutionApiClient()
    notified_count = 0
    failed_count = 0
    skipped_count = 0

    with get_session(db_path) as session:
        winners = (
            session.query(LotoiaClientConferenceResult)
            .filter(
                LotoiaClientConferenceResult.contest_number == int(contest_number),
                LotoiaClientConferenceResult.hits >= WINNER_MIN_HITS,
                LotoiaClientConferenceResult.notified.is_(False),
            )
            .order_by(LotoiaClientConferenceResult.game_index.asc())
            .all()
        )
        for winner in winners:
            message = build_winner_message(
                contest_number=int(winner.contest_number),
                game_index=int(winner.game_index),
                hits=int(winner.hits),
            )
            if client.send_text(str(winner.phone), message):
                winner.notified = True
                notified_count += 1
            else:
                failed_count += 1
        session.commit()

    payload = {
        "status": "completed",
        "contest_number": int(contest_number),
        "notified_count": notified_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
    }
    logger.info("PREMIO_NOTIFIER %s", payload)
    return payload
