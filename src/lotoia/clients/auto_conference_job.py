from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert

from lotoia.clients.conference_utils import (
    calculate_hits,
    extract_game_numbers,
    parse_official_numbers,
    premio_status_from_hits,
)
from lotoia.clients.repository import ClientRepository
from lotoia.database.contest_repository import ContestRepository
from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    LotoiaClient,
    LotoiaClientConferenceResult,
    LotoiaClientGeneration,
    create_database,
    get_session,
)

logger = logging.getLogger(__name__)


def run_auto_conference(*, db_path: Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """Conference WhatsApp client games against the latest synced official contest."""
    create_database(db_path)
    contest_repository = ContestRepository(db_path)
    client_repository = ClientRepository(db_path)

    contest_number = int(contest_repository.get_official_history_max_contest() or 0)
    if contest_number <= 0:
        return {
            "status": "skipped",
            "reason": "no_official_contest",
            "contest_number": None,
            "clients_processed": 0,
            "results_persisted": 0,
        }

    confirmation = contest_repository.confirm_sync_persistence(contest_number)
    if not confirmation.get("ok"):
        return {
            "status": "skipped",
            "reason": "sync_not_confirmed",
            "contest_number": contest_number,
            "confirmation": confirmation,
            "clients_processed": 0,
            "results_persisted": 0,
        }

    official_contest = contest_repository.get_official_history_contest(contest_number)
    if not official_contest:
        return {
            "status": "skipped",
            "reason": "official_contest_missing",
            "contest_number": contest_number,
            "clients_processed": 0,
            "results_persisted": 0,
        }
    official_numbers = parse_official_numbers(official_contest)

    today = datetime.now(UTC).date()
    clients_processed = 0
    results_persisted = 0
    skipped_clients = 0

    with get_session(db_path) as session:
        active_clients = (
            session.query(LotoiaClient)
            .filter(LotoiaClient.status == "ativo")
            .filter(LotoiaClient.data_expiracao >= datetime.combine(today, datetime.min.time(), tzinfo=UTC))
            .all()
        )

        for client in active_clients:
            client_id = int(client.id)
            if client_repository.client_contest_already_conferenced(
                client_id=client_id,
                contest_number=contest_number,
            ):
                skipped_clients += 1
                continue

            generations = (
                session.query(LotoiaClientGeneration)
                .filter(
                    LotoiaClientGeneration.client_id == client_id,
                    LotoiaClientGeneration.concurso_alvo == contest_number,
                )
                .all()
            )
            if not generations:
                continue

            clients_processed += 1
            backend = session.bind.dialect.name if session.bind is not None else "sqlite"
            for generation in generations:
                jogos = list(generation.jogos or [])
                for game_index, game in enumerate(jogos, start=1):
                    numbers = extract_game_numbers(dict(game))
                    hits = calculate_hits(numbers, official_numbers)
                    values = {
                        "client_id": client_id,
                        "phone": str(generation.phone or client.phone or ""),
                        "contest_number": contest_number,
                        "game_index": int(game_index),
                        "numbers": numbers,
                        "hits": int(hits),
                        "premio_status": premio_status_from_hits(hits),
                        "notified": False,
                        "created_at": datetime.now(UTC),
                    }
                    if backend == "postgresql":
                        stmt = pg_insert(LotoiaClientConferenceResult).values(**values)
                        stmt = stmt.on_conflict_do_nothing(
                            index_elements=["client_id", "contest_number", "game_index"],
                        )
                        result = session.execute(stmt)
                        if int(result.rowcount or 0) > 0:
                            results_persisted += 1
                    else:
                        existing = (
                            session.query(LotoiaClientConferenceResult)
                            .filter(
                                LotoiaClientConferenceResult.client_id == client_id,
                                LotoiaClientConferenceResult.contest_number == contest_number,
                                LotoiaClientConferenceResult.game_index == int(game_index),
                            )
                            .one_or_none()
                        )
                        if existing is None:
                            session.add(LotoiaClientConferenceResult(**values))
                            results_persisted += 1
        session.commit()

    payload = {
        "status": "completed",
        "contest_number": contest_number,
        "clients_processed": clients_processed,
        "skipped_clients": skipped_clients,
        "results_persisted": results_persisted,
        "official_numbers": official_numbers,
    }
    logger.info("AUTO_CONFERENCE %s", payload)
    return payload
