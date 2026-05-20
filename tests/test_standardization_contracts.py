from __future__ import annotations

import json
from datetime import UTC, datetime

from lotoia.observability import LogLevel, StructuredLogger
from lotoia.standards import (
    ArtifactKind,
    EventCategory,
    Severity,
    artifact_name,
    institutional_timestamp,
    metadata_envelope,
    operational_event,
    report_payload,
)
from lotoia.storage import DistributedArtifactStore, OperationalSnapshotStore


def test_institutional_timestamp_and_artifact_names_are_canonical() -> None:
    moment = datetime(2026, 5, 20, 13, 45, 30, tzinfo=UTC)

    assert institutional_timestamp(moment) == "20260520T134530Z"
    assert artifact_name(ArtifactKind.REPORT, "Generation Report", "PDF", timestamp="20260520T134530Z") == (
        "lotoia_report_generation_report_20260520T134530Z.pdf"
    )


def test_operational_event_and_metadata_envelopes_are_complete() -> None:
    event = operational_event(
        category=EventCategory.GENERATION,
        event="generation completed",
        status="success",
        severity=Severity.INFO,
        context={"games": 2},
    )
    metadata = metadata_envelope(artifact_type=ArtifactKind.SNAPSHOT, name="generation")

    assert event["category"] == "generation"
    assert event["event"] == "generation_completed"
    assert event["severity"] == "info"
    assert event["occurred_at"].endswith("Z")
    assert metadata["institution"] == "LotoIA"
    assert metadata["timezone"] == "UTC"


def test_report_payload_preserves_type_and_adds_metadata() -> None:
    payload = report_payload(report_type="check", payload={"contest_id": 1234})

    assert payload["type"] == "check"
    assert payload["contest_id"] == 1234
    assert payload["metadata"]["artifact_type"] == "report"
    assert payload["metadata"]["positioning"].startswith("Statistical Structural Platform")


def test_structured_logger_exposes_standard_event() -> None:
    logger = StructuredLogger()
    event = logger.error(
        "sqlite failed",
        category=EventCategory.SQLITE,
        event="query_failed",
        metadata={"query": "SELECT 1"},
    )
    payload = event.to_dict()

    assert payload["severity"] == "error"
    assert payload["standard_event"]["category"] == "sqlite"
    assert payload["standard_event"]["event"] == "query_failed"


def test_operational_snapshot_store_wraps_payload_with_metadata(tmp_path) -> None:
    store = OperationalSnapshotStore(DistributedArtifactStore(tmp_path))
    snapshot = store.persist(snapshot_type="generation", payload={"games": 1})

    artifact_bytes = store.artifact_store.get_bytes(snapshot.artifact.artifact_id)
    content = json.loads(artifact_bytes.decode("utf-8"))

    assert snapshot.metadata["artifact_type"] == "snapshot"
    assert snapshot.artifact.logical_name.startswith("lotoia_snapshot_generation_")
    assert content["metadata"]["name"] == "generation"
    assert content["payload"]["games"] == 1
