from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_post_merge_checklist_deploy_only_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/checks/railway_post_merge_checklist.py", "--deploy-only", "--json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)
    assert report["checklist_id"] == "RAILWAY_POST_MERGE_CLOUD_ONLY"
    assert report["mode"] == "deploy_only"
    step_names = [step["name"] for step in report["steps"]]
    assert "deploy_validation" in step_names
    assert "railway_variables_audit" in step_names
