from __future__ import annotations

from typing import Any

from lotoia.ml.score_ml import InterpretableLinearScoreML, attach_score_ml, supervised_rerank_games

__all__ = ["rerank_games", "supervised_rerank_games"]


def rerank_games(
    games: list[dict[str, Any]],
    *,
    enabled: bool = False,
    model: InterpretableLinearScoreML | None = None,
) -> list[dict[str, Any]]:
    """Attach the official incremental score_ml layer without replacing hybrid ranking.

    The generator still performs its primary ordering by final_score/quadra_score.
    Explicit supervised reranking is available through supervised_rerank_games.
    """
    for g in games:
        g["ml_enabled"] = bool(enabled)
        if enabled:
            attach_score_ml(g, model=model)
    return games
