from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator

from lotoia.data.loader import DEFAULT_HISTORY_PATH, load_draws_csv
from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.generator.basic_generator import generate_best_games
from lotoia.observability import MetricsRegistry, StructuredLogger
from lotoia.public.persistence import (
    CheckEventRepository,
    GenerationEventRepository,
    initialize_public_persistence,
)
from lotoia.public.services.lead_capture_service import (
    LeadCaptureRequest,
    LeadCaptureService,
    hash_ip,
    normalize_whatsapp,
)

MAX_PUBLIC_GAMES = 2
PUBLIC_STRATEGY = "public_hybrid_statistical_v1"

metrics_registry = MetricsRegistry()
structured_logger = StructuredLogger(service="lotoia-public")


class PublicGenerationRequest(LeadCaptureRequest):
    ml_enabled: bool = False


class PublicCheckRequest(LeadCaptureRequest):
    contest_id: int = Field(gt=0)
    numbers: list[int] = Field(min_length=15, max_length=15)

    @field_validator("numbers")
    @classmethod
    def validate_numbers(cls, value: list[int]) -> list[int]:
        if len(set(value)) != 15:
            raise ValueError("numbers must contain 15 unique values.")
        if any(number < 1 or number > 25 for number in value):
            raise ValueError("numbers must be between 1 and 25.")
        return sorted(value)


@dataclass
class PublicLimiter:
    cooldown_seconds: float = 1.0
    max_requests_per_window: int = 5
    window_seconds: float = 60.0
    _requests: dict[str, list[float]] = field(default_factory=dict)

    def check(self, key: str, *, now: float | None = None) -> tuple[bool, str]:
        current = time.monotonic() if now is None else now
        recent = [
            observed
            for observed in self._requests.get(key, [])
            if current - observed <= self.window_seconds
        ]
        if recent and current - recent[-1] < self.cooldown_seconds:
            return False, "cooldown"
        if len(recent) >= self.max_requests_per_window:
            return False, "rate_limit"
        recent.append(current)
        self._requests[key] = recent
        return True, "ok"


limiter = PublicLimiter()


def generate_public_games(
    request: PublicGenerationRequest,
    *,
    ip_address: str = "",
    user_agent: str = "",
    source: str = "public_api",
    db_path: Path = DEFAULT_DATABASE_PATH,
    limiter_key: str | None = None,
    active_limiter: PublicLimiter = limiter,
) -> dict[str, Any]:
    initialize_public_persistence(db_path)
    generation_repository = GenerationEventRepository(db_path)
    lead_service = LeadCaptureService(db_path)
    start = time.perf_counter()
    key = limiter_key or _limiter_key(ip_address, request.whatsapp)
    allowed, reason = active_limiter.check(key)
    if not allowed:
        _record_limiter_event("generate", reason)
        raise PublicRateLimitError(reason)

    seed = random.SystemRandom().randint(1, 2_147_483_647)
    state = random.getstate()
    random.seed(seed)
    try:
        generated = generate_best_games(
            count=MAX_PUBLIC_GAMES,
            pool_size=max(6, MAX_PUBLIC_GAMES),
            ml_enabled=request.ml_enabled,
        )
    finally:
        random.setstate(state)

    games = list(generated["games"])[:MAX_PUBLIC_GAMES]
    ranking_score = _ranking_score(games)
    execution_time_ms = (time.perf_counter() - start) * 1000.0
    lead = _capture_lead(
        request,
        source=source,
        ip_address=ip_address,
        user_agent=user_agent,
        lead_service=lead_service,
    )
    event = generation_repository.insert(
        lead_id=int(lead["id"]),
        generated_games=games,
        ml_enabled=request.ml_enabled,
        seed=seed,
        strategy=PUBLIC_STRATEGY,
        ranking_score=ranking_score,
        execution_time_ms=execution_time_ms,
    )
    _record_success("generate", execution_time_ms)
    structured_logger.info(
        "public_generation_completed",
        source="public_api",
        metadata={"lead_id": lead["id"], "event_id": event["id"], "ml_enabled": request.ml_enabled},
    )
    return {
        "lead_id": lead["id"],
        "event_id": event["id"],
        "games": games,
        "metadata": {
            "count": len(games),
            "max_games": MAX_PUBLIC_GAMES,
            "ml_enabled": request.ml_enabled,
            "seed": seed,
            "strategy": PUBLIC_STRATEGY,
            "ranking_score": ranking_score,
            "execution_time_ms": round(execution_time_ms, 3),
        },
    }


