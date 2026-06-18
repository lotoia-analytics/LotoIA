"""M-ML-069-AUDIT-01 — auditoria de aplicação real da calibração estrutural 16D–23D."""

from __future__ import annotations

import inspect

import dashboard.institutional_app as institutional_app
import dashboard.institutional_ml_calibration_cockpit as cockpit
from lotoia.ml.structural_auto_calibration import (
    ACTION_EXCESSIVE_DEZENAS,
    ACTION_PREFIX_DOMINANT,
    ACTION_UNDERCOVERED_DEZENAS,
    MISSION_ID,
    build_auto_calibration_plan_from_pool,
    build_structural_calibration_memory,
    is_structural_auto_calibration_format,
)
from lotoia.ml.overlap_format_thresholds import classify_overlap_for_format, classify_pair_overlap_level
from lotoia.ml.supervised_output_calibration import apply_supervised_output_calibration
from scripts.checks.m_ml_069_audit_01_structural_auto_calibration import audit_structural_auto_calibration_application


def _card(size: int, base: int = 1) -> list[int]:
    return list(range(base, base + size))


def _game(size: int, base: int = 1) -> dict:
    numbers = _card(size, base)
    return {"numbers": numbers, "final_card_numbers": numbers, "score_ml": 55.0, "profile_score": 1.0}


def _dominant_pool(size: int) -> list[dict]:
    return [_game(size, 1)] * 12 + [_game(size, 2)] * 8


def test_audit_script_passes_all_formats() -> None:
    report = audit_structural_auto_calibration_application()
    assert report["status"] == "PASS"
    assert report["checks"]["all_formats_gate_accepted"]
    assert report["checks"]["all_formats_auto_plan"]
    assert report["checks"]["all_formats_memory_registered"]
    assert report["checks"]["all_formats_calibration_applied"]
    assert report["checks"]["outside_formats_blocked"]
    assert report["checks"]["central_ml_observability"]
    assert report["checks"]["no_nested_expander"]
    assert report["m_ml_067_preserved"] is True
    assert report["purge_executed"] is False


def test_each_format_generates_structural_plan() -> None:
    for size in range(16, 24):
        assert is_structural_auto_calibration_format(size)
        plan = build_auto_calibration_plan_from_pool(_dominant_pool(size), game_size=size)
        assert plan.get("auto_structural_calibration") is True
        assert plan.get("plan_items")
        causes = {row["problema_detectado"] for row in plan.get("structural_actions") or []}
        assert ACTION_PREFIX_DOMINANT in causes
        assert ACTION_UNDERCOVERED_DEZENAS in causes
        assert ACTION_EXCESSIVE_DEZENAS in causes
        memory = dict(plan.get("structural_calibration_memory") or {})
        assert memory.get("mission_id") == MISSION_ID
        assert memory.get("per_format_records", {}).get(f"{size}D")


def test_outside_formats_do_not_activate_auto_calibration() -> None:
    for size in (15, 24):
        assert is_structural_auto_calibration_format(size) is False
        plan = build_auto_calibration_plan_from_pool(_dominant_pool(17), game_size=size)
        assert plan.get("auto_structural_calibration") is False
        assert not plan.get("plan_items")


def test_memory_registers_cause_action_intensity_impact() -> None:
    plan = build_auto_calibration_plan_from_pool(_dominant_pool(18), game_size=18)
    row = dict((plan.get("structural_actions") or [])[0])
    assert row.get("problema_detectado")
    assert row.get("acao_aplicada")
    assert row.get("intensidade")
    assert row.get("impacto_esperado")
    catalog = build_structural_calibration_memory()["action_catalog"]
    assert row["problema_detectado"] in catalog


def test_rerank_applies_diversity_bonus() -> None:
    size = 20
    games = _dominant_pool(size)
    for idx, game in enumerate(games):
        game["profile_score"] = 10.0 - (idx * 0.01)
        game["score_ml"] = 90.0 - idx
    calibrated, bundle = apply_supervised_output_calibration(games, game_size=size, ml_enabled=True)
    assert bundle.get("structural_calibration_memory")
    assert bundle.get("structural_auto_calibration_mission_id") == MISSION_ID
    assert calibrated[0].get("calibration_applied") is True
    assert bundle.get("structural_actions_applied")


def test_central_ml_exposes_structural_auto_calibration_card() -> None:
    source = inspect.getsource(cockpit.render_ml_calibration_cockpit)
    card_source = inspect.getsource(cockpit._render_structural_auto_calibration_card)
    assert "_render_structural_auto_calibration_card" in source
    assert "Problema:" in card_source
    assert "Ação aplicada:" in card_source
    assert "Intensidade:" in card_source
    assert "Impacto esperado:" in card_source


def test_central_ml_no_nested_expander_in_observational_alerts() -> None:
    source = inspect.getsource(institutional_app._render_central_ml_observational_alerts)
    assert "st.expander(" not in source


def test_m_ml_067_rules_unchanged() -> None:
    assert classify_pair_overlap_level(15, game_size=17) == "atencao"
    assert classify_pair_overlap_level(16, game_size=17) == "ruim"
    assert classify_overlap_for_format(15, game_size=17)["level"] == "atencao"
    assert classify_overlap_for_format(17, game_size=17)["level"] == "critico"


def test_generic_logic_no_exclusive_17d_branch() -> None:
    from lotoia.ml import structural_auto_calibration as module

    source = inspect.getsource(module)
    assert "if game_size == 17" not in source
    assert "if size == 17" not in source
