"""Lei 15 + Lei 15A — Core Realignment V2.

Governance configuration and feature flag for the two-layer structural
diversity enforcement introduced by LEI15_15A_CORE_REALIGNMENT_V2.

ADM Authorization
-----------------
  Mission : MISSAO_DA_VITORIA_REAVALIAR_NUCLEOS_LEI15_15A
  Evidence: EPOCH_001 audit + STRUCT_REALIGN_V1_15D_001 comparative report
  ADR     : ADR-044-REAVALIACAO-NUCLEOS-LEI15-15A
  Status  : AUTORIZADO_PELO_ADM

What V2 does (two layers)
--------------------------
  Layer 1 — Pool Pre-Filter (NEW):
    Before greedy GP composition, cap how many candidates per prefix_3 may
    enter the pool. This ensures the greedy algorithm has materially diverse
    candidates to select from even when the generation profiles (Recurrent +
    Hybrid) produce a heavily biased candidate set from the last draw.

  Layer 2 — Tighter Composition Thresholds:
    Runs compose_diverse_gp with stricter max_prefix3/suffix3 ratios than V1:
      max_prefix3_ratio : 0.25 → 0.15
      max_prefix4_ratio : 0.30 → 0.20
      max_suffix3_ratio : 0.25 → 0.15
      max_suffix4_ratio : 0.30 → 0.20

Feature flag
------------
  Env var : LOTOIA_LEI15_15A_CORE_REALIGNMENT_V2
  Values  :
    "off"          — disabled (default)
    "shadow_test"  — apply V2 only for STRUCT_CORE_REALIGN_V2_* labels
    "active"       — full V2 applied to all GP composition

Constraints (immutable)
-----------------------
  - Does NOT alter profile generation rules (R-03, R-04, R-05, R-06).
  - Does NOT alter _is_valid_game structural validation bounds.
  - Does NOT replace Lei 15 with ML.
  - Does NOT produce games without traceability.
  - Rollback: set env var to "off"; no DB migration required.
  - V1 remains active independently under LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1.
  - Pool safety: if post-filter pool < min_pool_size_after_filter, mandatory
    fallback to V1 compose_diverse_gp (never unaligned profile composition).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final


# ---------------------------------------------------------------------------
# Evidence base — EPOCH_001_V2 confirmed need for V2
# ---------------------------------------------------------------------------

EPOCH_001_V2_EVIDENCE: Final[dict[str, object]] = {
    "baseline_batch": "STRUCT_TEST_15D_001",
    "v1_batch": "STRUCT_REALIGN_V1_15D_001",
    "v1_gains": {
        "best_hit": "12 → 14",
        "avg_hits": "11.308 → 12.143",
        "runs_14plus": "0 → 5",
        "runs_13plus": "0 → 47",
        "suffix3_top": "53.0% → 26.7%",
        "gp_similarity": "12.210 → 9.717",
    },
    "v1_remaining_issue": "prefix 01-02-03 still at 40.4% (was 42.0%)",
    "root_cause": (
        "PROFILE_RECURRENT and PROFILE_HYBRID inherit 6-10 numbers from "
        "last_draw, producing a homogeneous pool biased toward prefix_3 of "
        "last draw. V1 greedy cannot diversify what does not exist in pool."
    ),
    "v2_intervention": "two-layer: pool pre-filter + tighter compose thresholds",
    "adr": "ADR-044-REAVALIACAO-NUCLEOS-LEI15-15A",
}


# ---------------------------------------------------------------------------
# Configuration dataclass — V2 thresholds
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CoreRealignmentV2Config:
    """Authorised thresholds for Core Realignment V2.

    V2 inherits V1's compose_diverse_gp algorithm but with:
    - Tighter prefix/suffix ratios to force more prefix diversity
    - A pool pre-filter cap (max candidates per prefix_3 in pool)
    - Stronger coverage bonus for recurrently missing digits
    """

    mode: str = "shadow_test"

    # -----------------------------------------------------------------------
    # Layer 1 — Pool Pre-Filter parameters
    # -----------------------------------------------------------------------

    # Maximum fraction of pool candidates that may share the same prefix_3
    # before pool pre-filtering is applied. E.g. 0.30 means at most 30% of
    # pool candidates may have the same 3-digit prefix before we cap them.
    max_pool_prefix3_ratio: float = 0.30

    # Minimum pool size after pre-filtering (safety floor — if filtering
    # would reduce pool below this threshold, skip the filter step and fall
    # back to V1-only composition).
    min_pool_size_after_filter: int = 30

    # -----------------------------------------------------------------------
    # Layer 2 — Tighter composition thresholds (stricter than V1)
    # -----------------------------------------------------------------------

    # Maximum fraction of GP games that may share prefix_3 / prefix_4
    max_prefix3_ratio: float = 0.15   # V1 was 0.25
    max_prefix4_ratio: float = 0.20   # V1 was 0.30

    # Maximum fraction of GP games that may share suffix_3 / suffix_4
    max_suffix3_ratio: float = 0.15   # V1 was 0.25
    max_suffix4_ratio: float = 0.20   # V1 was 0.30

    # Weight of concentration penalty per excess ratio unit
    concentration_penalty_weight: float = 55.0  # V1 was 40.0

    # -----------------------------------------------------------------------
    # Coverage bonus (same target digits, stronger bonus)
    # -----------------------------------------------------------------------

    target_coverage_digits: tuple[int, ...] = (16, 6, 17, 23, 20, 8, 10, 4)

    coverage_bonus_per_digit: float = 2.0   # V1 was 1.5
    max_coverage_bonus: float = 9.0         # V1 was 6.0

    # -----------------------------------------------------------------------
    # Overlap penalty (same as V1 — already well-calibrated)
    # -----------------------------------------------------------------------

    overlap_slack: int = 3
    overlap_penalty_per_digit: float = 8.0
    min_gp_for_concentration_check: int = 5

    # -----------------------------------------------------------------------
    # Metadata tags
    # -----------------------------------------------------------------------

    realignment_tag: str = "CORE_REALIGNMENT_V2"
    evidence_epoch: str = "EPOCH_001_V2"


# ---------------------------------------------------------------------------
# Feature flag resolver
# ---------------------------------------------------------------------------

_ENV_VAR: Final = "LOTOIA_LEI15_15A_CORE_REALIGNMENT_V2"
_VALID_MODES: Final = frozenset({"off", "shadow_test", "active"})
_V2_LABEL_PREFIX: Final = "STRUCT_CORE_REALIGN_V2_"


def get_v2_mode() -> str:
    """Read the V2 operational mode from environment.

    Returns one of: "off", "shadow_test", "active".
    Unknown values treated as "off" (fail-safe).
    """
    raw = os.getenv(_ENV_VAR, "off").strip().lower()
    return raw if raw in _VALID_MODES else "off"


def get_v2_config() -> CoreRealignmentV2Config:
    """Return the active CoreRealignmentV2Config for the current runtime."""
    return CoreRealignmentV2Config(mode=get_v2_mode())


def v2_is_active() -> bool:
    """True when V2 is fully active (all production GPs use V2)."""
    return get_v2_mode() == "active"


def v2_is_observable() -> bool:
    """True when V2 produces any output (shadow_test or active)."""
    return get_v2_mode() in {"shadow_test", "active"}


def is_v2_label(batch_label: str | None) -> bool:
    """True when the batch label belongs to a V2 test series.

    Examples that return True:
        STRUCT_CORE_REALIGN_V2_15D_001
        STRUCT_CORE_REALIGN_V2_16D_001
    """
    return str(batch_label or "").strip().upper().startswith(_V2_LABEL_PREFIX)


def should_apply_v2(batch_label: str | None = None) -> bool:
    """Decide whether V2 realignment should be used for this GP.

    Rules:
      mode=off         → False always
      mode=shadow_test → True only for STRUCT_CORE_REALIGN_V2_* labels
      mode=active      → False (blocked per ADR-044 until ADM unlock)
    """
    mode = get_v2_mode()
    if mode == "off":
        return False
    if mode == "active":
        return False
    return is_v2_label(batch_label)
