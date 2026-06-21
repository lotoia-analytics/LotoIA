"""Hotfix — compose_sovereign_gp deve fechar lotes grandes (ex.: 50 jogos)."""

from __future__ import annotations

import pytest

from lotoia.generation.lei15_core_002 import (
    _relaxed_overlap_limits,
    apply_anti_clone_gp,
    compose_sovereign_gp,
)
from lotoia.generator.basic_generator import generate_best_games, load_draws
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL, get_core_002_config
from lotoia.generation.lei15_core_002 import build_sovereign_pool
from lotoia.ml.overlap_format_thresholds import build_overlap_composition_rows
from lotoia.ml.structural_pool_15d_generator import (
    build_ml_structural_15d_pool,
    resolve_structural_pool_target,
)


@pytest.fixture(autouse=True)
def _enable_structural_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_ML_STRUCTURAL_15D_POOL_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_OPERATIONAL_HIERARCHY_ENABLED", "0")


def test_resolve_structural_pool_target_scales_with_requested_count() -> None:
    assert resolve_structural_pool_target(requested_count=10) >= 100
    assert resolve_structural_pool_target(requested_count=50) == 150
    assert resolve_structural_pool_target(requested_count=80) == 240


def test_compose_sovereign_gp_delivers_50_without_ml() -> None:
    cfg = get_core_002_config(BATCH_LABEL)
    history = load_draws()
    pool = build_sovereign_pool(200, seed=42, history=history, config=cfg)
    gp = compose_sovereign_gp(pool, 50, cfg, game_size=15)
    assert len(gp) == 50


def test_compose_sovereign_gp_delivers_50_with_structural_pool() -> None:
    cfg = get_core_002_config(BATCH_LABEL)
    history = load_draws()
    pool = build_sovereign_pool(200, seed=42, history=history, config=cfg)
    structural_pool, bundle = build_ml_structural_15d_pool(
        pool,
        history=history,
        seed=42,
        min_compliant=resolve_structural_pool_target(requested_count=50),
    )
    assert bundle.get("compliance_met") is True
    gp = compose_sovereign_gp(structural_pool, 50, cfg, game_size=15)
    assert len(gp) == 50


def test_apply_anti_clone_uses_fallback_pool() -> None:
    games = [
        {"numbers": list(range(1, 16)), "profile_score": 10.0, "final_score": {"final_score": 1.0}},
    ]
    fallback = [
        {
            "numbers": sorted([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16]),
            "profile_score": 9.0,
            "final_score": {"final_score": 1.0},
        }
    ]
    selected = apply_anti_clone_gp(games, [], 2, fallback_pool=fallback)
    assert len(selected) == 2


def test_overlap_composition_rows_arrow_compatible_types() -> None:
    rows = build_overlap_composition_rows(15, {12: 3, 13: 1, 10: 5})
    overlaps = [row["overlap"] for row in rows]
    assert all(isinstance(value, str) for value in overlaps)


def test_relaxed_overlap_limits_scale_with_batch_size() -> None:
    assert _relaxed_overlap_limits(10) == (11, 12)
    assert _relaxed_overlap_limits(50) == (11, 12, 13, 14, 15)


def test_generate_best_games_50_with_ml_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LOTOIA_DATABASE_URL", raising=False)
    monkeypatch.setenv("LOTOIA_ML_OUTPUT_CALIBRATION_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_OPERATIONAL_HIERARCHY_ENABLED", "1")
    monkeypatch.setattr(
        "lotoia.ml.structural_policy_15d.apply_structural_policy_15d_to_sovereign_batch",
        lambda selected, **kwargs: (list(selected), {"structural_policy_applied": True}),
    )
    result = generate_best_games(
        count=50,
        pool_size=150,
        batch_label=BATCH_LABEL,
        ml_enabled=True,
        seed=7,
    )
    assert len(result.get("games") or []) == 50
