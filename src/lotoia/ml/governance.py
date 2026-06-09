from __future__ import annotations

from typing import Any

from .rerank import rerank_games
from .score_ml import InterpretableLinearScoreML


def activate_score_ml_runtime(
    games: list[dict[str, Any]],
    *,
    enabled: bool = False,
    model: InterpretableLinearScoreML | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Governed activation of the incremental score_ml layer.

    The hybrid ranking remains authoritative; this helper only attaches
    score_ml metadata when enabled and returns an auditable activation summary.
    """

    reranked = rerank_games(games, enabled=enabled, model=model)
    scored_games = [game for game in reranked if "score_ml" in game]
    score_values = [float(game["score_ml"]) for game in scored_games]
    summary = {
        "enabled": bool(enabled),
        "activated": bool(enabled and scored_games),
        "scored_count": len(scored_games),
        "model_version": getattr(model, "model_version", "historical_recalibrated_v2"),
        "hybrid_ranking_preserved": True,
        "score_ml_min": min(score_values) if score_values else 0.0,
        "score_ml_max": max(score_values) if score_values else 0.0,
    }
    return reranked, summary