def check_public_contest(
    request: PublicCheckRequest,
    *,
    ip_address: str = "",
    user_agent: str = "",
    source: str = "public_api",
    db_path: Path = DEFAULT_DATABASE_PATH,
    history_path: Path = DEFAULT_HISTORY_PATH,
    limiter_key: str | None = None,
    active_limiter: PublicLimiter = limiter,
) -> dict[str, Any]:
    initialize_public_persistence(db_path)
    check_repository = CheckEventRepository(db_path)
    lead_service = LeadCaptureService(db_path)
    start = time.perf_counter()
    key = limiter_key or _limiter_key(ip_address, request.whatsapp)
    allowed, reason = active_limiter.check(key)
    if not allowed:
        _record_limiter_event("check", reason)
        raise PublicRateLimitError(reason)

    draw = _find_contest(request.contest_id, history_path)
    selected = set(request.numbers)
    drawn = set(draw.numbers)
    correct_numbers = sorted(selected & drawn)
    result_payload = {
        "contest_id": draw.contest,
        "draw_date": draw.date,
        "drawn_numbers": draw.numbers,
        "selected_numbers": request.numbers,
        "correct_numbers": correct_numbers,
        "hits": len(correct_numbers),
    }
    lead = _capture_lead(
        request,
        source=source,
        ip_address=ip_address,
        user_agent=user_agent,
        lead_service=lead_service,
    )
    event = check_repository.insert(
        lead_id=int(lead["id"]),
        contest_id=request.contest_id,
        selected_numbers=request.numbers,
        hits=len(correct_numbers),
        result_payload=result_payload,
    )
    execution_time_ms = (time.perf_counter() - start) * 1000.0
    _record_success("check", execution_time_ms)
    structured_logger.info(
        "public_check_completed",
        source="public_api",
        metadata={"lead_id": lead["id"], "event_id": event["id"], "contest_id": request.contest_id},
    )
    return {
        "lead_id": lead["id"],
        "event_id": event["id"],
        "hits": len(correct_numbers),
        "correct_numbers": correct_numbers,
        "result": result_payload,
        "metadata": {
            "strategy": "readonly_contest_check_v1",
            "execution_time_ms": round(execution_time_ms, 3),
        },
    }


class PublicRateLimitError(RuntimeError):
    pass


def _capture_lead(
    request: LeadCaptureRequest,
    *,
    source: str,
    ip_address: str,
    user_agent: str,
    lead_service: LeadCaptureService,
) -> dict[str, Any]:
    result = lead_service.capture(
        request.model_copy(update={"source": source}),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return result.lead


def _limiter_key(ip_address: str, whatsapp: str) -> str:
    return hash_ip(f"{ip_address}:{normalize_whatsapp(whatsapp)}")


def _ranking_score(games: list[dict[str, Any]]) -> float:
    if not games:
        return 0.0
    scores = [
        float(game.get("final_score", {}).get("final_score", 0.0))
        for game in games
    ]
    return sum(scores) / len(scores)


def _find_contest(contest_id: int, history_path: Path):
    for draw in load_draws_csv(history_path):
        if draw.contest == contest_id:
            return draw
    raise PublicContestNotFoundError(f"Contest {contest_id} not found.")


class PublicContestNotFoundError(ValueError):
    pass


def _record_success(operation: str, execution_time_ms: float) -> None:
    metrics_registry.increment("public.request.count", labels={"operation": operation, "status": "ok"})
    metrics_registry.timing("public.request.latency_ms", execution_time_ms, labels={"operation": operation})


def _record_limiter_event(operation: str, reason: str) -> None:
    metrics_registry.increment(
        "public.limiter.count",
        labels={"operation": operation, "reason": reason},
    )
    structured_logger.warning(
        "public_limiter_blocked",
        source="public_api",
        metadata={"operation": operation, "reason": reason},
    )
