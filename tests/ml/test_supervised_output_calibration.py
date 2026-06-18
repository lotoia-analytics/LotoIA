from __future__ import annotations

from copy import deepcopy

import pytest

from lotoia.ml.supervised_output_calibration import (
    CALIBRATION_ENGINE_ROLE,
    CALIBRATION_VERSION,
    MISSION_ID,
    analyze_pool_structural_issues,
    apply_supervised_output_calibration,
    is_output_calibration_enabled,
)


def _base_card(offset: int = 0) -> list[int]:
    return sorted({((index + offset - 1) % 25) + 1 for index in range(1, 16)})


def _make_game(numbers: list[int], *, profile_score: float = 10.0) -> dict[str, object]:
    return {
        "numbers": numbers,
        "profile_score": profile_score,
        "score_ml": 42.0,
        "final_score": {"final_score": profile_score},
    }


def _pool_with_redundancy(size: int = 12) -> list[dict[str, object]]:
    base = _base_card(0)
    games: list[dict[str, object]] = []
    for index in range(size):
        numbers = list(base)
        if index > 0:
            numbers[index % 15] = ((numbers[index % 15] + index) % 25) + 1
            numbers = sorted(set(numbers))[:15]
            while len(numbers) < 15:
                candidate = (numbers[-1] % 25) + 1
                if candidate not in numbers:
                    numbers.append(candidate)
            numbers = sorted(numbers)
        games.append(_make_game(numbers, profile_score=20.0 - index * 0.1))
    return games


def test_output_calibration_enabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOTOIA_ML_OUTPUT_CALIBRATION_ENABLED", raising=False)
    assert is_output_calibration_enabled() is True


def test_analyze_detects_near_duplicates_and_subcoverage() -> None:
    games = _pool_with_redundancy(20)
    diagnostics = analyze_pool_structural_issues(games, game_size=15)
    issue_types = {row["tipo"] for row in diagnostics["issues"]}
    assert diagnostics["pool_size"] == 20
    assert "quase_repetidos_alto" in issue_types or diagnostics["issue_count"] >= 1
    assert any(row["tipo"] == "dezena_subcoberta" for row in diagnostics["issues"])


def test_analyze_detects_excessive_prefix() -> None:
    prefix = [1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24]
    games = [_make_game(prefix) for _ in range(10)]
    games.extend(_make_game(_base_card(index)) for index in range(1, 4))
    diagnostics = analyze_pool_structural_issues(games, game_size=15)
    assert any(row["tipo"] == "prefixo_excessivo" for row in diagnostics["issues"])


def test_apply_calibration_penalizes_and_boosts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_ML_OUTPUT_CALIBRATION_ENABLED", "1")
    games = _pool_with_redundancy(16)
    before_order = [tuple(row["numbers"]) for row in games]
    calibrated, bundle = apply_supervised_output_calibration(games, game_size=15, ml_enabled=True)
    assert bundle["calibration_applied"] is True
    assert bundle["calibration_version"] == CALIBRATION_VERSION
    assert bundle["calibration_engine_role"] == CALIBRATION_ENGINE_ROLE
    assert bundle["mission_id"] == MISSION_ID
    assert len(calibrated) == len(games)
    assert all(row.get("calibration_applied") for row in calibrated)
    assert bundle["redundancy_penalty"] >= 0.0
    assert bundle["actions_applied"]
    assert bundle["lei15_core_002_preserved"] is True
    assert bundle["lei15a_applied"] is False
    after_order = [tuple(row["numbers"]) for row in calibrated]
    assert set(before_order) == set(after_order)


def test_apply_calibration_disabled_when_ml_off() -> None:
    games = _pool_with_redundancy(8)
    calibrated, bundle = apply_supervised_output_calibration(games, ml_enabled=False)
    assert bundle["calibration_applied"] is False
    assert calibrated is games


def test_calibration_reranks_by_profile_score(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_ML_OUTPUT_CALIBRATION_ENABLED", "1")
    low_overlap = _make_game([1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 24, 25, 2], profile_score=5.0)
    high_overlap = _make_game(_base_card(0), profile_score=50.0)
    pool = [high_overlap] + [deepcopy(high_overlap)] * 8 + [low_overlap] * 4
    for index, row in enumerate(pool):
        row["numbers"] = list(row["numbers"])
        if index % 3 == 1 and index > 0:
            nums = list(row["numbers"])
            nums[0] = ((nums[0] % 25) + 1)
            row["numbers"] = sorted(set(nums))[:15]
    calibrated, bundle = apply_supervised_output_calibration(pool, game_size=15, ml_enabled=True)
    assert bundle["calibration_applied"] is True
    top = calibrated[0]
    assert float(top.get("profile_score", 0) or 0) >= float(calibrated[-1].get("profile_score", 0) or 0)
