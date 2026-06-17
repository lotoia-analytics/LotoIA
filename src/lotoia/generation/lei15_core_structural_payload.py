"""Structural signatures and bias scoring for Lei 15 core CDX."""

from __future__ import annotations

from typing import Any

STRONG_V1_SUFFIXES: tuple[tuple[int, ...], ...] = (
    (22, 24, 25),
    (23, 24, 25),
    (18, 24, 25),
)
STRONG_V1_PREFIXES: tuple[tuple[int, ...], ...] = (
    (1, 2, 3),
    (1, 3, 4),
    (1, 3, 6),
    (1, 4, 6),
)

WATCH_PREFIX_PAIRS: tuple[tuple[int, ...], ...] = ((1, 2), (2, 3))
WATCH_SUFFIX_PAIRS: tuple[tuple[int, ...], ...] = ((22, 24), (24, 25), (22, 25))


def _fmt(nums: tuple[int, ...]) -> str:
    return "-".join(f"{n:02d}" for n in nums)


def prefix3(numbers: list[int]) -> tuple[int, ...]:
    return tuple(sorted(numbers)[:3])


def suffix3(numbers: list[int]) -> tuple[int, ...]:
    return tuple(sorted(numbers)[-3:])


def compute_structural_signatures(numbers: list[int]) -> dict[str, Any]:
    nums = sorted(int(n) for n in numbers)
    p3 = prefix3(nums)
    s3 = suffix3(nums)
    pairs_p = [_fmt(p) for p in WATCH_PREFIX_PAIRS if p[0] in nums and p[1] in nums]
    pairs_s = [_fmt(p) for p in WATCH_SUFFIX_PAIRS if p[0] in nums and p[1] in nums]
    return {
        "prefix_signature": _fmt(p3),
        "suffix_signature": _fmt(s3),
        "prefix_pairs": pairs_p,
        "suffix_pairs": pairs_s,
        "has_prefix_123": p3 == (1, 2, 3),
        "has_suffix_222425": s3 == (22, 24, 25),
    }


def is_v1_strong_pattern(numbers: list[int]) -> bool:
    sig = compute_structural_signatures(numbers)
    p3 = prefix3(numbers)
    s3 = suffix3(numbers)
    return p3 in STRONG_V1_PREFIXES or s3 in STRONG_V1_SUFFIXES or (
        sig["has_prefix_123"] and s3 in STRONG_V1_SUFFIXES
    )


def compute_structural_bias_score(
    numbers: list[int],
    *,
    profile_origin: str,
) -> float:
    """Higher = more structural bias (01-02-03 / 22-24-25 dominance)."""
    sig = compute_structural_signatures(numbers)
    score = 0.0
    if sig["has_prefix_123"]:
        score += 35.0
    if sig["has_suffix_222425"]:
        score += 30.0
    if "01-02" in sig["prefix_pairs"]:
        score += 8.0
    if "02-03" in sig["prefix_pairs"]:
        score += 8.0
    for pair in ("22-24", "24-25", "22-25"):
        if pair in sig["suffix_pairs"]:
            score += 6.0
    if profile_origin == "recorrente":
        score += 10.0
    elif profile_origin == "hibrido":
        score += 4.0
    if is_v1_strong_pattern(numbers):
        score = max(0.0, score - 18.0)
    return round(score, 3)


def apply_core_traceability_payload(
    game: dict[str, Any],
    *,
    profile_origin: str | None = None,
    relabeling_applied: bool = False,
    relabeling_reason: str | None = None,
) -> dict[str, Any]:
    origin = str(profile_origin or game.get("perfil_origem_real") or game.get("profile_type") or "")
    label_final = str(game.get("profile_type") or origin)
    numbers = list(game.get("numbers") or [])
    sig = compute_structural_signatures(numbers)
    bias = compute_structural_bias_score(numbers, profile_origin=origin)

    game["perfil_origem_real"] = origin
    game["perfil_label_final"] = label_final
    game["prefix_signature"] = sig["prefix_signature"]
    game["suffix_signature"] = sig["suffix_signature"]
    game["structural_bias_score"] = bias
    game["relabeling_applied"] = bool(relabeling_applied)
    game["relabeling_reason"] = relabeling_reason
    game["v1_strong_pattern_shield"] = is_v1_strong_pattern(numbers)

    trace = dict(game.get("core_traceability") or {})
    trace.update(
        {
            "perfil_origem_real": origin,
            "perfil_label_final": label_final,
            "prefix_signature": sig["prefix_signature"],
            "suffix_signature": sig["suffix_signature"],
            "structural_bias_score": bias,
            "relabeling_applied": bool(relabeling_applied),
            "relabeling_reason": relabeling_reason,
            "prefix_pairs": sig["prefix_pairs"],
            "suffix_pairs": sig["suffix_pairs"],
        }
    )
    game["core_traceability"] = trace
    return game


def apply_structural_bias_penalty_to_score(
    game: dict[str, Any],
    *,
    weight: float,
    enabled: bool,
) -> float:
    if not enabled:
        return float(game.get("profile_score", 0) or 0)
    origin = str(game.get("perfil_origem_real") or game.get("profile_type") or "")
    bias = compute_structural_bias_score(list(game.get("numbers") or []), profile_origin=origin)
    penalty = bias * weight / 100.0
    adjusted = max(0.0, float(game.get("profile_score", 0) or 0) - penalty)
    game["structural_bias_score"] = bias
    game["structural_bias_penalty"] = round(penalty, 3)
    game["profile_score"] = round(adjusted, 2)
    intel = game.get("historical_intelligence")
    if isinstance(intel, dict):
        intel["structural_bias_penalty"] = round(penalty, 3)
    return adjusted
