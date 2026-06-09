from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from uuid import uuid4

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    RuntimeExecution,
    RuntimeLineage,
    RuntimeMetric,
    RuntimeSnapshot,
    RuntimeSpan,
    get_session,
)
from lotoia.observability.distributed_tracing import DistributedTracer, TraceSpan
from lotoia.observability.metrics_registry import MetricSample, MetricsRegistry


class ObservabilityRepository:
    """Persist runtime execution, tracing, metrics, lineage, and snapshots."""

    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def start_execution(
        self,
        *,
        flow_name: str,
        stage: str = "",
        context: dict[str, Any] | None = None,
        execution_id: str | None = None,
    ) -> str:
        execution_id = execution_id or f"exec-{uuid4().hex}"
        with get_session(self.db_path) as session:
            session.add(
                RuntimeExecution(
                    execution_id=execution_id,
                    flow_name=flow_name,
                    stage=stage,
                    status="running",
                    context_json=context or {},
                )
            )
            session.commit()
        return execution_id

    def finish_execution(
        self,
        execution_id: str,
        *,
        status: str = "ok",
        stage: str = "",
        duration_ms: float | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        with get_session(self.db_path) as session:
            execution = session.query(RuntimeExecution).filter(RuntimeExecution.execution_id == execution_id).first()
            if execution is None:
                return
            execution.status = status
            if stage:
                execution.stage = stage
            execution.finished_at = datetime.now(UTC)
            execution.duration_ms = duration_ms
            execution.context_json = {**execution.context_json, **(context or {})}
            session.commit()

    def record_span(self, execution_id: str, span: TraceSpan, *, stage: str = "") -> dict[str, Any]:
        with get_session(self.db_path) as session:
            row = RuntimeSpan(
                execution_id=execution_id,
                trace_id=span.trace_id,
                span_id=span.span_id,
                parent_span_id=span.parent_span_id,
                name=span.name,
                stage=stage,
                status=span.status,
                started_at=span.started_at,
                finished_at=span.finished_at,
                duration_ms=span.duration_ms,
                attributes_json=span.attributes,
            )
            session.add(row)
            session.commit()
            return {"span_id": row.span_id, "execution_id": execution_id}

    def record_metric(
        self,
        execution_id: str,
        sample: MetricSample,
        *,
        stage: str = "",
    ) -> dict[str, Any]:
        with get_session(self.db_path) as session:
            row = RuntimeMetric(
                execution_id=execution_id,
                name=sample.name,
                value=sample.value,
                metric_type=str(sample.metric_type),
                labels_json={**sample.labels, **({"stage": stage} if stage else {})},
                metadata_json=sample.metadata,
                observed_at=sample.observed_at,
            )
            session.add(row)
            session.commit()
            return {"metric_id": row.id, "execution_id": execution_id}

    def record_lineage(
        self,
        execution_id: str,
        *,
        entity_type: str,
        entity_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with get_session(self.db_path) as session:
            row = RuntimeLineage(
                execution_id=execution_id,
                entity_type=entity_type,
                entity_id=entity_id,
                event_type=event_type,
                payload_json=payload or {},
            )
            session.add(row)
            session.commit()
            return {"lineage_id": row.id, "execution_id": execution_id}

    def record_snapshot(
        self,
        execution_id: str,
        *,
        snapshot_type: str,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        snapshot_id = f"obs-snapshot-{uuid4().hex}"
        with get_session(self.db_path) as session:
            row = RuntimeSnapshot(
                execution_id=execution_id,
                snapshot_id=snapshot_id,
                snapshot_type=snapshot_type,
                payload_json=payload,
                metadata_json=metadata or {},
            )
            session.add(row)
            session.commit()
            return {"snapshot_id": row.snapshot_id, "execution_id": execution_id}

    def list_executions(self, *, limit: int = 100) -> list[dict[str, Any]]:
        with get_session(self.db_path) as session:
            rows = (
                session.query(RuntimeExecution)
                .order_by(RuntimeExecution.started_at.desc(), RuntimeExecution.id.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": row.id,
                    "execution_id": row.execution_id,
                    "flow_name": row.flow_name,
                    "stage": row.stage,
                    "status": row.status,
                    "started_at": row.started_at,
                    "finished_at": row.finished_at,
                    "duration_ms": row.duration_ms,
                    "context_json": row.context_json,
                }
                for row in rows
            ]

    def list_spans(self, *, execution_id: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        with get_session(self.db_path) as session:
            query = session.query(RuntimeSpan).order_by(RuntimeSpan.started_at.desc(), RuntimeSpan.id.desc())
            if execution_id is not None:
                query = query.filter(RuntimeSpan.execution_id == execution_id)
            rows = query.limit(limit).all()
            return [
                {
                    "id": row.id,
                    "execution_id": row.execution_id,
                    "trace_id": row.trace_id,
                    "span_id": row.span_id,
                    "parent_span_id": row.parent_span_id,
                    "name": row.name,
                    "stage": row.stage,
                    "status": row.status,
                    "started_at": row.started_at,
                    "finished_at": row.finished_at,
                    "duration_ms": row.duration_ms,
                    "attributes_json": row.attributes_json,
                }
                for row in rows
            ]

    def list_metrics(self, *, execution_id: str | None = None, limit: int = 300) -> list[dict[str, Any]]:
        with get_session(self.db_path) as session:
            query = session.query(RuntimeMetric).order_by(RuntimeMetric.observed_at.desc(), RuntimeMetric.id.desc())
            if execution_id is not None:
                query = query.filter(RuntimeMetric.execution_id == execution_id)
            rows = query.limit(limit).all()
            return [
                {
                    "id": row.id,
                    "execution_id": row.execution_id,
                    "name": row.name,
                    "value": row.value,
                    "metric_type": row.metric_type,
                    "labels_json": row.labels_json,
                    "metadata_json": row.metadata_json,
                    "observed_at": row.observed_at,
                }
                for row in rows
            ]

    def list_lineage(self, *, execution_id: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        with get_session(self.db_path) as session:
            query = session.query(RuntimeLineage).order_by(RuntimeLineage.created_at.desc(), RuntimeLineage.id.desc())
            if execution_id is not None:
                query = query.filter(RuntimeLineage.execution_id == execution_id)
            rows = query.limit(limit).all()
            return [
                {
                    "id": row.id,
                    "execution_id": row.execution_id,
                    "entity_type": row.entity_type,
                    "entity_id": row.entity_id,
                    "event_type": row.event_type,
                    "payload_json": row.payload_json,
                    "created_at": row.created_at,
                }
                for row in rows
            ]

    def list_snapshots(self, *, execution_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with get_session(self.db_path) as session:
            query = session.query(RuntimeSnapshot).order_by(RuntimeSnapshot.created_at.desc(), RuntimeSnapshot.id.desc())
            if execution_id is not None:
                query = query.filter(RuntimeSnapshot.execution_id == execution_id)
            rows = query.limit(limit).all()
            return [
                {
                    "id": row.id,
                    "execution_id": row.execution_id,
                    "snapshot_id": row.snapshot_id,
                    "snapshot_type": row.snapshot_type,
                    "payload_json": row.payload_json,
                    "metadata_json": row.metadata_json,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class ObservabilityTracer:
    """Trace helper coupled to the observability repository."""

    def __init__(self, repository: ObservabilityRepository) -> None:
        self.repository = repository
        self.tracer = DistributedTracer()

    def start_execution(
        self,
        *,
        flow_name: str,
        stage: str = "",
        context: dict[str, Any] | None = None,
        execution_id: str | None = None,
    ) -> str:
        return self.repository.start_execution(
            flow_name=flow_name,
            stage=stage,
            context=context,
            execution_id=execution_id,
        )

    def span(
        self,
        execution_id: str,
        name: str,
        *,
        stage: str = "",
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ):
        return self.tracer.span(
            name,
            trace_id=execution_id,
            parent_span_id=parent_span_id,
            attributes=attributes,
        )

    def finish_span(self, execution_id: str, span: TraceSpan, *, stage: str = "") -> dict[str, Any]:
        return self.repository.record_span(execution_id, span, stage=stage)

    def finish_execution(
        self,
        execution_id: str,
        *,
        status: str = "ok",
        stage: str = "",
        duration_ms: float | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.repository.finish_execution(
            execution_id,
            status=status,
            stage=stage,
            duration_ms=duration_ms,
            context=context,
        )

    def record_metric(self, execution_id: str, sample: MetricSample, *, stage: str = "") -> dict[str, Any]:
        return self.repository.record_metric(execution_id, sample, stage=stage)

    def record_lineage(
        self,
        execution_id: str,
        *,
        entity_type: str,
        entity_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.repository.record_lineage(
            execution_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            payload=payload,
        )

    def record_snapshot(
        self,
        execution_id: str,
        *,
        snapshot_type: str,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.repository.record_snapshot(
            execution_id,
            snapshot_type=snapshot_type,
            payload=payload,
            metadata=metadata,
        )
