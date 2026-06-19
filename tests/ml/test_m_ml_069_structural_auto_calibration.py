"""M-ML-069 — calibração estrutural automática format-aware 16D–23D."""

from __future__ import annotations

import pytest

from dashboard.institutional_build import BUILD_MARKER
from lotoia.ml.structural_auto_calibration import (
    ACTION_EXCESSIVE_DEZENAS,
    ACTION_LOW_BASE_DIVERSITY,
    ACTION_LOW_DIVERSITY,
    ACTION_PREFIX_DOMINANT,
    ACTION_RERANK_CONCENTRATION,
    ACTION_SUFFIX_DOMINANT,
    ACTION_SUPERFICIAL_EXPANSION,
    ACTION_UNDERCOVERED_DEZENAS,
    INTENSITY_ALTA,
    INTENSITY_BAIXA,
    INTENSITY_MODERADA,
    MISSION_ID,
    build_auto_calibration_plan,
    build_auto_calibration_plan_from_pool,
    build_structural_calibration_memory,
    compute_structural_diversity_bonus,
    derive_structural_calibration_actions,
    is_structural_auto_calibration_format,
    resolve_progressive_intensity,
)
from lotoia.ml.supervised_output_calibration import apply_supervised_output_calibration
from lotoia.ml.overlap_format_thresholds import classify_overlap_for_format, classify_pair_overlap_level


def _card(size: int, base: int = 1) -> list[int]:
    return list(range(base, base + size))


def _game(size: int, base: int = 1, *, core: list[int] | None = None) -> dict:
    numbers = _card(size, base)
    payload: dict = {"numbers": numbers, "final_card_numbers": numbers, "score_ml": 55.0, "profile_score": 1.0}
    if core is not None:
        payload["core_numbers"] = core
    return payload


def _dominant_prefix_audit(size: int) -> dict:
    games = [_game(size, 1)] * 12 + [_game(size, 2)] * 8
    return build_auto_calibration_plan_from_pool(games, game_size=size)


@pytest.mark.parametrize("size", [16, 17, 18, 19, 20, 21, 22, 23])
def test_format_aware_supported_sizes(size: int) -> None:
    assert is_structural_auto_calibration_format(size) is True
    assert is_structural_auto_calibration_format(15) is False
    assert is_structural_auto_calibration_format(24) is False


@pytest.mark.parametrize("size", [16, 17, 18, 19, 20, 21, 22, 23])
def test_dominant_prefix_triggers_auto_action(size: int) -> None:
    plan = _dominant_prefix_audit(size)
    assert plan.get("auto_structural_calibration") is True
    causes = {row["problema_detectado"] for row in plan.get("structural_actions") or []}
    assert ACTION_PREFIX_DOMINANT in causes
    params = dict(plan.get("parametros_sugeridos") or {})
    assert float(params.get("prefix_penalty", 0) or 0) > 1.0


@pytest.mark.parametrize("size", [16, 17, 18, 19, 20, 21, 22, 23])
def test_dominant_suffix_triggers_auto_action(size: int) -> None:
    suffix_tail = sorted(list(range(1, size - 2)) + [23, 24, 25])
    games = [{"numbers": suffix_tail, "final_card_numbers": suffix_tail, "score_ml": 50.0}] * 20
    plan = build_auto_calibration_plan_from_pool(games, game_size=size)
    causes = {row["problema_detectado"] for row in plan.get("structural_actions") or []}
    assert ACTION_SUFFIX_DOMINANT in causes


@pytest.mark.parametrize("size", [16, 17, 18, 19, 20, 21, 22, 23])
def test_undercovered_dezenas_trigger_coverage_action(size: int) -> None:
    games = [_game(size, 1) for _ in range(20)]
    plan = build_auto_calibration_plan_from_pool(games, game_size=size)
    causes = {row["problema_detectado"] for row in plan.get("structural_actions") or []}
    assert ACTION_UNDERCOVERED_DEZENAS in causes
    assert float(dict(plan.get("parametros_sugeridos") or {}).get("missing_numbers_boost", 0) or 0) > 1.0


@pytest.mark.parametrize("size", [16, 17, 18, 19, 20, 21, 22, 23])
def test_excessive_dezenas_trigger_penalty_action(size: int) -> None:
    games = [_game(size, 1) for _ in range(20)]
    plan = build_auto_calibration_plan_from_pool(games, game_size=size)
    causes = {row["problema_detectado"] for row in plan.get("structural_actions") or []}
    assert ACTION_EXCESSIVE_DEZENAS in causes


