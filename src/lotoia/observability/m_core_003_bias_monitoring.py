"""M-CORE-003 — monitoramento contínuo de viés prefixo/sufixo (razão gerado/histórico)."""

from __future__ import annotations

import math
from typing import Any, Literal, Sequence

from lotoia.database.database import GeneratedGame, get_session
from lotoia.generation.m_core_003_prefix_suffix_policy import (
    HISTORICAL_PREFIX_FREQ_PCT,
    HISTORICAL_SUFFIX_FREQ_PCT,
    MISSION_ID,
    compare_pattern_ratios,
    compute_pattern_distribution,
)
from lotoia.statistics.card_structure import resolve_cartao_final_from_game

PatternKind = Literal["prefix", "suffix"]

MODERATE_BIAS_RATIO_THRESHOLD = 2.0
SEVERE_BIAS_RATIO_THRESHOLD = 3.0
WATCHLIST_PATTERN = "03-04-05"
WATCHLIST_RATIO_THRESHOLD = 3.5


def compute_normalized_pattern_entropy(distribution: dict[str, float]) -> float:
    """Entropia de Shannon normalizada (0–1) sobre a distribuição de padrões."""
    values = [float(value) for value in distribution.values() if float(value) > 0]
    if len(values) <= 1:
        return 0.0
    total = sum(values)
    if total <= 0:
        return 0.0
    entropy = 0.0
    for value in values:
        share = value / total
        entropy -= share * math.log2(share)
    max_entropy = math.log2(len(values))
    return round(entropy / max_entropy, 3) if max_entropy else 0.0


def _count_bias_levels(
    generated_pct: dict[str, float],
    historical_pct: dict[str, float],
) -> dict[str, int]:
    moderate = 0
    severe = 0
    for pattern, generated in generated_pct.items():
        baseline = float(historical_pct.get(pattern, 0.0) or 0.0)
        if baseline <= 0:
            continue
        ratio = float(generated) / baseline
        if ratio >= SEVERE_BIAS_RATIO_THRESHOLD:
            severe += 1
        elif ratio >= MODERATE_BIAS_RATIO_THRESHOLD:
            moderate += 1
    return {
        "moderate_bias_count": moderate,
        "severe_bias_count": severe,
    }


