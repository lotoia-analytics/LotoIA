"""Lei 15 — Core Realignment V4 PATTERN PROTECTED (shadow_test only).

Protects V1 combinatorial signature patterns — not exact baseline cards.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

REALIGNMENT_NAME: Final = "LEI15_CORE_REALIGNMENT_V4_PATTERN_PROTECTED"
ENV_VAR: Final = "LOTOIA_LEI15_CORE_REALIGNMENT_V4"
LABEL_PREFIX: Final = "STRUCT_LEI15_CORE_V4_PATTERN_PROTECTED_"
BATCH_LABEL: Final = "STRUCT_LEI15_CORE_V4_PATTERN_PROTECTED_15D_001"

STRONG_SUFFIXES: Final[tuple[tuple[int, ...], ...]] = (
    (22, 24, 25),
    (23, 24, 25),
    (18, 24, 25),
)
STRONG_PREFIXES: Final[tuple[tuple[int, ...], ...]] = (
    (1, 2, 3),
    (1, 3, 4),
    (1, 3, 6),
    (1, 4, 6),
)
MIDDLE_BLOCK_DIGITS: Final[tuple[int, ...]] = (6, 8, 14, 15, 16, 18)
PREFERRED_PROFILES: Final[tuple[str, ...]] = ("recorrente", "hibrido")


@dataclass(frozen=True, slots=True)
class CoreRealignmentV4Config:
    """Pattern-protected compose — Faixa A 30% + Faixa B 70%."""

    mode: str = "shadow_test"

    pattern_protected_ratio: float = 0.30
    min_pattern_score_faixa_a: float = 20.0

    max_pool_prefix3_ratio: float = 0.48
    min_pool_size_after_filter: int = 40

    max_prefix3_ratio: float = 0.36
    max_prefix4_ratio: float = 0.30
    max_suffix3_ratio: float = 0.38
    max_suffix4_ratio: float = 0.30

    concentration_penalty_weight: float = 42.0

    target_coverage_digits: tuple[int, ...] = (16, 6, 17, 23, 20, 8, 10, 4)
    coverage_bonus_per_digit: float = 1.5
    max_coverage_bonus: float = 6.0

    overlap_slack: int = 3
    overlap_penalty_per_digit: float = 8.0
    min_gp_for_concentration_check: int = 5

    base_score_weight: float = 0.01

    strong_suffixes: tuple[tuple[int, ...], ...] = STRONG_SUFFIXES
    strong_prefixes: tuple[tuple[int, ...], ...] = STRONG_PREFIXES
    middle_block_digits: tuple[int, ...] = MIDDLE_BLOCK_DIGITS
    preferred_profiles: tuple[str, ...] = PREFERRED_PROFILES

    realignment_tag: str = REALIGNMENT_NAME
    evidence_epoch: str = "EPOCH_001_LEI15_V4_PATTERN_PROTECTED"


_VALID_MODES: Final = frozenset({"off", "shadow_test", "active"})


def get_v4_mode() -> str:
    raw = os.getenv(ENV_VAR, "off").strip().lower()
    return raw if raw in _VALID_MODES else "off"


def get_v4_config() -> CoreRealignmentV4Config:
    return CoreRealignmentV4Config(mode=get_v4_mode())


def is_v4_label(batch_label: str | None) -> bool:
    return str(batch_label or "").strip().upper().startswith(LABEL_PREFIX)


def v4_is_observable() -> bool:
    return get_v4_mode() in {"shadow_test", "active"}


def should_apply_v4(batch_label: str | None = None) -> bool:
    """V4 is shadow_test only — active is blocked until ADR approval."""
    if get_v4_mode() != "shadow_test":
        return False
    return is_v4_label(batch_label)
