from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import importlib.util
from pathlib import Path
from typing import Any
import sys

from sqlalchemy import text

from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.database.database import get_session
from lotoia.ingestion import ResultSyncScheduler, ResultSyncService
from lotoia.reliability import RuntimeStabilityMonitor, ServiceRestartPolicy
from lotoia.observability import ObservabilityRepository

from .workflow_repository import WorkflowRepository


@dataclass(frozen=True, slots=True)
class WorkflowExecutionSnapshot:
    workflow_id: str
    workflow_name: str
    state: str
    summary: dict[str, Any]
    telemetry: dict[str, Any]
    steps: list[dict[str, Any]]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "state": self.state,
            "summary": self.summary,
            "telemetry": self.telemetry,
            "steps": self.steps,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class WorkflowRecoverySnapshot:
    workflow_id: str
    status: str
    retry_count: int
    recovered: bool
    notes: list[str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "status": self.status,
            "retry_count": self.retry_count,
            "recovered": self.recovered,
            "notes": self.notes,
            "metadata": self.metadata,
        }


def generate_public_games(*args: Any, **kwargs: Any) -> dict[str, Any]:
    module = WorkflowEngine._load_generate_public_games()
    return module(*args, **kwargs)


class WorkflowEngine:
    """Institutional workflow orchestration for governed operational automation."""

    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path
        self.repository = WorkflowRepository(db_path)
        self.observability = ObservabilityRepository(db_path)
        self.sync_service = ResultSyncService()
        self.reconciliation_engine = self._load_reconciliation_engine()(db_path)
        self.lifecycle = self._load_operational_lifecycle_engine()(db_path)
        self.restart_policy = ServiceRestartPolicy()
        self.stability_monitor = RuntimeStabilityMonitor()
        self.sync_scheduler = ResultSyncScheduler(service=self.sync_service)

    def run_sync_workflow(self, *, trigger: str = "manual") -> WorkflowExecutionSnapshot:
        run = self.repository.start_run(workflow_name="result_sync", trigger=trigger, context={"stage": "sync"})
        started = datetime.now(UTC)
        try:
            summary = self.sync_service.sync_latest()
            telemetry = {"synced_contests": len(summary.synced_contests), "fallback_used": summary.fallback_used}
            self.repository.record_step(run.workflow_id, step_name="sync_latest", status="ok", payload=summary.to_dict(), duration_ms=0.0)
            self.repository.finish_run(run.workflow_id, status="ok", duration_ms=(datetime.now(UTC) - started).total_seconds() * 1000, telemetry=telemetry)
            return WorkflowExecutionSnapshot(
                workflow_id=run.workflow_id,
                workflow_name="result_sync",
                state="completed",
                summary=summary.to_dict(),
                telemetry=telemetry,
                steps=self.repository.list_steps(workflow_id=run.workflow_id),
                metadata={"trigger": trigger},
            )
        except Exception as exc:  # pragma: no cover - guarded recovery path
            self.repository.record_step(run.workflow_id, step_name="sync_latest", status="failed", payload={}, duration_ms=0.0, error_message=str(exc))
            self.repository.finish_run(run.workflow_id, status="failed", duration_ms=(datetime.now(UTC) - started).total_seconds() * 1000, telemetry={"fallback_used": True}, error_message=str(exc))
            raise

    def run_generation_workflow(self, request: Any, *, source: str = "workflow", user_agent: str = "", ip_address: str = "") -> WorkflowExecutionSnapshot:
        run = self.repository.start_run(
            workflow_name="generation",
            trigger="manual",
            context={"source": source, "ml_enabled": bool(request.ml_enabled)},
        )
        started = datetime.now(UTC)
        payload = generate_public_games(
            request,
            db_path=self.db_path,
            source=source,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.repository.record_step(run.workflow_id, step_name="generate_public_games", status="ok", payload=payload, duration_ms=0.0)
        telemetry = self.build_telemetry()
        self.repository.finish_run(run.workflow_id, status="ok", duration_ms=(datetime.now(UTC) - started).total_seconds() * 1000, telemetry=telemetry)
        return WorkflowExecutionSnapshot(
            workflow_id=run.workflow_id,
            workflow_name="generation",
            state="completed",
            summary=payload.get("metadata", {}),
            telemetry=telemetry,
            steps=self.repository.list_steps(workflow_id=run.workflow_id),
            metadata={"source": source, "user_agent": user_agent, "ip_address": ip_address},
        )

    def run_closure_workflow(
        self,
        *,
        contest_id: int,
        generation_event_id: int,
        official_numbers: list[int],
        generated_games: list[dict[str, Any]],
        lead_id: int | None = None,
        cleanup: bool = True,
        report_dir: Path | None = None,
    ) -> WorkflowExecutionSnapshot:
        run = self.repository.start_run(
            workflow_name="daily_closure",
            trigger="scheduled",
            context={"contest_id": contest_id, "generation_event_id": generation_event_id},
        )
        started = datetime.now(UTC)
        report = self.lifecycle.close_day(
            contest_id=contest_id,
            generation_event_id=generation_event_id,
            generated_games=generated_games,
            official_numbers=official_numbers,
            lead_id=lead_id,
            cleanup=cleanup,
            report_dir=report_dir,
        )
        telemetry = self.build_telemetry()
        self.repository.record_step(run.workflow_id, step_name="close_day", status="ok", payload=report.to_dict(), duration_ms=0.0)
        self.repository.finish_run(run.workflow_id, status="ok", duration_ms=(datetime.now(UTC) - started).total_seconds() * 1000, telemetry=telemetry)
        return WorkflowExecutionSnapshot(
            workflow_id=run.workflow_id,
            workflow_name="daily_closure",
            state="completed",
            summary=report.to_dict(),
            telemetry=telemetry,
            steps=self.repository.list_steps(workflow_id=run.workflow_id),
            metadata={"contest_id": contest_id, "generation_event_id": generation_event_id},
        )

    def run_reconciliation_workflow(
        self,
        *,
        generation_event_id: int,
        contest_id: int,
        generated_games: list[dict[str, Any]],
        official_numbers: list[int],
        lead_id: int | None = None,
    ) -> WorkflowExecutionSnapshot:
        run = self.repository.start_run(
            workflow_name="reconciliation",
            trigger="manual",
            context={"contest_id": contest_id, "generation_event_id": generation_event_id},
        )
        started = datetime.now(UTC)
        summary = self.reconciliation_engine.reconcile_generation(
            generation_event_id=generation_event_id,
            contest_id=contest_id,
            generated_games=generated_games,
            official_numbers=official_numbers,
            lead_id=lead_id,
        )
        telemetry = self.build_telemetry()
        self.repository.record_step(run.workflow_id, step_name="reconcile_generation", status="ok", payload=summary.to_dict(), duration_ms=0.0)
        self.repository.finish_run(run.workflow_id, status="ok", duration_ms=(datetime.now(UTC) - started).total_seconds() * 1000, telemetry=telemetry)
        return WorkflowExecutionSnapshot(
            workflow_id=run.workflow_id,
            workflow_name="reconciliation",
            state="completed",
            summary=summary.to_dict(),
            telemetry=telemetry,
            steps=self.repository.list_steps(workflow_id=run.workflow_id),
            metadata={"contest_id": contest_id, "generation_event_id": generation_event_id},
        )

    def run_full_cycle(
        self,
        *,
        generation_request: PublicGenerationRequest | None = None,
        contest_id: int | None = None,
        generation_event_id: int | None = None,
        official_numbers: list[int] | None = None,
        source: str = "workflow",
        user_agent: str = "",
        ip_address: str = "",
        cleanup: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"steps": [], "status": "idle"}
        if generation_request is not None:
            generation_snapshot = self.run_generation_workflow(
                generation_request,
                source=source,
                user_agent=user_agent,
                ip_address=ip_address,
            )
            payload["steps"].append({"name": "generation", "snapshot": generation_snapshot.to_dict()})
            if generation_event_id is None:
                generation_event_id = self._latest_generation_event_id()
        sync_result = self.run_schedule_cycle()
        payload["steps"].append({"name": "sync", "snapshot": sync_result})
        if contest_id is not None and generation_event_id is not None and official_numbers is not None:
            with get_session(self.db_path) as session:
                rows = session.execute(
                    text(
                        """
                        SELECT numbers
                        FROM generated_games
                        WHERE generation_event_id = :generation_event_id
                        ORDER BY game_index ASC
                        """
                    ),
                    {"generation_event_id": generation_event_id},
                ).all()
                generated_games = [{"numbers": list(row[0] or [])} for row in rows]
            reconciliation_snapshot = self.run_reconciliation_workflow(
                generation_event_id=generation_event_id,
                contest_id=contest_id,
                generated_games=generated_games,
                official_numbers=official_numbers,
            )
            payload["steps"].append({"name": "reconciliation", "snapshot": reconciliation_snapshot.to_dict()})
            closure_snapshot = self.run_closure_workflow(
                contest_id=contest_id,
                generation_event_id=generation_event_id,
                official_numbers=official_numbers,
                generated_games=generated_games,
                cleanup=cleanup,
                report_dir=Path("reports") / "operational",
            )
            payload["steps"].append({"name": "closure", "snapshot": closure_snapshot.to_dict()})
            payload["status"] = "completed"
        elif generation_request is not None:
            payload["status"] = "partial"
        payload["telemetry"] = self.build_telemetry()
        return payload

    def run_schedule_cycle(self) -> dict[str, Any]:
        sync_summaries = self.sync_scheduler.run_due_checks()
        telemetry = self.build_telemetry()
        return {
            "sync_runs": [summary.to_dict() for summary in sync_summaries],
            "telemetry": telemetry,
            "status": "completed" if sync_summaries else "idle",
        }

    def build_telemetry(self) -> dict[str, Any]:
        runs = self.repository.list_runs(limit=200)
        steps = self.repository.list_steps(limit=500)
        failures = [run for run in runs if run.get("status") == "failed"]
        retries = sum(int(run.get("retries", 0) or 0) for run in runs)
        durations = [float(run["duration_ms"]) for run in runs if run.get("duration_ms") is not None]
        stability = self.stability_monitor.evaluate(self._runtime_stub())
        return {
            "workflow_count": len(runs),
            "step_count": len(steps),
            "failure_count": len(failures),
            "retry_count": retries,
            "average_duration_ms": sum(durations) / len(durations) if durations else 0.0,
            "latest_status": runs[0]["status"] if runs else "idle",
            "workflow_status": "healthy" if not failures else "degraded",
            "runtime_stability": stability.stability_score,
            "scheduler_active": stability.scheduler_active,
            "active_signals": len([step for step in steps if step.get("status") == "ok"]),
        }

    def build_dashboard(self) -> dict[str, Any]:
        telemetry = self.build_telemetry()
        runs = self.repository.list_runs(limit=10)
        steps = self.repository.list_steps(limit=20)
        health = "stable" if telemetry["workflow_status"] == "healthy" and telemetry["runtime_stability"] >= 0.70 else "watch"
        return {
            "summary": {
                "workflow_count": telemetry["workflow_count"],
                "step_count": telemetry["step_count"],
                "failure_count": telemetry["failure_count"],
                "retry_count": telemetry["retry_count"],
                "latest_status": telemetry["latest_status"],
                "workflow_status": telemetry["workflow_status"],
            },
            "health": {"status": health, "stability_score": telemetry["runtime_stability"], "scheduler_active": telemetry["scheduler_active"]},
            "runs": runs,
            "steps": steps,
            "active_workflows": [run for run in runs if run.get("status") == "running"],
            "alerts": self._alerts_from_telemetry(telemetry),
        }

    def build_recovery(self) -> WorkflowRecoverySnapshot:
        telemetry = self.build_telemetry()
        recovered = telemetry["workflow_status"] == "healthy"
        notes = [
            "workflows healthy" if recovered else "workflows require review",
            "scheduler active" if telemetry["scheduler_active"] else "scheduler inactive",
            "runtime stable" if telemetry["runtime_stability"] >= 0.70 else "runtime under watch",
        ]
        return WorkflowRecoverySnapshot(
            workflow_id="workflow-recovery",
            status=telemetry["workflow_status"],
            retry_count=telemetry["retry_count"],
            recovered=recovered,
            notes=notes,
            metadata={"alerts": len(self._alerts_from_telemetry(telemetry))},
        )

    def _alerts_from_telemetry(self, telemetry: dict[str, Any]) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        if telemetry["failure_count"]:
            alerts.append({"topic": "Falhas", "status": "alerta", "detail": f"{telemetry['failure_count']} workflows com falha."})
        if not telemetry["scheduler_active"]:
            alerts.append({"topic": "Agendamento", "status": "review", "detail": "Scheduler não está ativo no runtime atual."})
        if telemetry["retry_count"]:
            alerts.append({"topic": "Retries", "status": "review", "detail": f"{telemetry['retry_count']} tentativas registradas."})
        return alerts

    def _runtime_stub(self):
        class _Container:
            class _Context:
                runtime_id = "workflow-runtime"

            context = _Context()

            class _Registry:
                @staticmethod
                def has(name: str) -> bool:
                    return name in {"scheduled_task_engine", "telemetry_tracker", "observability_report", "healthcheck_service"}

            registry = _Registry()

            @staticmethod
            def resolve(name: str):
                if name == "healthcheck_service":
                    class _Health:
                        healthy = True
                        status = "healthy"

                        def check(self):
                            return self

                    return _Health()
                if name == "observability_report":
                    class _Obs:
                        snapshot = type("Snapshot", (), {"metrics": [1]})

                    return _Obs()
                raise KeyError(name)

        class _Status:
            processes = (
                {"name": "lotoia-api", "status": "running"},
                {"name": "lotoia-dashboard", "status": "running"},
                {"name": "lotoia-worker", "status": "running"},
                {"name": "lotoia-scheduler", "status": "running"},
            )

        class _Runtime:
            container = _Container()

            @staticmethod
            def status():
                return _Status()

        return _Runtime()

    def _latest_generation_event_id(self) -> int | None:
        with get_session(self.db_path) as session:
            row = session.execute(
                text(
                    """
                    SELECT id
                    FROM generation_events
                    ORDER BY created_at DESC, id DESC
                    LIMIT 1
                    """
                )
            ).first()
        return int(row[0]) if row else None

    @staticmethod
    def _module_from_path(module_name: str, relative_path: str) -> Any:
        module = sys.modules.get(module_name)
        if module is not None:
            return module
        module_path = Path(__file__).resolve().parents[1] / relative_path
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"unable to load module {module_name} from {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    @classmethod
    def _load_operational_lifecycle_engine(cls) -> Any:
        module = cls._module_from_path("lotoia._workflow_operational_lifecycle", "public/operational_lifecycle.py")
        return module.OperationalLifecycleEngine

    @classmethod
    def _load_reconciliation_engine(cls) -> Any:
        module = cls._module_from_path("lotoia._workflow_reconciliation", "public/reconciliation.py")
        return module.ReconciliationEngine

    @classmethod
    def _load_generate_public_games(cls) -> Any:
        module = cls._module_from_path("lotoia._workflow_public_service", "public/service.py")
        return module.generate_public_games
