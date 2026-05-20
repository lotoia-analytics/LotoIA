from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any

from lotoia.data.loader import (
    DEFAULT_HISTORY_PATH,
    load_draws_csv,
)
from lotoia.generator.engine import (
    generate_ranked_games,
)
from lotoia.public.models import (
    PublicCheckRequest,
    PublicGenerationRequest,
)


class PublicRateLimitError(Exception):
    pass


class PublicContestNotFoundError(Exception):
    pass


RATE_LIMIT_SECONDS = 15

_last_requests: dict[str, float] = {}


def _validate_rate_limit(
    limiter_key: str,
) -> None:

    current_time = time.time()

    previous_time = _last_requests.get(
        limiter_key
    )

    if previous_time:

        elapsed = (
            current_time
            - previous_time
        )

        if elapsed < RATE_LIMIT_SECONDS:

            raise PublicRateLimitError(
                (
                    "Muitas requisições. "
                    "Aguarde alguns segundos."
                )
            )

    _last_requests[
        limiter_key
    ] = current_time


def _find_contest(
    contest_id: int,
    history_path: Path,
):

    draws = list(
        load_draws_csv(history_path)
    )

    if not draws:

        raise PublicContestNotFoundError(
            "Nenhum concurso encontrado."
        )

    available_contests = [
        draw.contest
        for draw in draws
    ]

    latest_contest = max(
        available_contests
    )

    if contest_id > latest_contest:

        raise PublicContestNotFoundError(
            (
                f"Concurso {contest_id} "
                f"ainda não disponível. "
                f"Último concurso carregado: "
                f"{latest_contest}."
            )
        )

    for draw in draws:

        if draw.contest == contest_id:
            return draw

    raise PublicContestNotFoundError(
        (
            f"Concurso {contest_id} "
            f"não encontrado na base histórica."
        )
    )


def find_historical_matches(
    numbers: list[int],
    history_path: Path = DEFAULT_HISTORY_PATH,
) -> dict[str, Any]:

    target = sorted(numbers)

    draws = list(
        load_draws_csv(history_path)
    )

    matches = []

    for draw in draws:

        if sorted(draw.numbers) == target:

            matches.append(
                {
                    "contest": draw.contest,
                    "date": draw.date,
                }
            )

    return {
        "is_repeated": len(matches) > 0,
        "total_matches": len(matches),
        "matches": matches,
    }


def generate_public_games(
    request: PublicGenerationRequest,
    source: str,
    user_agent: str,
    limiter_key: str,
):

    _validate_rate_limit(
        limiter_key
    )

    seed = random.randint(
        1,
        999999,
    )

    started_at = time.time()

    games = generate_ranked_games(
        total_games=3,
        seed=seed,
        ml_enabled=request.ml_enabled,
    )

    execution_time_ms = (
        time.time()
        - started_at
    ) * 1000

    return {
        "games": games,
        "metadata": {
            "seed": seed,
            "strategy": "ranking_hibrido",
            "ranking_score": 0.91,
            "execution_time_ms": round(
                execution_time_ms,
                2,
            ),
            "ml_enabled": (
                request.ml_enabled
            ),
            "source": source,
            "user_agent": user_agent,
        },
    }


def check_public_contest(
    request: PublicCheckRequest,
    source: str,
    user_agent: str,
    limiter_key: str,
):

    _validate_rate_limit(
        limiter_key
    )

    started_at = time.time()

    draw = _find_contest(
        request.contest_id,
        DEFAULT_HISTORY_PATH,
    )

    correct_numbers = sorted(
        draw.numbers
    )

    checked_numbers = sorted(
        request.numbers
    )

    hits = len(
        set(correct_numbers)
        & set(checked_numbers)
    )

    execution_time_ms = (
        time.time()
        - started_at
    ) * 1000

    return {
        "hits": hits,
        "correct_numbers": (
            correct_numbers
        ),
        "result": {
            "contest_id": (
                request.contest_id
            ),
            "execution_time_ms": round(
                execution_time_ms,
                2,
            ),
            "source": source,
            "user_agent": user_agent,
        },
    }
