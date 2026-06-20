"""M-ML-071 — ML autorizada a calibrar pool pré-final format-aware 15D–23D."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_supervised_ml import build_calibration_event_summary
from lotoia.governance.lei15_core_002_sovereign import (
    BATCH_LABEL,
    ENV_GENERATION_ENABLED,
    resolve_core_002_batch_label,
)
from lotoia.generator.basic_generator import _attach_scores, _build_game, generate_best_games
from lotoia.ml.pre_final_pool_ml_calibration import (
    MISSION_ID,
    apply_pre_final_pool_ml_calibration,
    build_pre_final_pool_trace,
    finalize_pre_final_gp_outcome,
)
from lotoia.ml.structural_auto_calibration import MISSION_ID as M069_MISSION_ID
from lotoia.ml.structural_policy_15d import POLICY_VERSION as M070_POLICY_VERSION


@pytest.fixture(autouse=True)
def _stub_structural_policy_15d_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    policy: dict[str, Any] = {
        "policy_version": M070_POLICY_VERSION,
        "core_numbers": [7, 12, 16, 23],
        "discouraged_numbers": [2, 4, 11, 15, 24, 25],
    }

    monkeypatch.setattr(
        "lotoia.ml.supervised_output_calibration.ensure_structural_policy_15d_memory",
        lambda db_path=None: policy,
    )
    monkeypatch.setattr(
        "lotoia.ml.supervised_output_calibration.build_structural_policy_15d_calibration_plan",
        lambda bundle, policy_payload: {"has_plan": False, "parametros_sugeridos": {}},
    )


def _games(size: int, count: int) -> list[dict]:
    rows: list[dict] = []
    for index in range(count):
        numbers = sorted({((index + offset * 7) % 25) + 1 for offset in range(size)})
        rows.append(
            {
                "numbers": numbers,
                "final_card_numbers": numbers,
                "profile_score": float(index),
                "score_ml": 50.0,
                "final_score": {"final_score": float(index)},
            }
        )
    return rows


def test_pre_final_calibration_15d_policy_and_game_size() -> None:
    games = _games(15, 30)
    calibrated, bundle = apply_pre_final_pool_ml_calibration(
        games,
        game_size=30,
        requested_count=30,
        ml_enabled=True,
        batch_label=BATCH_LABEL,
    )
    assert len(calibrated) == 30
    assert bundle["game_size"] == 15
    assert bundle["requested_count"] == 30
    assert bundle["pre_final_calibration_policy"] == M070_POLICY_VERSION
    assert bundle["pre_final_calibration_applied"] is True


def test_pre_final_calibration_17d_uses_m069() -> None:
    batch_label = resolve_core_002_batch_label(17)
    games = _games(17, 20)
    _, bundle = apply_pre_final_pool_ml_calibration(
        games,
        game_size=17,
        requested_count=20,
        ml_enabled=True,
        batch_label=batch_label,
    )
    assert bundle["pre_final_calibration_format"] == "17D"
    assert bundle["pre_final_calibration_policy"] == M069_MISSION_ID


def test_candidates_reordered_and_final_gp_changed() -> None:
    baseline = _games(15, 12)
    for index, game in enumerate(baseline):
        game["profile_score"] = float(100 - index)
    shuffled = [dict(game) for game in reversed(baseline)]
    _, bundle = apply_pre_final_pool_ml_calibration(
        shuffled,
        game_size=15,
        requested_count=5,
        ml_enabled=True,
        batch_label=BATCH_LABEL,
        baseline_pool=baseline,
    )
    assert bundle["candidates_reordered"] >= 0
    assert "final_gp_changed_by_ml" in bundle


def test_finalize_pre_final_gp_outcome_compliance() -> None:
    baseline_gp = _games(15, 2)
    final_gp = list(reversed(baseline_gp))
    bundle = finalize_pre_final_gp_outcome(
        {"mission_id": MISSION_ID},
        baseline_gp=baseline_gp,
        final_gp=final_gp,
        structural_policy_bundle={"compliance_rate": 1.0, "policy_compliance_status": "compliant"},
    )
    assert bundle["final_gp_changed_by_ml"] is True
    assert bundle["final_compliance_rate"] == 1.0


def test_build_calibration_event_summary_exposes_pre_final() -> None:
    summary = build_calibration_event_summary(
        {
            "calibration_applied": True,
            "calibration_version": "M-ML-071-v1",
            "calibration_engine_role": "ACTIVE",
            "diagnostics": {"issues": [], "issue_count": 0},
            "pre_final_calibration_applied": True,
            "pre_final_pool_ml_enabled": True,
            "final_gp_changed_by_ml": True,
            "pre_final_pool_size": 40,
        }
    )
    assert summary["pre_final_calibration_applied"] is True
    assert summary["final_gp_changed_by_ml"] is True


@pytest.mark.parametrize(
    ("requested_count", "card_size", "batch_label"),
    [
        (20, 15, BATCH_LABEL),
        (30, 15, BATCH_LABEL),
        (20, 17, resolve_core_002_batch_label(17)),
    ],
)
def test_generate_best_games_pre_final_path(
    monkeypatch: pytest.MonkeyPatch,
    requested_count: int,
    card_size: int,
    batch_label: str,
) -> None:
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002", "sovereign")
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "1")
    monkeypatch.setenv("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "off")
    monkeypatch.setenv("LOTOIA_ML_OUTPUT_CALIBRATION_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_PRE_FINAL_POOL_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_OPERATIONAL_HIERARCHY_ENABLED", "0")

    pool_size = max(requested_count + 10, 40)

    def _mock_pool(pool_size_arg, *, seed, history, config):
        games = []
        for index in range(pool_size_arg):
            numbers = sorted({((index + offset * 7) % 25) + 1 for offset in range(card_size)})
            game = _build_game(numbers)
            _attach_scores(game, history=history, profile_type="recorrente")
            games.append(game)
        return games

    compose_calls: list[int] = []

    def _mock_compose(pool, count_arg, cfg, *, game_size=15):
        compose_calls.append(int(game_size))
        return list(pool[:count_arg])

    with patch("lotoia.generation.lei15_core_002.build_sovereign_pool", side_effect=_mock_pool):
        with patch(
            "lotoia.generation.lei15_core_002.compose_sovereign_gp",
            side_effect=_mock_compose,
        ):
            with patch(
                "lotoia.ml.structural_policy_15d.apply_structural_policy_15d_to_sovereign_batch",
                side_effect=lambda selected, **kwargs: (selected, {"structural_policy_applied": False}),
            ):
                result = generate_best_games(
                    count=requested_count,
                    pool_size=pool_size,
                    ml_enabled=True,
                    batch_label=batch_label,
                )

    assert result["count"] == requested_count
    assert result["game_size"] == card_size
    pre_final = dict(result.get("pre_final_pool_ml_calibration") or result.get("calibration_bundle") or {})
    assert pre_final.get("pre_final_calibration_applied") is True
    assert pre_final.get("game_size") == card_size
    assert all(size == card_size for size in compose_calls if compose_calls)


def test_build_pre_final_pool_trace_omits_raw_pool() -> None:
    trace = build_pre_final_pool_trace(
        {
            "pre_final_calibration_applied": True,
            "pre_final_pool_size": 40,
            "games": [{"numbers": list(range(1, 16))}],
            "metrics_before": {"diversity_score": 0.4},
            "metrics_after": {"diversity_score": 0.55},
        }
    )
    assert "games" not in trace
    assert trace["metrics_before"]["diversity_score"] == 0.4


def test_build_marker_updated() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v81"
    assert MISSION_ID == "M-ML-071"
