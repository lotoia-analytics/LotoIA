"""Feedback loop status — Cobertura Nova (M-FEEDBACK UI)."""

from __future__ import annotations

from dashboard.institutional_structural_coverage_modern_v2 import resolve_feedback_loop_status


def test_feedback_loop_status_waiting_without_conference() -> None:
    badge = resolve_feedback_loop_status(
        feedback_stats={"total_feedback": 0, "pending_contests": 0},
        conference_stats={"total_runs": 0},
    )
    assert badge["status_color"] == "gray"
    assert "AGUARDANDO" in badge["status"]


def test_feedback_loop_status_active_when_no_pending() -> None:
    badge = resolve_feedback_loop_status(
        feedback_stats={"total_feedback": 3, "pending_contests": 0, "latest_contest": 3710},
        conference_stats={"total_runs": 5},
    )
    assert badge["status_color"] == "green"
    assert "ATIVO" in badge["status"]
    assert "3710" in badge["status"]


def test_feedback_loop_status_underutilized_without_feedback_rows() -> None:
    badge = resolve_feedback_loop_status(
        feedback_stats={"total_feedback": 0, "pending_contests": 2},
        conference_stats={"total_runs": 4},
    )
    assert badge["status_color"] == "yellow"
    assert "SUBUTILIZADO" in badge["status"]


def test_feedback_loop_status_partial_when_pending_remain() -> None:
    badge = resolve_feedback_loop_status(
        feedback_stats={"total_feedback": 2, "pending_contests": 1},
        conference_stats={"total_runs": 3},
    )
    assert badge["status_color"] == "yellow"
    assert "PARCIAL" in badge["status"]
