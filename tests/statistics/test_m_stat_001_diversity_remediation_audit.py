"""M-STAT-001 — auditoria read-only da remediação de diversidade pool 15D."""

from __future__ import annotations

from typing import Any

import pytest

from lotoia.governance.institutional_agent_routing_matrix import AGENT_ESTATISTICO
from lotoia.statistics.diversity_remediation_audit import (
    MISSION_ID,
    _compare_top_slices,
    audit_diversity_remediation_cycle,
    build_low_diversity_audit_pool,
    capture_pool_audit_snapshot,
    classify_remediation_root_cause,
)


@pytest.fixture
def audit_history() -> list[Any]:
    class _Draw:
        def __init__(self, numbers: list[int]) -> None:
            self.numbers = numbers

    return [_Draw(sorted(range(1, 16)))] + [
        _Draw(sorted({((offset * 3 + index * 2) % 25) + 1 for index in range(15)}))
        for offset in range(12)
    ]


def test_capture_pool_audit_snapshot_gp20_top60() -> None:
    pool = build_low_diversity_audit_pool(pool_size=100, requested_count=20)
    snapshot = capture_pool_audit_snapshot(pool, game_size=15, requested_count=20)
    assert snapshot["pool_size"] == 100
    assert snapshot["candidate_pool_size"] == 60
    assert snapshot["diversity_score"] < 0.55


def test_compare_top_slice_changed() -> None:
    result = _compare_top_slices([(1, 2, 3), (4, 5, 6)], [(4, 5, 6), (1, 2, 3)])
    assert result["top_slice_changed"] is True
    assert result["candidates_reordered"] == 2


def test_audit_diversity_remediation_cycle_metrics(audit_history: list[Any]) -> None:
    pool = build_low_diversity_audit_pool(pool_size=100, requested_count=20)
    audit = audit_diversity_remediation_cycle(
        pool,
        game_size=15,
        requested_count=20,
        batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
        history=audit_history,
        seed=73,
    )
    assert audit["mission_id"] == MISSION_ID
    assert "before" in audit and "after" in audit
    assert "delta" in audit
    assert audit["delta"]["diversity_score"]["absolute"] is not None
    assert audit["top_slice"]["top_slice_changed"] in {True, False}
    assert audit["agent_routing"]["responsible_agent"] == AGENT_ESTATISTICO


def test_rerank_trace_candidates_counts(audit_history: list[Any]) -> None:
    pool = build_low_diversity_audit_pool(pool_size=100, requested_count=20)
    audit = audit_diversity_remediation_cycle(
        pool,
        game_size=15,
        requested_count=20,
        history=audit_history,
        seed=73,
    )
    rerank = dict(audit["corrective_actions"]["rerank_diversidade"])
    assert "candidates_reordered" in rerank
    assert "candidates_replaced" in rerank
    assert isinstance(rerank["candidates_reordered"], int)
    assert isinstance(rerank["candidates_replaced"], int)


def test_prefix_suffix_delta_present(audit_history: list[Any]) -> None:
    pool = build_low_diversity_audit_pool(pool_size=100, requested_count=20)
    audit = audit_diversity_remediation_cycle(
        pool,
        game_size=15,
        requested_count=20,
        history=audit_history,
        seed=73,
    )
    before = dict(audit["before"]["dominance"])
    after = dict(audit["after"]["dominance"])
    assert "prefix_top" in before
    assert "suffix_top" in after


def test_root_cause_classification(audit_history: list[Any]) -> None:
    pool = build_low_diversity_audit_pool(pool_size=100, requested_count=20)
    audit = audit_diversity_remediation_cycle(
        pool,
        game_size=15,
        requested_count=20,
        history=audit_history,
        seed=73,
    )
    root = classify_remediation_root_cause(audit)
    assert root["primary_cause"]
    assert root["recommended_next_mission"]
    assert root["responsible_agent"] == AGENT_ESTATISTICO
    assert root["maintain_diversity_threshold"] is True


def test_remediation_not_effective_for_low_diversity_pool(audit_history: list[Any]) -> None:
    pool = build_low_diversity_audit_pool(pool_size=100, requested_count=20)
    audit = audit_diversity_remediation_cycle(
        pool,
        game_size=15,
        requested_count=20,
        history=audit_history,
        seed=73,
    )
    assert audit["remediation_effective"] is False
    assert audit["after"]["diversity_score"] < 0.55
