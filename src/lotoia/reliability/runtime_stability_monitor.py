"""Runtime stability monitoring for resilient continuous operation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class StabilitySnapshot:
    """Point-in-time runtime stability snapshot."""

    created_at: datetime
    health_status: str
    degraded_services: tuple[str, ...]
    failed_processes: tuple[str, ...]
    scheduler_active: bool
    worker_active: bool
    observability_active: bool
    telemetry_active: bool
    stability_score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class RuntimeStabilityMonitor:
    """Detect degradation from runtime status, healthcheck, and dependency state."""

    def evaluate(self, runtime: Any) -> StabilitySnapshot:
        """Evaluate runtime stability."""

        health = runtime.container.resolve("healthcheck_service").check()
        status = runtime.status()
        failed_processes = tuple(
            process["name"]
            for process in status.processes
            if process["status"] not in {"running"}
            and process["name"] in {"lotoia-api", "lotoia-dashboard", "lotoia-worker", "lotoia-scheduler"}
        )
        worker_active = _worker_active(status.processes)
        scheduler_active = runtime.container.registry.has("scheduled_task_engine") and _service_running(
            status.processes,
            "lotoia-scheduler",
        )
        observability_active = bool(runtime.container.resolve("observability_report").snapshot.metrics)
        telemetry_active = runtime.container.registry.has("telemetry_tracker")
        degraded = tuple(sorted(set(failed_processes + (() if worker_active else ("lotoia-worker",)))))
        score_parts = (
            1.0 if health.healthy else 0.0,
            1.0 if not failed_processes else 0.0,
            1.0 if worker_active else 0.0,
            1.0 if scheduler_active else 0.0,
            1.0 if observability_active else 0.0,
            1.0 if telemetry_active else 0.0,
        )
        return StabilitySnapshot(
            created_at=datetime.now(UTC),
            health_status=health.status,
            degraded_services=degraded,
            failed_processes=failed_processes,
            scheduler_active=scheduler_active,
            worker_active=worker_active,
            observability_active=observability_active,
            telemetry_active=telemetry_active,
            stability_score=sum(score_parts) / len(score_parts),
            metadata={"runtime_id": runtime.container.context.runtime_id},
        )


def _worker_active(processes: tuple[dict[str, Any], ...]) -> bool:
    return _service_running(processes, "lotoia-worker")


def _service_running(processes: tuple[dict[str, Any], ...], service_name: str) -> bool:
    service = next((process for process in processes if process["name"] == service_name), None)
    if service is None:
        return True
    return service["status"] == "running"
