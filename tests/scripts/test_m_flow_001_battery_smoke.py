"""M-FLOW-001 — smoke da bateria GP:20 15D (3 ciclos, SQLite isolado)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.audits.m_flow_001_generation_calibration_battery import (
    MISSION_ID,
    aggregate_results,
    run_battery,
)


@pytest.fixture
def battery_output(tmp_path: Path) -> Path:
    return tmp_path / "m_flow_001"


def test_m_flow_001_battery_smoke_three_cycles(battery_output: Path) -> None:
    report = run_battery(cycles=3, db_path=battery_output / "stub.db", output_dir=battery_output)
    summary = dict(report.get("summary") or {})
    assert report.get("mission_id") == MISSION_ID
    assert summary.get("total_cycles") == 3
    assert int(summary.get("N_persisted", 0) or 0) == 3
    assert int(summary.get("N1_persisted", 0) or 0) == 3
    assert int(summary.get("plans_loaded", 0) or 0) == 3
    assert int(summary.get("plans_applied", 0) or 0) == 3
    assert report.get("purge_executed") is False
    assert (battery_output / "docs").exists() is False
    json_files = list(battery_output.glob("lotoia_m_flow_001_battery_*.json"))
    assert json_files


def test_aggregate_failure_table() -> None:
    agg = aggregate_results(
        [
            {"failure_stage": "OK"},
            {"failure_stage": "I", "generation_event_id_N1": 2},
            {"failure_stage": "I", "generation_event_id_N1": 4},
        ]
    )
    assert agg["summary"]["not_released_by_quality"] == 2
    assert agg["failure_table"][0]["failure"] == "I"
