from __future__ import annotations

from lotoia.workflows import WorkflowRecoveryEngine


def test_workflow_recovery_decides_retry_for_degraded_step() -> None:
    recovery = WorkflowRecoveryEngine(max_retries=2, cooldown_seconds=1)
    action = recovery.decide(workflow_id="wf-1", step_name="sync_latest", status="failed", service_name="result_sync")

    assert action.workflow_id == "wf-1"
    assert action.step_name == "sync_latest"
    assert action.should_retry is True
    assert action.reason == "service_degraded"
