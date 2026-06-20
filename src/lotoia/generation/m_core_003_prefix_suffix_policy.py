"""M-CORE-003 — política anti-viés de prefixo/sufixo (freq histórica Lotofácil)."""

from __future__ import annotations

import math
from collections import Counter
from typing import Final, Literal, Sequence

from lotoia.generation.lei15_core_structural_payload import compute_structural_signatures

MISSION_ID: Final = "M-CORE-003"
EVIDENCE_EPOCH: Final = "EPOCH_002_M_CORE_003"

# Frequências históricas (3.714 concursos oficiais — freq >= 1% no allowlist).
HISTORICAL_PREFIX_FREQ_PCT: Final[dict[str, float]] = {
    "01-02-03": 20.09,
    "01-02-04": 9.34,
    "01-03-04": 9.13,
    "02-03-04": 8.99,
    "01-02-05": 3.90,
    "01-03-05": 4.17,
    "02-03-05": 3.50,
    "01-04-05": 3.74,
    "02-04-05": 3.93,
    "03-04-05": 4.09,
    "01-02-06": 1.48,
    "01-03-06": 1.43,
    "02-03-06": 1.40,
    "01-04-06": 1.40,
    "02-04-06": 1.45,
    "03-04-06": 1.70,
    "02-05-06": 1.53,
    "03-05-06": 1.51,
    "01-05-06": 1.37,
    "01-05-07": 0.48,
}

HISTORICAL_SUFFIX_FREQ_PCT: Final[dict[str, float]] = {
    "23-24-25": 20.87,
    "22-24-25": 9.75,
    "22-23-25": 8.56,
    "22-23-24": 8.10,
    "21-24-25": 3.80,
    "21-22-25": 4.20,
    "21-23-25": 3.85,
    "21-23-24": 3.23,
    "21-22-24": 4.17,
    "21-22-23": 3.77,
    "20-24-25": 1.70,
    "20-23-25": 1.51,
    "20-22-25": 1.67,
    "20-22-24": 1.86,
    "20-22-23": 1.27,
    "20-21-25": 2.15,
    "20-21-24": 1.37,
    "20-21-23": 1.59,
    "20-23-24": 1.62,
    "19-23-24": 0.65,
}

ALLOWED_PREFIXES: Final[frozenset[str]] = frozenset(HISTORICAL_PREFIX_FREQ_PCT)
ALLOWED_SUFFIXES: Final[frozenset[str]] = frozenset(HISTORICAL_SUFFIX_FREQ_PCT)

POOL_MAX_PER_PREFIX: Final[int] = 3
POOL_MAX_PER_SUFFIX: Final[int] = 5

PatternKind = Literal["prefix", "suffix"]


def historical_freq_pct(pattern: str, *, kind: PatternKind) -> float:
    normalized = str(pattern or "").strip()
    table = HISTORICAL_PREFIX_FREQ_PCT if kind == "prefix" else HISTORICAL_SUFFIX_FREQ_PCT
    return float(table.get(normalized, 0.0) or 0.0)


def historical_pattern_cap(historical_freq_pct: float, *, gp_size: int = 10) -> int:
    """Cap proporcional à frequência histórica e ao tamanho do lote (M-CORE-003)."""
    freq = float(historical_freq_pct or 0.0)
    size = max(1, int(gp_size or 10))
    expected = size * freq / 100.0
    if freq < 2.0:
        return min(1, int(expected))
    return max(1, math.ceil(expected))


def resolve_pattern_cap(pattern: str, *, kind: PatternKind, gp_size: int = 10) -> int:
    freq = historical_freq_pct(pattern, kind=kind)
    if freq <= 0:
        return 1
    return historical_pattern_cap(freq, gp_size=gp_size)


def is_allowed_prefix(pattern: str) -> bool:
    return str(pattern or "").strip() in ALLOWED_PREFIXES


