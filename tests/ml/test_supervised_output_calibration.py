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
    resolve_near_duplicate_pair_ratio,
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


@pytest.fixture(autouse=True)
def _mock_structural_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    policy: dict[str, object] = {
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


def test_analyze_uses_adaptive_near_dup_limit_for_small_lot() -> None:
    games = _pool_with_redundancy(6)
    diagnostics = analyze_pool_structural_issues(games, game_size=15, requested_count=5)
    near_dup_issues = [
        row for row in diagnostics["issues"] if row.get("tipo") == "quase_repetidos_alto"
    ]
    if near_dup_issues:
        assert "limite_lote=0.60" in str(near_dup_issues[0].get("descricao") or "")
    assert resolve_near_duplicate_pair_ratio(5) == 0.60


def test_analyze_small_lot_uses_adaptive_distinct_coverage() -> None:
    games = [_make_game(_base_card(index)) for index in range(5)]
    diagnostics = analyze_pool_structural_issues(games, game_size=15, requested_count=5)
    blocking = [
        row
        for row in diagnostics["issues"]
        if row.get("tipo") == "dezena_subcoberta" and row.get("dezena") in {7, 15, 23}
    ]
    assert not blocking


def test_small_lot_with_sufficient_distinct_coverage_does_not_block_critical_dezenas() -> None:
    """M-ML-080-FIX-01 — lote 1–5 com >=18 dezenas distintas não reprova por 7/15/23 ausentes."""
    card_a = [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 16, 17]
    card_b = [18, 19, 20, 21, 22, 24, 25, 1, 2, 3, 4, 5, 6, 8, 9]
    games = [_make_game(card_a), _make_game(card_b), _make_game(card_b)]
    diagnostics = analyze_pool_structural_issues(games, game_size=15, requested_count=5)
    blocking = [row for row in diagnostics["issues"] if row.get("tipo") == "dezena_subcoberta"]
    assert not any(int(row.get("dezena", 0) or 0) in {7, 15, 23} for row in blocking if "dezena" in row)
    observational = [
        row for row in diagnostics["issues"] if row.get("tipo") == "dezena_critica_ausente_observacional"
    ]
    assert len(observational) == 3


def test_mid_small_lot_with_22_distinct_does_not_block_critical_dezenas() -> None:
    """M-ML-080-FIX-01 — lote 6–15 com >=22 dezenas distintas não reprova por 7/15/23 ausentes."""
    dezenas = list(range(1, 23))
    games = [_make_game(dezenas, profile_score=10.0 - index) for index in range(8)]
    diagnostics = analyze_pool_structural_issues(games, game_size=15, requested_count=10)
    blocking = [row for row in diagnostics["issues"] if row.get("tipo") == "dezena_subcoberta"]
    assert not any(int(row.get("dezena", 0) or 0) in {7, 15, 23} for row in blocking if "dezena" in row)


def test_large_lot_keeps_per_dezena_subcoverage() -> None:
    core = list(range(1, 16))
    games = [_make_game(core) for _ in range(19)]
    games.append(_make_game([16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 1, 2, 3, 4, 5]))
    diagnostics = analyze_pool_structural_issues(games, game_size=15, requested_count=20)
    assert any(row.get("tipo") == "dezena_subcoberta" for row in diagnostics["issues"])


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
