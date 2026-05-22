from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "WorkflowDashboardSnapshot",
    "WorkflowEngine",
    "WorkflowExecutionSnapshot",
    "WorkflowRecoverySnapshot",
    "WorkflowRecoveryAction",
    "WorkflowRecoveryEngine",
    "WorkflowSchedule",
    "WorkflowScheduler",
    "WorkflowRepository",
    "WorkflowRunSnapshot",
    "WorkflowStepSnapshot",
    "build_workflow_dashboard",
]


_EXPORTS: dict[str, tuple[str, str]] = {
    "WorkflowDashboardSnapshot": ("lotoia.workflows.workflow_dashboard", "WorkflowDashboardSnapshot"),
    "WorkflowEngine": ("lotoia.workflows.workflow_engine", "WorkflowEngine"),
    "WorkflowExecutionSnapshot": ("lotoia.workflows.workflow_engine", "WorkflowExecutionSnapshot"),
    "WorkflowRecoverySnapshot": ("lotoia.workflows.workflow_engine", "WorkflowRecoverySnapshot"),
    "WorkflowRecoveryAction": ("lotoia.workflows.workflow_recovery", "WorkflowRecoveryAction"),
    "WorkflowRecoveryEngine": ("lotoia.workflows.workflow_recovery", "WorkflowRecoveryEngine"),
    "WorkflowSchedule": ("lotoia.workflows.workflow_scheduler", "WorkflowSchedule"),
    "WorkflowScheduler": ("lotoia.workflows.workflow_scheduler", "WorkflowScheduler"),
    "WorkflowRepository": ("lotoia.workflows.workflow_repository", "WorkflowRepository"),
    "WorkflowRunSnapshot": ("lotoia.workflows.workflow_repository", "WorkflowRunSnapshot"),
    "WorkflowStepSnapshot": ("lotoia.workflows.workflow_repository", "WorkflowStepSnapshot"),
    "build_workflow_dashboard": ("lotoia.workflows.workflow_dashboard", "build_workflow_dashboard"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
