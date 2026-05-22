from __future__ import annotations

from pathlib import Path

from lotoia.workflows import build_workflow_dashboard


def test_workflow_dashboard_exposes_operational_summary(tmp_path: Path) -> None:
    dashboard = build_workflow_dashboard(tmp_path / "lotoia.db")

    assert dashboard["state"] in {"operational", "review"}
    assert "summary" in dashboard
    assert "live_workflows" in dashboard
    assert "alerts" in dashboard
