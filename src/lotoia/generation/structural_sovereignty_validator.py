"""M-SANITY-001 — Filtro de Soberania Oficial (tolerância zero ao vazio estatístico)."""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from lotoia.generation.m_core_003_prefix_suffix_policy import historical_freq_pct
from lotoia.statistics.card_structure import (
    compute_prefix,
    compute_suffix,
    format_dezena_group,
    resolve_cartao_final_from_game,
)

logger = logging.getLogger(__name__)

MISSION_ID = "M-SANITY-001"
DEFAULT_OFFICIAL_WINDOW = 3000
MIN_BASELINE_CONTESTS = 50
LOG_PREFIX = "[LEI15_SANITY]"


@dataclass
class OfficialStructuralBaseline:
    """Frequências observadas na base histórica oficial (janela configurável)."""

    contests_used: int = 0
    prefix3: Counter[str] = field(default_factory=Counter)
    prefix4: Counter[str] = field(default_factory=Counter)
    suffix3: Counter[str] = field(default_factory=Counter)
    suffix4: Counter[str] = field(default_factory=Counter)


def _extract_numbers_from_draw(draw: object) -> list[int]:
    if isinstance(draw, Sequence) and not isinstance(draw, (str, bytes, bytearray)):
        try:
            numbers = [int(value) for value in draw if 1 <= int(value) <= 25]
            if len(numbers) >= 15:
                return sorted(set(numbers))
        except (TypeError, ValueError):
            pass

    raw = getattr(draw, "numbers", None)
    if raw is None and isinstance(draw, Mapping):
        raw = draw.get("numbers")
    if raw is None:
        return []
    numbers = [int(value) for value in list(raw or []) if 1 <= int(value) <= 25]
    return sorted(set(numbers))


def build_official_structural_baseline(
    official_history: Sequence[object],
    *,
    window: int = DEFAULT_OFFICIAL_WINDOW,
) -> OfficialStructuralBaseline:
    """Constrói perfil estrutural a partir dos concursos oficiais."""
    baseline = OfficialStructuralBaseline()
    cards: list[list[int]] = []
    for draw in list(official_history)[-max(1, int(window)) :]:
        numbers = _extract_numbers_from_draw(draw)
        if len(numbers) == 15:
            cards.append(numbers)
    baseline.contests_used = len(cards)
    for card in cards:
        baseline.prefix3[format_dezena_group(compute_prefix(card, 3))] += 1
        baseline.prefix4[format_dezena_group(compute_prefix(card, 4))] += 1
        baseline.suffix3[format_dezena_group(compute_suffix(card, 3))] += 1
        baseline.suffix4[format_dezena_group(compute_suffix(card, 4))] += 1
    return baseline


def _is_official_statistical_void(
    kind: str,
    pattern: str,
    counter: Counter[str],
    baseline: OfficialStructuralBaseline,
    *,
    min_baseline_contests: int = MIN_BASELINE_CONTESTS,
) -> bool:
    if not pattern:
        return False

    observed = int(counter.get(pattern, 0) or 0)
    if observed > 0:
        return False

    if baseline.contests_used >= min_baseline_contests:
        return True

    if kind == "prefix_3":
        return historical_freq_pct(pattern, kind="prefix") <= 0
    if kind == "suffix_3":
        return historical_freq_pct(pattern, kind="suffix") <= 0
    return False


def _game_sort_key(game: Mapping[str, Any]) -> tuple[float, float]:
    return (
        -float(game.get("profile_score", 0) or 0),
        -float(game.get("final_score", {}).get("final_score", 0) or 0),
    )


