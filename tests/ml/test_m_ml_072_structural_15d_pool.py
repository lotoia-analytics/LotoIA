"""M-ML-072 — Gerador estrutural ML 15D com pool mínimo de 100 jogos conformes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import pytest

from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import (
    BATCH_LABEL,
    ENV_GENERATION_ENABLED,
)
from lotoia.generator.basic_generator import _attach_scores, _build_game, generate_best_games
from lotoia.ml.structural_pool_15d_generator import (
    MISSION_ID,
    MIN_COMPLIANT_POOL_SIZE,
    MIN_POOL_COMPLIANCE_RATE,
    POOL_ORIGIN_LABEL,
    REFERENCE_CONTEST_WINDOW,
    build_ml_structural_15d_pool,
    build_structural_15d_pool_trace,
)


@dataclass
class _Draw:
    numbers: list[int]


def _history(previous: list[int] | None = None, *, extra_draws: int = 12) -> list[_Draw]:
    base = sorted(previous or list(range(1, 16)))
    rows = [_Draw(base)]
    for offset in range(extra_draws):
        numbers = sorted({((offset * 3 + index * 2) % 25) + 1 for index in range(15)})
        rows.append(_Draw(numbers))
    return rows


def _raw_pool(size: int = 20) -> list[dict[str, Any]]:
    games: list[dict[str, Any]] = []
    for index in range(size):
        numbers = sorted({((index + offset * 5) % 25) + 1 for offset in range(15)})
        game = _build_game(numbers)
        _attach_scores(game, history=_history(), profile_type="recorrente")
        games.append(game)
    return games


@pytest.fixture(autouse=True)
def _enable_structural_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_ML_STRUCTURAL_15D_POOL_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_OPERATIONAL_HIERARCHY_ENABLED", "0")


@pytest.fixture(autouse=True)
def _stub_structural_policy_15d_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    policy: dict[str, Any] = {
        "policy_version": "M-ML-070-v1",
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


def test_build_ml_structural_15d_pool_minimum_compliant_and_compliance_rate() -> None:
    pool, bundle = build_ml_structural_15d_pool(
        _raw_pool(25),
        history=_history(),
        seed=42,
    )
    assert bundle["structural_pool_applied"] is True
    assert bundle["pool_origin"] == POOL_ORIGIN_LABEL
    assert bundle["structural_compliant_pool_size"] >= MIN_COMPLIANT_POOL_SIZE
    assert len(pool) >= MIN_COMPLIANT_POOL_SIZE
    assert bundle["compliance_rate"] >= MIN_POOL_COMPLIANCE_RATE
    assert bundle["compliance_met"] is True
    assert bundle["reference_contest_window"] == REFERENCE_CONTEST_WINDOW
    confronto = dict(bundle.get("confronto_recent_contests") or {})
    assert confronto.get("reference_contest_window") == 10
    assert int(confronto.get("reference_contests_count", 0) or 0) <= 10


def test_build_structural_15d_pool_trace_omits_raw_games() -> None:
    trace = build_structural_15d_pool_trace(
        {
            "structural_pool_applied": True,
            "structural_pool_size": 120,
            "games": [{"numbers": list(range(1, 16))}],
            "metrics_before": {"diversity_score": 0.5},
            "metrics_after": {"diversity_score": 0.72},
        }
    )
    assert "games" not in trace
    assert trace["structural_pool_size"] == 120


def test_generate_best_games_uses_structural_pool_before_pre_final_calibration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002", "sovereign")
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "1")
    monkeypatch.setenv("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "off")
    monkeypatch.setenv("LOTOIA_ML_OUTPUT_CALIBRATION_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_PRE_FINAL_POOL_ENABLED", "1")

    requested_count = 5
    pool_size = 40
    history = _history()

    def _mock_pool(pool_size_arg, *, seed, history, config):
        games = []
        for index in range(pool_size_arg):
            numbers = sorted({((index + offset * 7) % 25) + 1 for offset in range(15)})
            game = _build_game(numbers)
            _attach_scores(game, history=history, profile_type="recorrente")
            games.append(game)
        return games

    structural_calls: list[int] = []

    def _mock_structural(raw_pool, *, history, min_compliant=100, seed=None, policy=None):
        structural_calls.append(len(raw_pool))
        compliant_pool, bundle = build_ml_structural_15d_pool(
            raw_pool,
            history=history,
            min_compliant=min_compliant,
            seed=seed,
            policy=policy,
        )
        return compliant_pool, bundle

    def _mock_compose(pool, count_arg, cfg, *, game_size=15):
        return list(pool[:count_arg])

    with patch("lotoia.generation.lei15_core_002.build_sovereign_pool", side_effect=_mock_pool):
        with patch(
            "lotoia.ml.structural_pool_15d_generator.build_ml_structural_15d_pool",
            side_effect=_mock_structural,
        ):
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
                        batch_label=BATCH_LABEL,
                    )

    assert result["count"] == requested_count
    structural_bundle = dict(result.get("ml_structural_15d_pool") or {})
    assert structural_bundle.get("structural_pool_applied") is True
    assert structural_bundle.get("pool_origin") == POOL_ORIGIN_LABEL
    assert structural_bundle.get("structural_compliant_pool_size", 0) >= MIN_COMPLIANT_POOL_SIZE
    assert structural_calls == [pool_size]
    pre_final = dict(result.get("pre_final_pool_ml_calibration") or {})
    assert pre_final.get("pre_final_calibration_applied") is True


def test_build_marker_updated() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v71"
    assert MISSION_ID == "M-ML-072"
