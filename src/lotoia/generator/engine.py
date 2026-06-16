from __future__ import annotations

from typing import Any

from lotoia.generator.basic_generator import generate_best_games


def generate_ranked_games(
    total_games: int = 10,
    *,
    seed: int | None = None,
    ml_enabled: bool = False,
    pool_size: int | None = None,
    batch_label: str | None = None,
) -> list[dict[str, Any]]:
    """Compatibility adapter for public runtime callers."""

    resolved_pool_size = pool_size or max(total_games, 30)
    result = generate_best_games(
        count=total_games,
        pool_size=resolved_pool_size,
        ml_enabled=ml_enabled,
        seed=seed,
        batch_label=batch_label,
    )
    return result["games"]
