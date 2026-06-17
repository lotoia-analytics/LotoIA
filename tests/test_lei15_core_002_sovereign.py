from __future__ import annotations

import pytest

from lotoia.generation.lei15_core_002 import (
    apply_critical_digit_layer,
    compose_sovereign_gp,
    tag_sovereign_gp_metadata,
)
from lotoia.governance.analysis_batch_labels import (
    LEI15_CORE_002_SOVEREIGN,
    infer_batch_type,
    normalize_batch_label,
)
from lotoia.governance.lei15_core_002_sovereign import (
    BATCH_LABEL,
    SOVEREIGN_STATUS,
    enforce_generation_policy,
    get_core_002_config,
    institutional_status_report,
    is_sovereign_core_label,
    lei15a_operational_gate,
    should_apply_core_002,
)
from lotoia.generator.basic_generator import generate_best_games
from lotoia.statistics.historical_intelligence import PROFILE_RECURRENT


def _mock_game(numbers: list[int], score: float = 90.0) -> dict:
    return {
        "numbers": numbers,
        "profile_type": PROFILE_RECURRENT,
        "profile_score": score,
        "final_score": {"final_score": 1.0},
        "perfil_origem_real": PROFILE_RECURRENT,
    }


def test_sovereign_label_registered() -> None:
    assert normalize_batch_label(BATCH_LABEL) == BATCH_LABEL
    assert infer_batch_type(BATCH_LABEL) == LEI15_CORE_002_SOVEREIGN
    assert is_sovereign_core_label(BATCH_LABEL)


def test_generation_blocked_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002", "sovereign")
    monkeypatch.delenv("LOTOIA_LEI15_CORE_002_GENERATION_ENABLED", raising=False)
    with pytest.raises(RuntimeError, match="Geração bloqueada"):
        enforce_generation_policy(BATCH_LABEL)
    with pytest.raises(RuntimeError, match="Geração Lei 15 bloqueada"):
        generate_best_games(count=5, pool_size=10, batch_label=BATCH_LABEL)


def test_should_apply_when_sovereign_implanted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002", "sovereign")
    assert should_apply_core_002(BATCH_LABEL) is True
    assert should_apply_core_002("STRUCT_REALIGN_V1_15D_001") is False


def test_institutional_status_snapshot() -> None:
    report = institutional_status_report()
    assert report["core_id"] == "LEI15_CORE_002"
    assert report["generation_blocked"] is True
    assert report["active_public_blocked"] is True
    assert report["legacy_core"]["status"] == "baseline_congelado_read_only"
    assert lei15a_operational_gate()["open_15a"] is False


def test_sovereign_payload_fields() -> None:
    cfg = get_core_002_config(BATCH_LABEL)
    games = [_mock_game([1, 2, 3, 6, 7, 8, 10, 11, 14, 16, 18, 20, 22, 24, 25])]
    apply_critical_digit_layer(games)
    tag_sovereign_gp_metadata(games, config=cfg)
    game = games[0]
    assert game["lei15_core_002_applied"] is True
    assert game["sovereign_core_status"] == SOVEREIGN_STATUS
    assert game["candidate_origin_label"] == BATCH_LABEL
    assert game["generation_cand_d_applied"] is True
    assert game["v1_strong_shield_applied"] is True
    assert game["anti_clone_gp_applied"] is True
    assert game["critical_digit_layer_applied"] is True
    assert game["perfil_origem_real"] == PROFILE_RECURRENT
    assert game["prefix_signature"] == "01-02-03"
    assert game["suffix_signature"] == "22-24-25"
    assert game["relabeling_applied"] is False


def test_compose_layers_tagged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "shadow_test")
    cfg = get_core_002_config(BATCH_LABEL)
    pool = []
    for i in range(20):
        nums = sorted({((i * 7 + j * 11) % 25) + 1 for j in range(20)})[:15]
        game = _mock_game(nums, 95 - i)
        game["prefix_signature"] = f"0{(i % 7) + 1:02d}-0{(i % 7) + 2:02d}-0{(i % 7) + 3:02d}"
        game["suffix_signature"] = f"2{(20 - i) % 7 + 1:02d}-2{(21 - i) % 7 + 1:02d}-2{(22 - i) % 7 + 1:02d}"
        pool.append(game)
    gp = compose_sovereign_gp(pool, 5, cfg, game_size=15)
    assert len(gp) == 5
    assert all(g.get("v1_selection_compose_applied") for g in gp)
    assert all(g.get("lei15_core_002_applied") for g in gp)
