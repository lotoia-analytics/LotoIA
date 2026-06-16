"""Lei 15 + Lei 15A — Core Realignment V3 BALANCED.

Hits-first structural realignment: reduce prefix excess gradually without
destroying combinatorial strength from Lei 15 profile inheritance.

ADR: ADR-045-CORE-REALIGNMENT-V3-BALANCED
Mission: MISSAO_DA_VITORIA_REAVALIAR_NUCLEOS_LEI15_15A
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class CoreRealignmentV3Config:
    """Balanced thresholds — between V1 and rejected V2."""

    mode: str = "shadow_test"

    # Layer 1 — soft pool pre-filter (only trim extreme prefix groups)
    max_pool_prefix3_ratio: float = 0.42
    min_pool_size_after_filter: int = 40

    # Layer 2 — moderate composition (V1-like, slightly tighter prefix)
    max_prefix3_ratio: float = 0.32
    max_prefix4_ratio: float = 0.28
    max_suffix3_ratio: float = 0.22
    max_suffix4_ratio: float = 0.25

    concentration_penalty_weight: float = 42.0

    target_coverage_digits: tuple[int, ...] = (16, 6, 17, 23, 20, 8, 10, 4)
    coverage_bonus_per_digit: float = 1.5
    max_coverage_bonus: float = 6.0

    overlap_slack: int = 3
    overlap_penalty_per_digit: float = 8.0
    min_gp_for_concentration_check: int = 5

    # Favor combinatorial base score slightly more than V2 (hits-first)
    base_score_weight: float = 0.002

    realignment_tag: str = "CORE_REALIGNMENT_V3_BALANCED"
    evidence_epoch: str = "EPOCH_001_V3_BALANCED"


_ENV_VAR: Final = "LOTOIA_LEI15_15A_CORE_REALIGNMENT_V3"
_VALID_MODES: Final = frozenset({"off", "shadow_test", "active"})
_V3_LABEL_PREFIX: Final = "STRUCT_CORE_REALIGN_V3_BALANCED_"


def get_v3_mode() -> str:
    raw = os.getenv(_ENV_VAR, "off").strip().lower()
    return raw if raw in _VALID_MODES else "off"


def get_v3_config() -> CoreRealignmentV3Config:
    return CoreRealignmentV3Config(mode=get_v3_mode())


def v3_is_observable() -> bool:
    return get_v3_mode() in {"shadow_test", "active"}


def is_v3_label(batch_label: str | None) -> bool:
    return str(batch_label or "").strip().upper().startswith(_V3_LABEL_PREFIX)


def should_apply_v3(batch_label: str | None = None) -> bool:
    mode = get_v3_mode()
    if mode == "off":
        return False
    if mode == "active":
        return False
    return is_v3_label(batch_label)