def validate_structural_sovereignty(
    game: Mapping[str, Any],
    official_history: Sequence[object] | OfficialStructuralBaseline,
    *,
    baseline_window: int = DEFAULT_OFFICIAL_WINDOW,
    min_baseline_contests: int = MIN_BASELINE_CONTESTS,
) -> dict[str, Any]:
    """Valida cartão contra histórico oficial — hard block em padrões com freq. zero."""
    if isinstance(official_history, OfficialStructuralBaseline):
        baseline = official_history
    else:
        baseline = build_official_structural_baseline(official_history, window=baseline_window)

    numbers = resolve_cartao_final_from_game(dict(game))
    if len(numbers) < 15:
        return {
            "valid": False,
            "mission_id": MISSION_ID,
            "reason": "invalid_card_size",
            "violations": [],
        }

    violations: list[dict[str, str]] = []
    checks: list[tuple[str, str, Counter[str]]] = [
        ("prefix_3", format_dezena_group(compute_prefix(numbers, 3)), baseline.prefix3),
        ("suffix_3", format_dezena_group(compute_suffix(numbers, 3)), baseline.suffix3),
    ]
    for kind, pattern, counter in checks:
        if _is_official_statistical_void(
            kind,
            pattern,
            counter,
            baseline,
            min_baseline_contests=min_baseline_contests,
        ):
            violations.append({"kind": kind, "pattern": pattern})

    if violations:
        primary = violations[0]
        pattern_label = primary.get("pattern", "")
        kind_label = primary.get("kind", "pattern")
        if kind_label.startswith("prefix"):
            discard_label = f"Prefixo: {pattern_label}"
        elif kind_label.startswith("suffix"):
            discard_label = f"Sufixo: {pattern_label}"
        else:
            discard_label = f"{kind_label}: {pattern_label}"
        logger.warning(
            "%s Jogo descartado por vazio estatístico oficial (%s)",
            LOG_PREFIX,
            discard_label,
        )
        return {
            "valid": False,
            "mission_id": MISSION_ID,
            "reason": "official_statistical_void",
            "violations": violations,
            "discard_label": discard_label,
            "official_contests_used": baseline.contests_used,
        }

    return {
        "valid": True,
        "mission_id": MISSION_ID,
        "violations": [],
        "official_contests_used": baseline.contests_used,
    }


def apply_structural_sovereignty_to_gp(
    games: list[dict],
    pool: list[dict],
    count: int,
    official_history: Sequence[object] | OfficialStructuralBaseline,
    *,
    fallback_pool: list[dict] | None = None,
    baseline_window: int = DEFAULT_OFFICIAL_WINDOW,
    min_baseline_contests: int = MIN_BASELINE_CONTESTS,
) -> tuple[list[dict], dict[str, Any]]:
    """Filtra GP inválido e recompõe com substitutos do pool (tolerância zero)."""
    if isinstance(official_history, OfficialStructuralBaseline):
        baseline = official_history
    else:
        baseline = build_official_structural_baseline(official_history, window=baseline_window)

    discard_counts: Counter[str] = Counter()
    selected: list[dict] = []
    seen: set[tuple[int, ...]] = set()
    discarded_details: list[dict[str, Any]] = []

    def _accept(candidate: Mapping[str, Any], *, replacement: bool = False) -> bool:
        key = tuple(resolve_cartao_final_from_game(dict(candidate)))
        if not key or key in seen:
            return False
        validation = validate_structural_sovereignty(
            candidate,
            baseline,
            min_baseline_contests=min_baseline_contests,
        )
        if not validation.get("valid"):
            for violation in list(validation.get("violations") or []):
                discard_counts[str(violation.get("kind") or "unknown")] += 1
            discarded_details.append(
                {
                    "numbers": list(key),
                    "replacement": replacement,
                    "violations": list(validation.get("violations") or []),
                    "discard_label": validation.get("discard_label"),
                }
            )
            return False
        enriched = dict(candidate)
        enriched["structural_sovereignty_validated"] = True
        enriched["structural_sovereignty_mission_id"] = MISSION_ID
        if replacement:
            enriched["structural_sovereignty_replacement"] = True
        selected.append(enriched)
        seen.add(key)
        return True

    for game in games:
        if len(selected) >= count:
            break
        _accept(game)

    if len(selected) < count:
        completion_sources = [
            list(pool or []),
            list(fallback_pool or []),
        ]
        for source in completion_sources:
            if len(selected) >= count:
                break
            for candidate in sorted(source, key=_game_sort_key):
                if len(selected) >= count:
                    break
                _accept(candidate, replacement=True)

    bundle = {
        "mission_id": MISSION_ID,
        "applied": True,
        "target_count": int(count),
        "delivered_count": len(selected),
        "discarded_count": len(discarded_details),
        "discard_counts_by_kind": dict(discard_counts),
        "discarded_details": discarded_details[:25],
        "official_contests_used": baseline.contests_used,
    }
    return selected[:count], bundle
