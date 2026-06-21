from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any

from lotoia.clients.game_expansion import expand_generation_games_for_format
from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL as LEI15_SOVEREIGN_BATCH_LABEL
from lotoia.generator.engine import generate_ranked_games
from lotoia.public.persistence import GenerationEventRepository, LeadRepository


def generate_messenger_games(
    *,
    targets: list[tuple[int, int]],
    psid: str,
    client_name: str = "Cliente",
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    quantidade = sum(qty for _, qty in targets)
    seed = random.randint(1, 999999)
    started_at = time.time()
    base_games = generate_ranked_games(
        total_games=int(quantidade),
        seed=seed,
        ml_enabled=False,
        batch_label=LEI15_SOVEREIGN_BATCH_LABEL,
    )
    games: list[dict[str, Any]] = []
    offset = 0
    for formato, qty in targets:
        chunk = list(base_games[offset : offset + int(qty)])
        offset += int(qty)
        expanded = expand_generation_games_for_format(chunk, int(formato))
        for game in expanded:
            tagged = dict(game)
            tagged["formato_cartao"] = int(formato)
            games.append(tagged)
    execution_time_ms = (time.time() - started_at) * 1000
    ranking_score = float(
        sum(float(game.get("final_score", {}).get("final_score", 0) or 0) for game in games) / max(len(games), 1)
        if games
        else 0.0
    )

    lead_repo = LeadRepository(db_path)
    lead = lead_repo.find_by_first_name_and_whatsapp(client_name, str(psid))
    if lead is None:
        lead = lead_repo.find_by_first_name_and_whatsapp("Messenger", str(psid))
    if lead is None:
        lead = lead_repo.insert(
            first_name=client_name or "Messenger",
            whatsapp=str(psid),
            source="messenger",
            ip_hash="",
            user_agent="messenger_bot",
        )

    generation_repo = GenerationEventRepository(db_path)
    generation_event = generation_repo.insert(
        lead_id=int(lead["id"]),
        generated_games=games,
        ml_enabled=False,
        seed=seed,
        strategy="messenger_statistical_v1",
        ranking_score=ranking_score,
        execution_time_ms=execution_time_ms,
        origin="messenger_bot",
        generation_mode="messenger_hybrid_statistical_v1",
        context={
            "targets": [{"formato": int(formato), "quantidade": int(qty)} for formato, qty in targets],
            "quantidade": int(quantidade),
            "source": "messenger",
            "messenger_psid": str(psid),
        },
        first_name=client_name,
        whatsapp=str(psid),
        channel="messenger",
    )
    return games, generation_event