@pytest.mark.parametrize("size", [16, 17, 18, 19, 20, 21, 22, 23])
def test_low_base_diversity_triggers_action(size: int) -> None:
    core = list(range(1, 16))
    games = [
        _game(size, 1, core=core),
        _game(size, 1, core=core),
        _game(size, 1, core=core),
        _game(size, 1, core=core),
        _game(size, 1, core=core),
        _game(size, 2, core=list(range(2, 17))),
    ]
    plan = build_auto_calibration_plan_from_pool(games, game_size=size)
    causes = {row["problema_detectado"] for row in plan.get("structural_actions") or []}
    assert ACTION_LOW_BASE_DIVERSITY in causes


@pytest.mark.parametrize("size", [17, 18, 19, 20, 21, 22, 23])
def test_superficial_expansion_triggers_action(size: int) -> None:
    core = list(range(1, 16))
    extra = [16, 17][: max(0, size - 15)]
    games = [
        _game(size, 1, core=core)
        for _ in range(8)
    ]
    for game in games:
        game["numbers"] = core + extra
        game["final_card_numbers"] = core + extra
    plan = build_auto_calibration_plan_from_pool(games, game_size=size)
    causes = {row["problema_detectado"] for row in plan.get("structural_actions") or []}
    assert ACTION_SUPERFICIAL_EXPANSION in causes or ACTION_LOW_BASE_DIVERSITY in causes


def test_progressive_intensity_escalation() -> None:
    assert resolve_progressive_intensity(1) == INTENSITY_BAIXA
    assert resolve_progressive_intensity(2) == INTENSITY_MODERADA
    assert resolve_progressive_intensity(3) == INTENSITY_ALTA
    assert resolve_progressive_intensity(9) == INTENSITY_ALTA


def test_structural_calibration_memory_catalog() -> None:
    memory = build_structural_calibration_memory()
    assert memory["mission_id"] == MISSION_ID
    assert memory["supported_formats"] == [f"{size}D" for size in range(16, 24)]
    assert "prefixo_dominante" in memory["action_catalog"]
    for fmt in memory["per_format_records"]:
        assert fmt.endswith("D")


def test_rerank_considers_structural_diversity() -> None:
    size = 17
    games = [_game(size, 1)] * 10 + [_game(size, 2)] * 10
    for idx, game in enumerate(games):
        game["profile_score"] = 10.0 - (idx * 0.01)
        game["score_ml"] = 90.0 - idx
    calibrated, bundle = apply_supervised_output_calibration(games, game_size=size, ml_enabled=True)
    causes = {row["problema_detectado"] for row in bundle.get("structural_actions_applied") or []}
    assert ACTION_RERANK_CONCENTRATION in causes or ACTION_LOW_DIVERSITY in causes
    assert bundle.get("structural_calibration_memory")
    assert calibrated[0].get("calibration_applied") is True


def test_apply_supervised_registers_memory_for_17d() -> None:
    games = [_game(17, 1)] * 12 + [_game(17, 2)] * 8
    _, bundle = apply_supervised_output_calibration(games, game_size=17, ml_enabled=True)
    assert bundle.get("structural_auto_calibration_mission_id") == MISSION_ID
    memory = dict(bundle.get("structural_calibration_memory") or {})
    assert memory.get("mission_id") == MISSION_ID
    assert memory.get("per_format_records", {}).get("17D")


def test_no_exclusive_17d_rule_in_module() -> None:
    import inspect

    from lotoia.ml import structural_auto_calibration as module

    source = inspect.getsource(module)
    assert "if game_size == 17" not in source
    assert "if size == 17" not in source


def test_m_ml_067_overlap_rules_preserved() -> None:
    assert classify_pair_overlap_level(15, game_size=17) == "atencao"
    assert classify_pair_overlap_level(16, game_size=17) == "ruim"
    assert classify_overlap_for_format(15, game_size=17)["level"] == "atencao"
    assert classify_overlap_for_format(17, game_size=17)["level"] == "critico"


def test_build_marker_v58() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v58"


def test_derive_actions_from_audit_report() -> None:
    audit = dict(_dominant_prefix_audit(18).get("structural_audit") or {})
    actions, _params = derive_structural_calibration_actions(audit, occurrence_count=2)
    assert actions
    assert all(row["intensidade"] == INTENSITY_MODERADA for row in actions)


def test_diversity_bonus_prefers_non_dominant_prefix() -> None:
    diagnostics = {"number_presence": {str(n): 2 for n in range(1, 26)}}
    game = _game(17, 2)
    bonus = compute_structural_diversity_bonus(
        game,
        diagnostics=diagnostics,
        pool_size=20,
        dominant_prefix="01-02-03",
        dominant_suffix="",
    )
    assert bonus > 0.0