def is_allowed_suffix(pattern: str) -> bool:
    return str(pattern or "").strip() in ALLOWED_SUFFIXES


def _game_sort_key(game: dict) -> tuple[float, float]:
    return (
        -float(game.get("profile_score", 0) or 0),
        -float(game.get("final_score", {}).get("final_score", 0) or 0),
    )


def _game_key(game: dict) -> tuple[int, ...]:
    return tuple(int(n) for n in (game.get("numbers") or []))


def _pattern_signatures(game: dict) -> tuple[str, str]:
    prefix = str(game.get("prefix_signature") or "").strip()
    suffix = str(game.get("suffix_signature") or "").strip()
    if prefix and suffix:
        return prefix, suffix
    sig = compute_structural_signatures(list(game.get("numbers") or []))
    return str(sig.get("prefix_signature") or ""), str(sig.get("suffix_signature") or "")


def pre_filter_pool_diversity(pool: list[dict], *, gp_size: int = 10) -> list[dict]:
    """Filtra pool bruto — allowlist histórica (concentração no fechamento do GP)."""
    if not pool:
        return []
    allowlist_only = _allowlist_only_pool(pool)
    return allowlist_only or list(pool)


def _allowlist_only_pool(pool: list[dict]) -> list[dict]:
    allowed: list[dict] = []
    for game in pool:
        prefix, suffix = _pattern_signatures(game)
        if is_allowed_prefix(prefix) and is_allowed_suffix(suffix):
            allowed.append(game)
    return allowed or list(pool)


def enforce_gp_diversity_cap(
    games: list[dict],
    pool: list[dict],
    count: int,
    *,
    fallback_pool: list[dict] | None = None,
) -> list[dict]:
    """Hard-cap final no GP — cap proporcional à frequência histórica."""
    if count <= 0:
        return []
    if not games and not pool and not fallback_pool:
        return []

    prefix_counts: Counter[str] = Counter()
    suffix_counts: Counter[str] = Counter()
    selected: list[dict] = []
    seen: set[tuple[int, ...]] = set()

    def _fits_caps(prefix: str, suffix: str) -> bool:
        prefix_cap = resolve_pattern_cap(prefix, kind="prefix", gp_size=count)
        suffix_cap = resolve_pattern_cap(suffix, kind="suffix", gp_size=count)
        return prefix_counts[prefix] < prefix_cap and suffix_counts[suffix] < suffix_cap

    def _accept(game: dict, *, completion: bool = False) -> bool:
        key = _game_key(game)
        if not key or key in seen:
            return False
        prefix, suffix = _pattern_signatures(game)
        if not prefix or not suffix:
            return False
        if not _fits_caps(prefix, suffix):
            return False
        enriched = dict(game)
        if completion:
            enriched["gp_diversity_cap_completion"] = True
        enriched["m_core_003_gp_diversity_cap_applied"] = True
        selected.append(enriched)
        seen.add(key)
        prefix_counts[prefix] += 1
        suffix_counts[suffix] += 1
        return True

    for game in sorted(games, key=_game_sort_key):
        if len(selected) >= count:
            break
        _accept(game)

    completion_sources = [
        pre_filter_pool_diversity(pool, gp_size=count),
        _allowlist_only_pool(fallback_pool or []),
        _allowlist_only_pool(pool),
    ]
    for replacement_pool in completion_sources:
        if len(selected) >= count:
            break
        for game in sorted(replacement_pool, key=_game_sort_key):
            if len(selected) >= count:
                break
            _accept(game, completion=True)

    if len(selected) < count:
        relaxed_multiplier = 2

        def _fits_relaxed_caps(prefix: str, suffix: str) -> bool:
            prefix_cap = resolve_pattern_cap(prefix, kind="prefix", gp_size=count) * relaxed_multiplier
            suffix_cap = resolve_pattern_cap(suffix, kind="suffix", gp_size=count) * relaxed_multiplier
            return prefix_counts[prefix] < prefix_cap and suffix_counts[suffix] < suffix_cap

        for replacement_pool in completion_sources:
            if len(selected) >= count:
                break
            for game in sorted(replacement_pool, key=_game_sort_key):
                if len(selected) >= count:
                    break
                key = _game_key(game)
                if not key or key in seen:
                    continue
                prefix, suffix = _pattern_signatures(game)
                if not prefix or not suffix or not _fits_relaxed_caps(prefix, suffix):
                    continue
                enriched = dict(game)
                enriched["gp_diversity_cap_completion"] = True
                enriched["m_core_003_gp_diversity_cap_relaxed"] = True
                enriched["m_core_003_gp_diversity_cap_applied"] = True
                selected.append(enriched)
                seen.add(key)
                prefix_counts[prefix] += 1
                suffix_counts[suffix] += 1

    if len(selected) < count:
        for replacement_pool in completion_sources:
            if len(selected) >= count:
                break
            for game in sorted(replacement_pool, key=_game_sort_key):
                if len(selected) >= count:
                    break
                key = _game_key(game)
                if not key or key in seen:
                    continue
                prefix, suffix = _pattern_signatures(game)
                if not prefix or not suffix:
                    continue
                if resolve_pattern_cap(prefix, kind="prefix", gp_size=count) <= 0:
                    continue
                if resolve_pattern_cap(suffix, kind="suffix", gp_size=count) <= 0:
                    continue
                if not is_allowed_prefix(prefix) or not is_allowed_suffix(suffix):
                    continue
                enriched = dict(game)
                enriched["gp_diversity_cap_completion"] = True
                enriched["m_core_003_gp_diversity_cap_fill"] = True
                enriched["m_core_003_gp_diversity_cap_applied"] = True
                selected.append(enriched)
                seen.add(key)
                prefix_counts[prefix] += 1
                suffix_counts[suffix] += 1

    return selected[:count]


