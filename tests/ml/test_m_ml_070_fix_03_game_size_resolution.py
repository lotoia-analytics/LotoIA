"""M-ML-070-FIX-03 — requested_count separado de game_size na calibração 15D."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL, ENV_GENERATION_ENABLED
from lotoia.generator.basic_generator import _attach_scores, _build_game, generate_best_games
from lotoia.ml.overlap_format_thresholds import SUPPORTED_FORMAT_SIZES
from lotoia.ml.supervised_output_calibration import (
    MISSION_ID_FIX_03,
    analyze_pool_structural_issues,
    apply_supervised_output_calibration,
    resolve_pool_game_size,
)


@pytest.fixture(autouse=True)
def _stub_structural_policy_15d_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    policy: dict[str, Any] = {
        "policy_version": "M-ML-070-v1",
        "core_numbers": [7, 15, 23],
        "discouraged_numbers": [],
    }

    monkeypatch.setattr(
        "lotoia.ml.supervised_output_calibration.ensure_structural_policy_15d_memory",
        lambda db_path=None: policy,
    )
    monkeypatch.setattr(
        "lotoia.ml.supervised_output_calibration.build_structural_policy_15d_calibration_plan",
        lambda bundle, policy_payload: {"has_plan": False, "parametros_sugeridos": {}},
    )


def _games_15d(count: int) -> list[dict]:
    rows: list[dict] = []
    for index in range(count):
        numbers = sorted({((index + offset * 7) % 25) + 1 for offset in range(15)})
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


def test_resolve_pool_game_size_rejects_count_as_format() -> None:
    games = _games_15d(5)
    resolved, contract = resolve_pool_game_size(
        games,
        batch_label=BATCH_LABEL,
        game_size=30,
        requested_count=30,
    )
    assert resolved == 15
    assert contract["resolved_from"] == "batch_label"
    assert any("requested_count" in error for error in contract["contract_errors"])


def test_analyze_pool_structural_issues_gp30_uses_game_size_15() -> None:
    games = _games_15d(30)
    diagnostics = analyze_pool_structural_issues(
        games,
        game_size=30,
        batch_label=BATCH_LABEL,
        requested_count=30,
    )
    assert diagnostics["game_size"] == 15
    assert diagnostics["game_size_contract"]["mission_id"] == MISSION_ID_FIX_03
    assert diagnostics["redundancy"]["game_size"] == 15
    assert diagnostics["redundancy"]["formato"] == "15D"


def test_apply_supervised_calibration_gp30_15d_no_value_error() -> None:
    games = _games_15d(30)
    calibrated, bundle = apply_supervised_output_calibration(
        games,
        game_size=30,
        ml_enabled=True,
        event_context={
            "batch_label": BATCH_LABEL,
            "requested_count": 30,
        },
    )
    assert len(calibrated) == 30
    assert bundle["game_size"] == 15
    assert bundle["game_size_contract"]["game_size"] == 15
    assert bundle["calibration_applied"] is True


def test_requested_count_differs_from_game_size() -> None:
    games = _games_15d(20)
    resolved, contract = resolve_pool_game_size(
        games,
        batch_label=BATCH_LABEL,
        game_size=20,
        requested_count=20,
    )
    assert resolved == 15
    assert contract["requested_count"] == 20
    assert contract["game_size"] == 15
    assert contract["requested_game_size"] == 20


@pytest.mark.parametrize("requested_count", [20, 30])
def test_gp_15d_generates_without_error(
    monkeypatch: pytest.MonkeyPatch,
    requested_count: int,
) -> None:
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002", "sovereign")
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "1")
    monkeypatch.setenv("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "off")
    monkeypatch.setenv("LOTOIA_ML_OUTPUT_CALIBRATION_ENABLED", "1")

    pool_size = max(requested_count + 10, 40)

    def _mock_pool(pool_size_arg, *, seed, history, config):
        games = []
        for index in range(pool_size_arg):
            numbers = sorted({((index + offset * 7) % 25) + 1 for offset in range(15)})
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
                side_effect=lambda selected, **kwargs: (
                    selected,
                    {"structural_policy_applied": False},
                ),
            ):
                result = generate_best_games(
                    count=requested_count,
                    pool_size=pool_size,
                    ml_enabled=True,
                    batch_label=BATCH_LABEL,
                )

    assert result["count"] == requested_count
    assert result["requested_count"] == requested_count
    assert result["game_size"] == 15
    assert compose_calls == [15]
    calibration = dict(result.get("calibration_bundle") or {})
    assert calibration.get("game_size") == 15


def test_m_ml_067_supported_formats_unchanged() -> None:
    assert list(SUPPORTED_FORMAT_SIZES) == list(range(15, 24))


def test_basic_generator_sovereign_path_uses_resolved_game_size() -> None:
    import inspect

    source = inspect.getsource(generate_best_games)
    sovereign_block = source.split("if _apply_sovereign and ml_enabled:")[1].split("elif _apply_v4:")[0]
    assert "resolve_pool_game_size" in source
    assert "game_size=_sovereign_game_size" in sovereign_block
    assert "game_size=count" not in sovereign_block
