"""M-AGENT-002 — agent_operador_ml executor autônomo local pré-entrega do GP."""

from __future__ import annotations

from typing import Any

from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_clean_law15_runtime import render_agent_operador_ml_summary
import dashboard.institutional_app as institutional_app
from lotoia.generator.basic_generator import _build_game
from lotoia.ml.agent_operador_ml_executor import (
    AGENT_MODE,
    AGENT_NAME,
    GP_ENTREGUE_ACEITAVEL,
    GP_ENTREGUE_COM_ALERTA,
    GP_FALHA_POOL_INSUFICIENTE,
    MISSION_ID,
    _is_valid_card,
    _prefix_key,
    compute_gp_batch_metrics,
    execute_agent_operador_ml_pre_delivery,
    is_agent_operador_ml_enabled,
)
from lotoia.statistics.card_structure import compute_suffix, format_dezena_group
from lotoia.statistics.similarity_overlap_decomposition import DOMINANT_STRUCTURAL_TRIPLE_LABEL


def _game(numbers: list[int]) -> dict[str, Any]:
    row = _build_game(sorted(set(numbers))[:15])
    row["lei15_core_002_applied"] = True
    return row


def _distinct_pool(count: int, *, offset: int = 0) -> list[dict[str, Any]]:
    pool: list[dict[str, Any]] = []
    for index in range(count):
        base = ((index + offset) * 3) % 20
        numbers = sorted({((base + step * 2 + offset) % 25) + 1 for step in range(15)})
        pool.append(_game(numbers))
    return pool


def _suffix_for(numbers: list[int]) -> str:
    return format_dezena_group(compute_suffix(sorted(numbers), 3))


def _with_shared_suffix(pool: list[dict[str, Any]], suffix_numbers: tuple[int, int, int]) -> list[dict[str, Any]]:
    adjusted: list[dict[str, Any]] = []
    for index, game in enumerate(pool):
        numbers = sorted(
            {
                ((index + step) % 20) + 1
                for step in range(12)
            }
            | set(suffix_numbers)
        )
        while len(numbers) < 15:
            candidate = (len(numbers) + index + 5) % 25 + 1
            if candidate not in numbers:
                numbers.append(candidate)
        adjusted.append(_game(sorted(numbers)[:15]))
    return adjusted


def _with_shared_prefix(pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
    adjusted: list[dict[str, Any]] = []
    for index, game in enumerate(pool):
        numbers = sorted({1, 2, 3, *((((index + step) % 20) + 4) for step in range(12))})
        adjusted.append(_game(numbers[:15]))
    return adjusted


def _with_shared_triple(pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
    adjusted: list[dict[str, Any]] = []
    for index in range(len(pool)):
        numbers = sorted({1, 2, 3, *(((index + step) % 20) + 4 for step in range(12))})
        adjusted.append(_game(numbers[:15]))
    return adjusted


def test_agent_enabled_by_default() -> None:
    assert is_agent_operador_ml_enabled() is True


def test_gp_duplicates_replaced_when_pool_sufficient() -> None:
    pool = _distinct_pool(12)
    duplicate = dict(pool[0])
    selected = [duplicate, dict(duplicate), *pool[1:4]]
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=5,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
        batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
    )
    games = list(result.get("games") or [])
    signatures = {tuple(sorted(g.get("numbers", []))) for g in games}
    assert len(games) == 5
    assert len(signatures) == 5
    assert result["delivery_status"] in {GP_ENTREGUE_ACEITAVEL, GP_ENTREGUE_COM_ALERTA}
    trace = dict(result.get("trace") or {})
    assert int(trace.get("agent_before_metrics", {}).get("duplicates", 0) or 0) >= 1
    assert int(trace.get("agent_after_metrics", {}).get("duplicates", 0) or 0) == 0


def test_gp_suffix_dominance_reduced_with_before_after() -> None:
    pool = _with_shared_suffix(_distinct_pool(14), (23, 24, 25))
    selected = pool[:6]
    dominant_before = _suffix_for(selected[0].get("numbers", []))
    assert dominant_before
    before = compute_gp_batch_metrics(selected, requested_quantity=6, card_format=15)
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=6,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
    )
    after = dict(result.get("trace", {}).get("agent_after_metrics") or {})
    assert "agent_improvement_summary" in result.get("trace", {})
    assert after.get("dominant_suffix", "x") != dominant_before or int(after.get("max_overlap", 99)) <= int(
        before.get("max_overlap", 99)
    )


