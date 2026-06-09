from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from lotoia.database.database import DEFAULT_DATABASE_PATH, WorkflowRun, WorkflowStep, get_session
from lotoia.database.database import WorkflowEvent


@dataclass(frozen=True, slots=True)
class WorkflowRunSnapshot:
    workflow_id: str
    workflow_name: str
    trigger: str
    status: str
    retries: int
    started_at: datetime
    finished_at: datetime | None
    duration_ms: float | None
    context: dict[str, Any]
    telemetry: dict[str, Any]
    error_message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "trigger": self.trigger,
            "status": self.status,
            "retries": self.retries,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "context": self.context,
            "telemetry": self.telemetry,
            "error_message": self.error_message,
        }


@dataclass(frozen=True, slots=True)
class WorkflowStepSnapshot:
    workflow_id: str
    step_name: str
    status: str
    attempt: int
    started_at: datetime
    finished_at: datetime | None
    duration_ms: float | None
    payload: dict[str, Any]
    error_message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "step_name": self.step_name,
            "status": self.status,
            "attempt": self.attempt,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "payload": self.payload,
            "error_message": self.error_message,
        }


class WorkflowRepository:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def start_run(self, *, workflow_name: str, trigger: str = "manual", context: dict[str, Any] | None = None) -> WorkflowRunSnapshot:
        workflow_id = f"workflow-{uuid4().hex}"
        with get_session(self.db_path) as session:
            session.add(
                WorkflowEvent(
                    workflow_id=workflow_id,
                    workflow_name=workflow_name,
                    correlation_id=workflow_id,
                    stage=str((context or {}).get("stage", "")),
                    source=trigger,
                    status="running",
                    payload=context or {},
                )
            )
            session.add(
                WorkflowRun(
                    workflow_id=workflow_id,
                    workflow_name=workflow_name,
                    trigger=trigger,
                    status="running",
                    context_json=context or {},
                    telemetry_json={},
                )
            )
            session.commit()
        return WorkflowRunSnapshot(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            trigger=trigger,
            status="running",
            retries=0,
            started_at=datetime.now(UTC),
            finished_at=None,
            duration_ms=None,
            context=context or {},
            telemetry={},
            error_message="",
        )

    def finish_run(self, workflow_id: str, *, status: str, duration_ms: float | None = None, telemetry: dict[str, Any] | None = None, error_message: str = "") -> None:
        with get_session(self.db_path) as session:
            run = session.query(WorkflowRun).filter(WorkflowRun.workflow_id == workflow_id).first()
            if run is None:
                return
            run.status = status
            run.finished_at = datetime.now(UTC)
            run.duration_ms = duration_ms
            run.telemetry_json = telemetry or {}
            run.error_message = error_message
            event = session.query(WorkflowEvent).filter(WorkflowEvent.workflow_id == workflow_id).first()
            if event is not None:
                event.status = status
                event.finished_at = datetime.now(UTC)
                event.duration_ms = duration_ms
                event.payload = telemetry or {}
                event.error_message = error_message
            session.commit()

    def record_step(self, workflow_id: str, *, step_name: str, status: str, payload: dict[str, Any] | None = None, duration_ms: float | None = None, attempt: int = 1, error_message: str = "") -> WorkflowStepSnapshot:
        with get_session(self.db_path) as session:
            row = WorkflowStep(
                workflow_id=workflow_id,
                step_name=step_name,
                status=status,
                attempt=attempt,
                duration_ms=duration_ms,
                payload_json=payload or {},
                error_message=error_message,
            )
            session.add(row)
            session.commit()
            return WorkflowStepSnapshot(
                workflow_id=workflow_id,
                step_name=step_name,
                status=status,
                attempt=attempt,
                started_at=row.started_at,
                finished_at=row.finished_at,
                duration_ms=duration_ms,
                payload=payload or {},
                error_message=error_message,
            )

    def list_runs(self, *, limit: int = 100) -> list[dict[str, Any]]:
        with get_session(self.db_path) as session:
            rows = (
                session.query(WorkflowRun)
                .order_by(WorkflowRun.started_at.desc(), WorkflowRun.id.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": row.id,
                    "workflow_id": row.workflow_id,
                    "workflow_name": row.workflow_name,
                    "trigger": row.trigger,
                    "status": row.status,
                    "retries": row.retries,
                    "started_at": row.started_at,
                    "finished_at": row.finished_at,
                    "duration_ms": row.duration_ms,
                    "context_json": row.context_json,
                    "telemetry_json": row.telemetry_json,
                    "error_message": row.error_message,
                }
                for row in rows
            ]

    def list_steps(self, *, workflow_id: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        with get_session(self.db_path) as session:
            query = session.query(WorkflowStep).order_by(WorkflowStep.started_at.desc(), WorkflowStep.id.desc())
            if workflow_id is not None:
                query = query.filter(WorkflowStep.workflow_id == workflow_id)
            rows = query.limit(limit).all()
            return [
                {
                    "id": row.id,
                    "workflow_id": row.workflow_id,
                    "step_name": row.step_name,
                    "status": row.status,
                    "attempt": row.attempt,
                    "started_at": row.started_at,
                    "finished_at": row.finished_at,
                    "duration_ms": row.duration_ms,
                    "payload_json": row.payload_json,
                    "error_message": row.error_message,
                }
                for row in rows
            ]