def compute_pattern_distribution(
    cards: Sequence[Sequence[int]],
    *,
    kind: PatternKind,
) -> dict[str, float]:
    """Distribuição percentual de prefixo3/sufixo3 em um conjunto de cartões."""
    counter: Counter[str] = Counter()
    for card in cards:
        numbers = [int(value) for value in card]
        if len(numbers) < 15:
            continue
        sig = compute_structural_signatures(numbers)
        key = str(sig["prefix_signature"] if kind == "prefix" else sig["suffix_signature"])
        counter[key] += 1
    total = sum(counter.values())
    if total <= 0:
        return {}
    return {pattern: round(100.0 * count / total, 2) for pattern, count in counter.items()}


def compute_historical_distribution_from_draws(
    draws: Sequence[object],
    *,
    kind: PatternKind,
) -> dict[str, float]:
    cards = [list(getattr(draw, "numbers", []) or []) for draw in draws]
    return compute_pattern_distribution(cards, kind=kind)


def compare_pattern_ratios(
    generated_pct: dict[str, float],
    historical_pct: dict[str, float],
    *,
    ratio_threshold: float = 2.0,
) -> list[dict[str, object]]:
    """Compara % gerado vs histórico e retorna padrões acima do limiar."""
    rows: list[dict[str, object]] = []
    for pattern, generated in sorted(generated_pct.items()):
        baseline = float(historical_pct.get(pattern, 0.0) or 0.0)
        if baseline <= 0:
            continue
        ratio = round(float(generated) / baseline, 2)
        if ratio >= ratio_threshold:
            rows.append(
                {
                    "pattern": pattern,
                    "generated_pct": float(generated),
                    "historical_pct": baseline,
                    "ratio": ratio,
                }
            )
    rows.sort(key=lambda row: float(row["ratio"]), reverse=True)
    return rows


WALKFORWARD_VALIDATION_SEEDS: Final[tuple[int, ...]] = tuple(1000 + index * 137 for index in range(10))