def build_pattern_ratio_rows(
    generated_pct: dict[str, float],
    historical_pct: dict[str, float],
    *,
    kind: PatternKind,
    ratio_threshold: float = 1.0,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pattern, generated in sorted(generated_pct.items(), key=lambda item: item[1], reverse=True):
        baseline = float(historical_pct.get(pattern, 0.0) or 0.0)
        if baseline <= 0:
            continue
        ratio = round(float(generated) / baseline, 2)
        if ratio < ratio_threshold:
            continue
        rows.append(
            {
                "kind": kind,
                "pattern": pattern,
                "generated_pct": round(float(generated), 2),
                "historical_pct": round(baseline, 2),
                "ratio": ratio,
                "severity": (
                    "severo"
                    if ratio >= SEVERE_BIAS_RATIO_THRESHOLD
                    else "moderado"
                    if ratio >= MODERATE_BIAS_RATIO_THRESHOLD
                    else "observável"
                ),
            }
        )
    rows.sort(key=lambda row: float(row["ratio"]), reverse=True)
    return rows


def build_m_core_003_bias_monitoring_report(
    cards: Sequence[Sequence[int]],
    *,
    games_count: int | None = None,
    generation_event_ids: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Monta scorecard M-CORE-003 para jogos operacionais persistidos."""
    normalized_cards = [
        [int(value) for value in card]
        for card in cards
        if len([int(value) for value in card]) >= 15
    ]
    total_games = int(games_count or len(normalized_cards) or 0)
    if total_games <= 0:
        return {
            "mission_id": MISSION_ID,
            "available": False,
            "games_count": 0,
            "reason": "no_valid_cards",
        }

    generated_prefix = compute_pattern_distribution(normalized_cards, kind="prefix")
    generated_suffix = compute_pattern_distribution(normalized_cards, kind="suffix")
    prefix_levels = _count_bias_levels(generated_prefix, HISTORICAL_PREFIX_FREQ_PCT)
    suffix_levels = _count_bias_levels(generated_suffix, HISTORICAL_SUFFIX_FREQ_PCT)

    prefix_over_moderate = compare_pattern_ratios(
        generated_prefix,
        HISTORICAL_PREFIX_FREQ_PCT,
        ratio_threshold=MODERATE_BIAS_RATIO_THRESHOLD,
    )
    suffix_over_moderate = compare_pattern_ratios(
        generated_suffix,
        HISTORICAL_SUFFIX_FREQ_PCT,
        ratio_threshold=MODERATE_BIAS_RATIO_THRESHOLD,
    )
    prefix_over_severe = compare_pattern_ratios(
        generated_prefix,
        HISTORICAL_PREFIX_FREQ_PCT,
        ratio_threshold=SEVERE_BIAS_RATIO_THRESHOLD,
    )
    suffix_over_severe = compare_pattern_ratios(
        generated_suffix,
        HISTORICAL_SUFFIX_FREQ_PCT,
        ratio_threshold=SEVERE_BIAS_RATIO_THRESHOLD,
    )

    watchlist_row = next(
        (
            row
            for row in build_pattern_ratio_rows(
                generated_prefix,
                HISTORICAL_PREFIX_FREQ_PCT,
                kind="prefix",
                ratio_threshold=1.0,
            )
            if row["pattern"] == WATCHLIST_PATTERN
        ),
        None,
    )
    watchlist_ratio = float(watchlist_row["ratio"]) if watchlist_row else 0.0

    severe_total = int(prefix_levels["severe_bias_count"] + suffix_levels["severe_bias_count"])
    moderate_total = int(prefix_levels["moderate_bias_count"] + suffix_levels["moderate_bias_count"])
    entropy_prefix = compute_normalized_pattern_entropy(generated_prefix)
    entropy_suffix = compute_normalized_pattern_entropy(generated_suffix)

    if severe_total > 0:
        verdict = "VIÉS SEVERO DETECTADO — revisar calibração"
        compliance = False
    elif moderate_total > 0:
        verdict = "VIÉS MODERADO — monitorar"
        compliance = False
    elif watchlist_ratio >= WATCHLIST_RATIO_THRESHOLD:
        verdict = f"WATCHLIST {WATCHLIST_PATTERN} acima de {WATCHLIST_RATIO_THRESHOLD}x"
        compliance = False
    else:
        verdict = "M-CORE-003 ALINHADO"
        compliance = True

    return {
        "mission_id": MISSION_ID,
        "available": True,
        "games_count": total_games,
        "generation_event_ids": [int(value) for value in (generation_event_ids or []) if int(value) > 0],
        "distinct_prefix_patterns": len(generated_prefix),
        "distinct_suffix_patterns": len(generated_suffix),
        "entropy_prefix": entropy_prefix,
        "entropy_suffix": entropy_suffix,
        "moderate_bias_count": moderate_total,
        "severe_bias_count": severe_total,
        "prefix_moderate_bias_count": int(prefix_levels["moderate_bias_count"]),
        "suffix_moderate_bias_count": int(suffix_levels["moderate_bias_count"]),
        "prefix_severe_bias_count": int(prefix_levels["severe_bias_count"]),
        "suffix_severe_bias_count": int(suffix_levels["severe_bias_count"]),
        "prefix_patterns_over_moderate": prefix_over_moderate,
        "suffix_patterns_over_moderate": suffix_over_moderate,
        "prefix_patterns_over_severe": prefix_over_severe,
        "suffix_patterns_over_severe": suffix_over_severe,
        "watchlist_pattern": WATCHLIST_PATTERN,
        "watchlist_ratio": watchlist_ratio,
        "watchlist_threshold": WATCHLIST_RATIO_THRESHOLD,
        "critical_pattern_01_04_06": next(
            (row for row in prefix_over_moderate if row["pattern"] == "01-04-06"),
            None,
        ),
        "ratio_rows": build_pattern_ratio_rows(
            generated_prefix,
            HISTORICAL_PREFIX_FREQ_PCT,
            kind="prefix",
            ratio_threshold=MODERATE_BIAS_RATIO_THRESHOLD,
        )
        + build_pattern_ratio_rows(
            generated_suffix,
            HISTORICAL_SUFFIX_FREQ_PCT,
            kind="suffix",
            ratio_threshold=MODERATE_BIAS_RATIO_THRESHOLD,
        ),
        "compliance": compliance,
        "verdict": verdict,
    }


def load_operational_cards_for_bias_monitoring(
    db_path: Any,
    *,
    generation_event_ids: Sequence[int] | None = None,
) -> tuple[list[list[int]], list[int]]:
    """Carrega cartões 15D persistidos para monitoramento M-CORE-003."""
    target_ids = sorted({int(value) for value in (generation_event_ids or []) if int(value) > 0})
    cards: list[list[int]] = []
    resolved_ids: list[int] = []
    with get_session(db_path) as session:
        query = session.query(GeneratedGame).order_by(
            GeneratedGame.generation_event_id.asc(),
            GeneratedGame.game_index.asc(),
        )
        if target_ids:
            query = query.filter(GeneratedGame.generation_event_id.in_(target_ids))
        for row in query.all():
            ge_id = int(getattr(row, "generation_event_id", 0) or 0)
            payload = {
                "numbers": list(getattr(row, "numbers", []) or []),
                "context_json": dict(getattr(row, "context_json", {}) or {}),
                "final_score": dict(getattr(row, "final_score", {}) or {}),
            }
            numbers = resolve_cartao_final_from_game(payload)
            if len(numbers) < 15:
                continue
            cards.append([int(value) for value in numbers])
            if ge_id > 0 and ge_id not in resolved_ids:
                resolved_ids.append(ge_id)
    return cards, resolved_ids


def build_m_core_003_bias_monitoring_report_from_db(
    db_path: Any,
    *,
    generation_event_ids: Sequence[int] | None = None,
) -> dict[str, Any]:
    cards, resolved_ids = load_operational_cards_for_bias_monitoring(
        db_path,
        generation_event_ids=generation_event_ids,
    )
    return build_m_core_003_bias_monitoring_report(
        cards,
        games_count=len(cards),
        generation_event_ids=resolved_ids,
    )
