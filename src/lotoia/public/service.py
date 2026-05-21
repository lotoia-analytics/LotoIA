from __future__ import annotations

import random
import time
from collections import deque
from pathlib import Path
from typing import Any

from lotoia.data.loader import DEFAULT_HISTORY_PATH, load_draws_csv
from lotoia.generator.engine import generate_ranked_games
from lotoia.public.persistence import GenerationEventRepository, LeadRepository, initialize_public_persistence
from lotoia.public.models import PublicCheckRequest, PublicGenerationRequest


class PublicRateLimitError(Exception):
    pass


class PublicContestNotFoundError(Exception):
    pass


class PublicLimiter:
    def __init__(self, cooldown_seconds: int = 15, max_requests_per_window: int = 2, window_seconds: int = 60) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.max_requests_per_window = max_requests_per_window
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = {}

    def check(self, limiter_key: str, now: float | None = None) -> tuple[bool, str]:
        current_time = now if now is not None else time.time()
        history = self._requests.setdefault(limiter_key, deque())
        while history and current_time - history[0] > self.window_seconds:
            history.popleft()
        if history and current_time - history[-1] < self.cooldown_seconds:
            return False, "cooldown"
        if len(history) >= self.max_requests_per_window:
            return False, "window"
        history.append(current_time)
        return True, "ok"


def _resolve_limiter(active_limiter: PublicLimiter | None) -> PublicLimiter:
    return active_limiter or PublicLimiter()


def _validate_rate_limit(limiter_key: str, active_limiter: PublicLimiter | None = None) -> None:
    allowed, reason = _resolve_limiter(active_limiter).check(limiter_key)
    if not allowed:
        raise PublicRateLimitError(
            "Muitas requisições. Aguarde alguns segundos."
            if reason == "cooldown"
            else "Muitas requisições na janela atual."
        )


def _find_contest(contest_id: int, history_path: Path) -> Any:
    draws = list(load_draws_csv(history_path))
    if not draws:
        raise PublicContestNotFoundError("Nenhum concurso encontrado.")
    latest_contest = max(draw.contest for draw in draws)
    if contest_id > latest_contest:
        raise PublicContestNotFoundError(
            f"Concurso {contest_id} ainda não disponível. Último concurso carregado: {latest_contest}."
        )
    for draw in draws:
        if draw.contest == contest_id:
            return draw
    raise PublicContestNotFoundError(f"Concurso {contest_id} não encontrado na base histórica.")


def find_historical_matches(numbers: list[int], history_path: Path = DEFAULT_HISTORY_PATH) -> dict[str, Any]:
    target = sorted(numbers)
    matches = []
    for draw in load_draws_csv(history_path):
        if sorted(draw.numbers) == target:
            matches.append({"contest": draw.contest, "date": draw.date})
    return {"is_repeated": len(matches) > 0, "total_matches": len(matches), "matches": matches}


def generate_public_games(
    request: PublicGenerationRequest,
    *,
    db_path: Path | None = None,
    source: str = "public_api",
    ip_address: str = "",
    user_agent: str = "",
    active_limiter: PublicLimiter | None = None,
) -> dict[str, Any]:
    _validate_rate_limit(ip_address or "anonymous", active_limiter)
    target_contest = _latest_history_contest(history_path=DEFAULT_HISTORY_PATH)
    seed = random.randint(1, 999999)
    started_at = time.time()
    games_payload = generate_ranked_games(total_games=2, seed=seed, ml_enabled=request.ml_enabled)
    execution_time_ms = (time.time() - started_at) * 1000
    if db_path is not None:
        initialize_public_persistence(db_path)
        lead_repository = LeadRepository(db_path)
        generation_repository = GenerationEventRepository(db_path)
        lead = lead_repository.find_by_first_name_and_whatsapp(request.first_name.strip(), request.whatsapp)
        if lead is None:
            lead = lead_repository.insert(
                first_name=request.first_name.strip(),
                whatsapp=request.whatsapp,
                source=source,
                ip_hash="",
                user_agent=user_agent,
            )
        generation_repository.insert(
            lead_id=lead["id"],
            generated_games=games_payload,
            ml_enabled=request.ml_enabled,
            seed=seed,
            strategy="public_hybrid_statistical_v1",
            ranking_score=0.91,
            execution_time_ms=round(execution_time_ms, 2),
            target_contest=target_contest,
            origin=source,
            generation_mode="public_hybrid_statistical_v1",
            context={
                "source": source,
                "user_agent": user_agent,
                "target_contest": target_contest,
                "ml_enabled": bool(request.ml_enabled),
            },
        )
    return {
        "games": games_payload,
        "metadata": {
            "seed": seed,
            "strategy": "public_hybrid_statistical_v1",
            "ranking_score": 0.91,
            "execution_time_ms": round(execution_time_ms, 2),
            "ml_enabled": bool(request.ml_enabled),
            "source": source,
            "user_agent": user_agent,
            "max_games": 2,
            "engine_version": "historical_recalibrated_v2",
            "fallback_used": False,
            "profile_distribution": {
                profile: sum(1 for game in games_payload if game.get("profile_type") == profile)
                for profile in ("recorrente", "hibrido", "caotico")
            },
            "target_contest": target_contest,
        },
    }


def check_public_contest(
    request: PublicCheckRequest,
    *,
    db_path: Path | None = None,
    history_path: Path = DEFAULT_HISTORY_PATH,
    source: str = "public_api",
    ip_address: str = "",
    user_agent: str = "",
    active_limiter: PublicLimiter | None = None,
) -> dict[str, Any]:
    _validate_rate_limit(ip_address or "anonymous", active_limiter)
    started_at = time.time()
    draw = _find_contest(request.contest_id, history_path)
    correct_numbers = sorted(draw.numbers)
    checked_numbers = sorted(request.numbers)
    hits = len(set(correct_numbers) & set(checked_numbers))
    execution_time_ms = (time.time() - started_at) * 1000
    return {
        "hits": hits,
        "correct_numbers": correct_numbers,
        "result": {
            "contest_id": request.contest_id,
            "execution_time_ms": round(execution_time_ms, 2),
            "source": source,
            "user_agent": user_agent,
        },
    }


def _latest_history_contest(history_path: Path = DEFAULT_HISTORY_PATH) -> int | None:
    try:
        draws = load_draws_csv(history_path)
    except Exception:
        return None
    if not draws:
        return None
    return max(draw.contest for draw in draws)
