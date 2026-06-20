"""M-AGENT-002-VALID-01 — validação operacional do executor GP + formato dinâmico."""

from __future__ import annotations

import inspect
import random
from typing import Any
from unittest.mock import patch

import pytest

import dashboard.institutional_app as institutional_app
from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_clean_law15_runtime import render_agent_operador_ml_summary
from lotoia.generator.basic_generator import _build_game
from lotoia.ml.agent_operador_ml_executor import (
    GP_ENTREGUE_ACEITAVEL,
    GP_ENTREGUE_COM_ALERTA,
    GP_FALHA_POOL_INSUFICIENTE,
    execute_agent_operador_ml_pre_delivery,
)
from tests.ml.test_m_agent_002_gp_executor import (
    _distinct_pool,
    _with_shared_suffix,
    _with_shared_triple,
)

TRACE_REQUIRED_KEYS = (
    "agent_operador_ml_applied",
    "agent_name",
    "agent_mode",
    "agent_trace_id",
    "gp_requested_quantity",
    "gp_delivered_quantity",
    "gp_delivery_status",
    "agent_before_metrics",
    "agent_after_metrics",
    "agent_actions_applied",
    "agent_improvement_summary",
    "agent_respected_core_002",
    "agent_respected_law_15",
)


def _game(numbers: list[int]) -> dict[str, Any]:
    row = _build_game(sorted(set(numbers))[:15])
    row["lei15_core_002_applied"] = True
    return row


def _unique_pool(size: int, *, seed: int = 42) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    pool: list[dict[str, Any]] = []
    seen: set[tuple[int, ...]] = set()
    attempts = 0
    while len(pool) < size and attempts < 500_000:
        attempts += 1
        numbers = sorted(rng.sample(range(1, 26), 15))
        signature = tuple(numbers)
        if signature in seen:
            continue
        seen.add(signature)
        pool.append(_game(numbers))
    if len(pool) < size:
        raise RuntimeError(f"unable to build {size} unique cards for validation battery")
    return pool


@pytest.mark.parametrize("requested_quantity", [5, 20, 30])
def test_gp_variable_quantity_delivers_unique_games(requested_quantity: int) -> None:
    unique_pool = _unique_pool(requested_quantity + 12)
    selected = unique_pool[:requested_quantity]
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=requested_quantity,
        card_format=15,
        selected_games=selected,
        candidate_pool=unique_pool,
    )
    games = list(result.get("games") or [])
    signatures = {tuple(sorted(g.get("numbers", []))) for g in games}
    assert len(games) == requested_quantity
    assert len(signatures) == requested_quantity
    assert result["delivery_status"] in {GP_ENTREGUE_ACEITAVEL, GP_ENTREGUE_COM_ALERTA}


def test_no_hardcoded_card_format_15_in_agent_call() -> None:
    source = inspect.getsource(institutional_app._run_clean_law15_generation)
    assert "card_format=15" not in source
    assert "resolved_card_format" in source
    assert "selected_card_format" in source


def test_agent_receives_dynamic_card_format_from_generation_flow() -> None:
    captured: dict[str, Any] = {}

    def _capture_agent(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {
            "games": list(kwargs.get("selected_games") or []),
            "trace": {"agent_operador_ml_applied": True, "gp_delivery_status": GP_ENTREGUE_ACEITAVEL},
            "delivery_status": GP_ENTREGUE_ACEITAVEL,
            "agent_applied": True,
        }

    sovereign_payload = {
        "games": [_game(list(range(1, 16)))],
        "gp_candidate_pool": _distinct_pool(8),
        "ml_enabled": False,
        "game_size": 15,
        "analysis_batch_label": "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
    }

    with patch.object(
        institutional_app,
        "_invoke_sovereign_adm_generate_best_games",
        return_value=sovereign_payload,
    ), patch.object(
        institutional_app,
        "_is_sovereign_generation_blocked",
        return_value=False,
    ), patch(
        "lotoia.ml.agent_operador_ml_executor.execute_agent_operador_ml_pre_delivery",
        side_effect=_capture_agent,
    ), patch(
        "lotoia.ml.agent_operador_ml_executor.is_agent_operador_ml_enabled",
        return_value=True,
    ), patch.object(
        institutional_app,
        "output_commander_validate_games",
        return_value={"status_comandante_saida": "APROVADO", "quantidade_jogos_rejeitados": 0},
    ), patch.object(
        institutional_app,
        "load_all_output_signatures",
        return_value=set(),
    ):
        result = institutional_app._run_clean_law15_generation(
            requested_count=1,
            selected_card_format=17,
        )

    assert int(captured.get("card_format", 0) or 0) == 17
    assert int(result.get("selected_card_format", 0) or 0) == 17


def test_scenario_duplicates_corrected_with_sufficient_pool() -> None:
    pool = _distinct_pool(15)
    duplicate = dict(pool[0])
    selected = [duplicate, dict(duplicate), *pool[1:4]]
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=5,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
    )
    trace = dict(result.get("trace") or {})
    after = dict(trace.get("agent_after_metrics") or {})
    assert int(after.get("duplicates", -1)) == 0
    assert int(trace.get("gp_delivered_quantity", 0) or 0) == 5
    assert result["delivery_status"] != GP_FALHA_POOL_INSUFICIENTE
    actions = " ".join(trace.get("agent_actions_applied") or [])
    assert "deduplicate" in actions