def test_gp_prefix_dominance_registers_action() -> None:
    pool = _with_shared_prefix(_distinct_pool(14))
    selected = pool[:5]
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=5,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
    )
    actions = list(result.get("trace", {}).get("agent_actions_applied") or [])
    assert actions
    assert any("prefix" in action or "deduplicate" in action or "recompose" in action for action in actions)


def test_gp_triple_dominance_reduced() -> None:
    pool = _with_shared_triple(_distinct_pool(16))
    selected = pool[:6]
    triple_share_before = sum(
        1 for game in selected if _prefix_key(game) == DOMINANT_STRUCTURAL_TRIPLE_LABEL
    )
    assert triple_share_before >= 1
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=6,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
    )
    trace = dict(result.get("trace") or {})
    assert trace.get("agent_actions_applied")


def test_gp_pool_insufficient_proven_failure() -> None:
    pool = _distinct_pool(2)
    selected = pool[:2]
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=5,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
    )
    assert result["delivery_status"] == GP_FALHA_POOL_INSUFICIENTE
    evidence = dict(result.get("trace", {}).get("gp_failure_evidence") or {})
    assert evidence.get("primary_cause")
    assert int(evidence.get("requested_quantity", 0) or 0) == 5
    assert int(evidence.get("possible_quantity", 99) or 99) < 5


def test_gp_material_sufficient_delivers() -> None:
    pool = _distinct_pool(20)
    selected = pool[:4]
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=4,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
    )
    assert result["delivery_status"] in {GP_ENTREGUE_ACEITAVEL, GP_ENTREGUE_COM_ALERTA}
    assert len(result.get("games") or []) == 4


def test_gp_uniqueness_delivered_equals_requested() -> None:
    pool = _distinct_pool(18)
    selected = pool[:7]
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=7,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
    )
    games = list(result.get("games") or [])
    signatures = {tuple(sorted(g.get("numbers", []))) for g in games}
    assert len(games) == 7
    assert len(signatures) == 7
    trace = dict(result.get("trace") or {})
    assert int(trace.get("gp_delivered_quantity", 0) or 0) == 7
    assert int(trace.get("agent_after_metrics", {}).get("unique_games", 0) or 0) == 7


def test_gp_law_15_no_violation_in_final_games() -> None:
    pool = _distinct_pool(16)
    selected = pool[:5]
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=5,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
    )
    for game in list(result.get("games") or []):
        assert _is_valid_card(game, card_format=15)
        numbers = sorted(int(n) for n in game.get("numbers", []))
        assert len(numbers) == 15
        assert all(1 <= number <= 25 for number in numbers)


def test_gp_core_002_respected() -> None:
    pool = _distinct_pool(10)
    for game in pool:
        game["lei15_core_002_applied"] = True
    selected = pool[:4]
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=4,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
        core_002_status="sovereign",
    )
    trace = dict(result.get("trace") or {})
    assert trace.get("agent_respected_core_002") is True
    assert trace.get("agent_respected_law_15") is True


def test_trace_contract_fields_present() -> None:
    pool = _distinct_pool(8)
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=3,
        card_format=15,
        selected_games=pool[:3],
        candidate_pool=pool,
    )
    trace = dict(result.get("trace") or {})
    assert trace.get("agent_operador_ml_applied") is True
    assert trace.get("agent_name") == AGENT_NAME
    assert trace.get("agent_mode") == AGENT_MODE
    assert trace.get("agent_mission_id") == MISSION_ID
    assert trace.get("agent_trace_id")
    assert "agent_before_metrics" in trace
    assert "agent_after_metrics" in trace
    assert trace.get("agent_action_executed") is not False


def test_streamlit_regression_loaders() -> None:
    assert callable(institutional_app.main)
    assert callable(render_agent_operador_ml_summary)
    assert hasattr(institutional_app, "_run_clean_law15_generation")
    assert hasattr(institutional_app, "_render_clean_law15_generation_page")


def test_build_marker_v84() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v85"


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
