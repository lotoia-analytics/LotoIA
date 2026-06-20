"""M-AGENT-002-FIX-02 — correção similarity/overlap do agent_operador_ml."""

from __future__ import annotations

import random
from typing import Any

import pytest

from lotoia.ml.agent_operador_ml_executor import (
    ACTION_RECOMPOSE_OVERLAP_DIVERSITY,
    ACTION_REDUCE_SIMILARITY_OVERLAP,
    DEFAULT_MAX_ATTEMPTS,
    _has_similarity_overlap_issues,
    _recompose_gp,
    execute_agent_operador_ml_pre_delivery,
    get_max_agent_attempts,
)
from tests.ml.test_m_agent_002_gp_executor import _distinct_pool, _game


def _high_overlap_card(base: list[int], variant: int) -> list[int]:
    shared = sorted(base[:13])
    available = [number for number in range(1, 26) if number not in shared]
    first = available[variant % len(available)]
    second = available[(variant * 3 + 1) % len(available)]
    if first == second:
        second = available[(variant * 3 + 2) % len(available)]
    return sorted(shared + [first, second])


def _build_ge48_like_selection(*, requested: int = 20) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    base = sorted(range(1, 16))
    shared = sorted(base[:13])
    available = [number for number in range(1, 26) if number not in shared]
    pair_options = [
        (available[i], available[j])
        for i in range(len(available))
        for j in range(i + 1, len(available))
    ]
    selected = [
        _game(sorted(shared + [pair_options[index % len(pair_options)][0], pair_options[index % len(pair_options)][1]]))
        for index in range(requested)
    ]
    pool = _distinct_pool(requested + 30, offset=7)
    rng = random.Random(48)
    while len(pool) < requested + 30:
        numbers = sorted(rng.sample(range(1, 26), 15))
        signature = tuple(numbers)
        if signature not in {tuple(sorted(g.get("numbers", []))) for g in pool}:
            pool.append(_game(numbers))
    return selected, pool


def test_default_max_attempts_allows_recompose() -> None:
    assert DEFAULT_MAX_ATTEMPTS >= 7
    assert get_max_agent_attempts() >= 7


def test_recompose_gp_is_reachable_after_dominance_sequence() -> None:
    pool = _distinct_pool(25)
    recomposed, action = _recompose_gp(
        pool,
        requested_quantity=10,
        card_format=15,
        batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
        attempt_index=6,
    )
    assert action in {"recompose_diverse_gp", "recompose_partial", "recompose_insufficient_pool", "recompose_compose_failed"}
    assert isinstance(recomposed, list)


def test_high_similarity_without_dominance_triggers_correction() -> None:
    selected, pool = _build_ge48_like_selection(requested=20)
    assert _has_similarity_overlap_issues(
        {
            "mean_similarity": 0.64,
            "max_overlap": 13,
            "structural_diversity": 0.36,
            "issue_count": 2,
            "issues": [
                {"tipo": "similaridade_media_gp_elevada"},
                {"tipo": "sobreposicao_maxima_elevada"},
            ],
        },
        card_format=15,
    )

    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=20,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
        batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
    )
    trace = dict(result.get("trace") or {})
    assert trace.get("agent_similarity_overlap_correction_attempted") is True
    assert trace.get("agent_noop_prevented") is True
    actions = list(trace.get("agent_actions_applied") or [])
    assert any(
        action in actions
        for action in (
            ACTION_REDUCE_SIMILARITY_OVERLAP,
            ACTION_RECOMPOSE_OVERLAP_DIVERSITY,
            "reduce_similarity_overlap_partial",
            "recompose_diverse_gp",
        )
    )
    assert len(result.get("games") or []) == 20
    assert trace.get("similarity_before") is not None
    assert trace.get("similarity_after") is not None


def test_max_overlap_reduces_or_declares_failure() -> None:
    selected, pool = _build_ge48_like_selection(requested=12)
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=12,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
    )
    trace = dict(result.get("trace") or {})
    before_overlap = int(trace.get("max_overlap_before", 99) or 99)
    after_overlap = int(trace.get("max_overlap_after", 99) or 99)
    improved = after_overlap < before_overlap or bool(trace.get("agent_similarity_overlap_correction_applied"))
    failed_with_evidence = bool(trace.get("agent_similarity_overlap_correction_failed")) and bool(
        trace.get("similarity_overlap_failure_evidence")
    )
    assert improved or failed_with_evidence


def test_low_diversity_triggers_real_attempt() -> None:
    selected, pool = _build_ge48_like_selection(requested=8)
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=8,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
    )
    trace = dict(result.get("trace") or {})
    assert float(trace.get("structural_diversity_before", 1.0) or 1.0) < 0.55
    assert trace.get("agent_similarity_overlap_correction_attempted") is True
    assert int(trace.get("overlap_reduction_candidates_evaluated", 0) or 0) > 0


def test_ge48_like_not_silent_noop() -> None:
    selected, pool = _build_ge48_like_selection(requested=20)
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=20,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
    )
    trace = dict(result.get("trace") or {})
    before = dict(trace.get("agent_before_metrics") or {})
    after = dict(trace.get("agent_after_metrics") or {})
    assert int(before.get("duplicates", 0) or 0) == 0
    assert float(before.get("mean_similarity", 0.0) or 0.0) >= 0.55
    assert int(before.get("max_overlap", 0) or 0) >= 12
    assert trace.get("agent_similarity_overlap_correction_attempted") is True
    changed = (
        float(after.get("mean_similarity", 9.0) or 9.0) < float(before.get("mean_similarity", 0.0) or 0.0)
        or int(after.get("max_overlap", 99) or 99) < int(before.get("max_overlap", 99) or 99)
        or float(after.get("structural_diversity", 0.0) or 0.0) > float(before.get("structural_diversity", 0.0) or 0.0)
        or bool(trace.get("agent_similarity_overlap_correction_failed"))
    )
    assert changed
    assert len(result.get("games") or []) == 20


def test_similarity_trace_fields_present() -> None:
    selected, pool = _build_ge48_like_selection(requested=6)
    result = execute_agent_operador_ml_pre_delivery(
        requested_quantity=6,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
    )
    trace = dict(result.get("trace") or {})
    for key in (
        "agent_similarity_overlap_correction_attempted",
        "agent_similarity_overlap_correction_action",
        "agent_similarity_overlap_correction_applied",
        "agent_noop_prevented",
        "similarity_before",
        "similarity_after",
        "max_overlap_before",
        "max_overlap_after",
        "structural_diversity_before",
        "structural_diversity_after",
        "issue_count_before",
        "issue_count_after",
        "overlap_reduction_candidates_evaluated",
        "pool_alternatives_available",
        "similarity_overlap_best_attempt_metrics",
    ):
        assert key in trace


def test_recompose_runs_within_attempt_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def _spy_recompose(*args: Any, **kwargs: Any) -> tuple[list[dict[str, Any]], str]:
        calls.append(int(kwargs.get("attempt_index", -1)))
        return [], "recompose_insufficient_pool"

    monkeypatch.setattr(
        "lotoia.ml.agent_operador_ml_executor._recompose_gp",
        _spy_recompose,
    )
    selected, pool = _build_ge48_like_selection(requested=5)
    execute_agent_operador_ml_pre_delivery(
        requested_quantity=5,
        card_format=15,
        selected_games=selected,
        candidate_pool=pool,
    )
    assert calls
    assert max(calls) >= 5