def test_scenario_overlap_excessive_attempts_reduction() -> None:
    base = _game(list(range(1, 16)))
    near_clone = _game(list(range(1, 14)) + [24, 25])
    pool = _distinct_pool(12) + [near_clone]
    selected = [dict(base), dict(near_clone), *pool[:3]]
    before_overlap = execute_agent_operador_ml_pre_delivery(
        requested_quantity=1,
        card_format=15,
        selected_games=selected[:1],
        candidate_pool=pool,
    )
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=5,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
    )
    trace = dict(result.get("trace") or {})
    before = dict(trace.get("agent_before_metrics") or {})
    after = dict(trace.get("agent_after_metrics") or {})
    assert int(after.get("max_overlap", 99)) <= int(before.get("max_overlap", 99))
    assert trace.get("agent_improvement_summary")
    _ = before_overlap


def test_scenario_suffix_dominance_registers_before_after() -> None:
    pool = _with_shared_suffix(_distinct_pool(14), (23, 24, 25))
    selected = pool[:6]
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=6,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
    )
    trace = dict(result.get("trace") or {})
    assert trace.get("agent_before_metrics")
    assert trace.get("agent_after_metrics")
    assert trace.get("agent_actions_applied") is not None


def test_scenario_prefix_triple_dominance_corrective_action() -> None:
    pool = _with_shared_triple(_distinct_pool(16))
    selected = pool[:5]
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=5,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
    )
    trace = dict(result.get("trace") or {})
    actions = list(trace.get("agent_actions_applied") or [])
    assert actions
    assert all(
        game.get("game_quality_status") != "critical"
        for game in result.get("games") or []
        if game.get("game_quality_status")
    )


def test_scenario_pool_insufficient_objective_failure() -> None:
    pool = _distinct_pool(2)
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=8,
        card_format=15,
        selected_games=pool,
        candidate_pool=pool,
    )
    assert result["delivery_status"] == GP_FALHA_POOL_INSUFICIENTE
    evidence = dict(result.get("trace", {}).get("gp_failure_evidence") or {})
    for key in (
        "requested_quantity",
        "possible_quantity",
        "pool_size",
        "unique_pool_candidates",
        "conformant_pool_candidates",
    ):
        assert key in evidence
    trace = dict(result.get("trace") or {})
    assert trace.get("gp_failure_reason")


def test_scenario_sufficient_material_delivers() -> None:
    pool = _distinct_pool(25)
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=20,
        card_format=15,
        selected_games=pool[:20],
        candidate_pool=pool,
    )
    assert result["delivery_status"] in {GP_ENTREGUE_ACEITAVEL, GP_ENTREGUE_COM_ALERTA}
    assert len(result.get("games") or []) == 20


def test_trace_contract_complete() -> None:
    pool = _distinct_pool(10)
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=4,
        card_format=15,
        selected_games=pool[:4],
        candidate_pool=pool,
    )
    trace = dict(result.get("trace") or {})
    for key in TRACE_REQUIRED_KEYS:
        assert key in trace, f"missing trace key: {key}"


def test_generation_context_persists_agent_trace_fields() -> None:
    persist_source = inspect.getsource(institutional_app._persist_clean_law15_generation_history)
    assert "agent_operador_ml" in persist_source
    assert "agent_operador_ml_applied" in persist_source or "**dict(result.get(\"agent_operador_ml\")" in persist_source


def test_adm_flow_loaders_regression() -> None:
    assert callable(institutional_app.main)
    assert callable(render_agent_operador_ml_summary)
    assert hasattr(institutional_app, "_run_clean_law15_generation")
    assert hasattr(institutional_app, "_load_accumulated_analytical_rows_light")
    assert hasattr(institutional_app, "_load_official_conference_generation_groups")


def test_m_ops_078_fix_02_not_required_for_this_mission_note() -> None:
    conference_source = inspect.getsource(institutional_app._run_institutional_conference)
    if "_prepare_conference_group" not in conference_source:
        pytest.skip("M-OPS-078-FIX-02 ainda não aplicada — Conferir pode usar filtro legado de lote inteiro")


def test_build_marker_v85() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v86"


def test_governance_contract_check_passes() -> None:
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "checks" / "governance_contract_check.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
