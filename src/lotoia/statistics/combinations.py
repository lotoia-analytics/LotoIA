from __future__ import annotations

from collections import Counter
from itertools import combinations


def combo_stats(
    draws,
    combo_size: int,
) -> dict[tuple[int, ...], dict[str, float | int]]:
    counts: Counter[tuple[int, ...]] = Counter()
    for draw in draws:
        counts.update(combinations(draw.numbers, combo_size))

    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return {
        combo: {"count": count, "rank": rank}
        for rank, (combo, count) in enumerate(ordered, start=1)
    }


def combo_score(
    numbers: list[int],
    combo_size: int,
    stats: dict[tuple[int, ...], dict[str, float | int]],
) -> dict[str, float | int]:
    found = []
    for combo in combinations(numbers, combo_size):
        combo_data = stats.get(combo)
        if combo_data:
            found.append(combo_data)

    found_count = len(found)
    total_count = sum(int(item["count"]) for item in found)
    total_rank = sum(int(item["rank"]) for item in found)
    return {
        "found": found_count,
        "total_count": total_count,
        "average_count": total_count / found_count if found_count else 0,
        "average_rank": total_rank / found_count if found_count else 0,
    }


def rank_component_score(average_rank: float, rank_count: int) -> float:
    if average_rank <= 0:
        return 0

    normalized = 1 - ((average_rank - 1) / max(rank_count - 1, 1))
    return max(0, min(100, normalized * 100))
