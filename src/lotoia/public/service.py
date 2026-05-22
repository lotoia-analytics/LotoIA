from __future__ import annotations

import random
import time
from collections import deque
from pathlib import Path
from typing import Any
from uuid import uuid4

from lotoia.data.loader import DEFAULT_HISTORY_PATH, load_draws_csv
from lotoia.generator.engine import generate_ranked_games
from lotoia.ml import activate_score_ml_runtime
from lotoia.database.public_repository import save_check_event
from lotoia.public.persistence import GenerationEventRepository, LeadRepository, initialize_public_persistence
from lotoia.public.models import PublicCheckRequest, PublicGenerationRequest
from lotoia.observability import MetricsRegistry, ObservabilityRepository, ObservabilityTracer


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
    execution_id = f"exec-{uuid4().hex}"
    observability_repository = ObservabilityRepository(db_path) if db_path is not None else None
    observability = ObservabilityTracer(observability_repository) if observability_repository is not None else None
    metrics = MetricsRegistry()
    if observability is not None:
        observability.start_execution(
            flow_name="generation",
            stage="generation",
            context={"source": source, "target_contest": target_contest, "ml_enabled": bool(request.ml_enabled)},
            execution_id=execution_id,
        )
    generation_span = observability.tracer.start_span("generate_public_games", trace_id=execution_id, attributes={"flow": "generation"}) if observability is not None else None
    games_payload = generate_ranked_games(total_games=2, seed=seed, ml_enabled=request.ml_enabled)
    games_payload, score_ml_runtime = activate_score_ml_runtime(games_payload, enabled=request.ml_enabled)
    execution_time_ms = (time.time() - started_at) * 1000
    if observability is not None:
        observability.record_metric(execution_id, metrics.timing("runtime_latency_ms", execution_time_ms), stage="generation")
        observability.record_lineage(
            execution_id,
            entity_type="generation_event",
            entity_id=str(seed),
            event_type="generator_completed",
            payload={
                "target_contest": target_contest,
                "ml_enabled": bool(request.ml_enabled),
                "score_ml_runtime": score_ml_runtime,
            },
        )
        if generation_span is not None:
            finished_generation_span = observability.tracer.finish_span(
                generation_span.span_id,
                status="ok",
                attributes={"execution_time_ms": round(execution_time_ms, 2)},
            )
            observability_repository.record_span(execution_id, finished_generation_span, stage="generation")
            observability.finish_execution(
                execution_id,
                status="ok",
                stage="generation",
                duration_ms=round(execution_time_ms, 2),
                context={"source": source, "target_contest": target_contest},
            )
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
            first_name=str(lead["first_name"]),
            whatsapp=str(lead["whatsapp"]),
            context={
                "source": source,
                "user_agent": user_agent,
                "target_contest": target_contest,
                "ml_enabled": bool(request.ml_enabled),
                "execution_id": execution_id,
            },
        )
        if observability is not None:
            observability.record_snapshot(
                execution_id,
                snapshot_type="generation",
                payload={
                    "games": games_payload,
                    "metadata": {
                        "seed": seed,
                        "target_contest": target_contest,
                    },
                },
                metadata={"flow_name": "generation"},
            )
    return {
        "games": games_payload,
        "metadata": {
            "execution_id": execution_id,
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
            "score_ml_runtime": score_ml_runtime,
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
    execution_id = f"exec-{uuid4().hex}"
    observability_repository = ObservabilityRepository(db_path) if db_path is not None else None
    observability = ObservabilityTracer(observability_repository) if observability_repository is not None else None
    metrics = MetricsRegistry()
    if observability is not None:
        observability.start_execution(
            flow_name="check",
            stage="check",
            context={"source": source, "contest_id": request.contest_id},
            execution_id=execution_id,
        )
    check_span = observability.tracer.start_span("check_public_contest", trace_id=execution_id, attributes={"flow": "check"}) if observability is not None else None
    draw = _find_contest(request.contest_id, history_path)
    correct_numbers = sorted(draw.numbers)
    checked_numbers = sorted(request.numbers)
    hits = len(set(correct_numbers) & set(checked_numbers))
    execution_time_ms = (time.time() - started_at) * 1000
    if observability is not None:
        observability.record_metric(execution_id, metrics.timing("runtime_latency_ms", execution_time_ms), stage="check")
        observability.record_lineage(
            execution_id,
            entity_type="check_event",
            entity_id=str(request.contest_id),
            event_type="checker_completed",
            payload={"hits": hits},
        )
        if check_span is not None:
            finished_check_span = observability.tracer.finish_span(
                check_span.span_id,
                status="ok",
                attributes={"execution_time_ms": round(execution_time_ms, 2)},
            )
            observability_repository.record_span(execution_id, finished_check_span, stage="check")
            observability.finish_execution(
                execution_id,
                status="ok",
                stage="check",
                duration_ms=round(execution_time_ms, 2),
                context={"source": source, "contest_id": request.contest_id},
            )
    if db_path is not None:
        initialize_public_persistence(db_path)
        lead_repository = LeadRepository(db_path)
        lead = lead_repository.find_by_first_name_and_whatsapp(request.first_name.strip(), request.whatsapp)
        if lead is None:
            lead = lead_repository.insert(
                first_name=request.first_name.strip(),
                whatsapp=request.whatsapp,
                source=source,
                ip_hash="",
                user_agent=user_agent,
            )
        save_check_event(
            lead_id=int(lead["id"]),
            contest_id=request.contest_id,
            selected_numbers=checked_numbers,
            hits=hits,
            result_payload={
                "contest_id": request.contest_id,
                "execution_time_ms": round(execution_time_ms, 2),
                "source": source,
                "user_agent": user_agent,
                "execution_id": execution_id,
                "correct_numbers": correct_numbers,
                "selected_numbers": checked_numbers,
                "hits": hits,
            },
            db_path=db_path,
        )
    return {
        "hits": hits,
        "correct_numbers": correct_numbers,
        "result": {
            "contest_id": request.contest_id,
            "execution_time_ms": round(execution_time_ms, 2),
            "source": source,
            "user_agent": user_agent,
            "execution_id": execution_id,
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
