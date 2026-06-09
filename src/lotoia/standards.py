"""Institutional standardization contracts for LotoIA artifacts and events."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

INSTITUTIONAL_IDENTITY = "LotoIA"
INSTITUTIONAL_POSITIONING = "Statistical Structural Platform with Incremental Supervised Assistance"
STANDARD_VERSION = "standardization-v0.1.0"


class Severity(StrEnum):
    """Canonical severity vocabulary for operational records."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventCategory(StrEnum):
    """Canonical operational event categories."""

    GENERATION = "generation"
    CHECK = "check"
    EXPORT = "export"
    REPORT = "report"
    SNAPSHOT = "snapshot"
    ML = "ml"
    OBSERVABILITY = "observability"
    AUDIT = "audit"
    SQLITE = "sqlite"
    RUNTIME = "runtime"


class ArtifactKind(StrEnum):
    """Canonical institutional artifact families."""

    SNAPSHOT = "snapshot"
    REPORT = "report"
    ML_SNAPSHOT = "ml_snapshot"
    ML_REPORT = "ml_report"
    EXPORT = "export"


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


def institutional_timestamp(moment: datetime | None = None) -> str:
    """Return the canonical compact UTC timestamp used in artifact names."""

    value = moment or utc_now()
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def iso_timestamp(moment: datetime | None = None) -> str:
    """Return an ISO-8601 UTC timestamp with explicit Z suffix."""

    value = moment or utc_now()
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    """Normalize names for stable artifact identifiers."""

    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "artifact"


def artifact_name(kind: ArtifactKind | str, name: str, extension: str, *, timestamp: str | None = None) -> str:
    """Build a canonical artifact filename."""

    ext = extension.lstrip(".").lower()
    return f"lotoia_{str(kind)}_{slugify(name)}_{timestamp or institutional_timestamp()}.{ext}"


def artifact_path(root: Path, kind: ArtifactKind | str, name: str, extension: str) -> Path:
    """Return a canonical artifact path under the provided root."""

    return root / artifact_name(kind, name, extension)


def metadata_envelope(
    *,
    artifact_type: ArtifactKind | str,
    name: str,
    context: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build canonical metadata for reports, snapshots, exports, and ML artifacts."""

    return {
        "standard_version": STANDARD_VERSION,
        "institution": INSTITUTIONAL_IDENTITY,
        "positioning": INSTITUTIONAL_POSITIONING,
        "artifact_type": str(artifact_type),
        "name": slugify(name),
        "created_at": created_at or iso_timestamp(),
        "timezone": "UTC",
        "context": context or {},
    }


def report_payload(
    *,
    report_type: str,
    payload: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach institutional report metadata while preserving the original payload."""

    timestamp = iso_timestamp()
    return {
        "metadata": metadata_envelope(
            artifact_type=ArtifactKind.REPORT,
            name=report_type,
            context=context,
            created_at=timestamp,
        ),
        "timestamp": institutional_timestamp(),
        "type": report_type,
        **payload,
    }


def operational_event(
    *,
    category: EventCategory | str,
    event: str,
    status: str,
    severity: Severity | str = Severity.INFO,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a canonical operational event envelope."""

    return {
        "standard_version": STANDARD_VERSION,
        "occurred_at": iso_timestamp(),
        "severity": str(severity),
        "category": str(category),
        "event": slugify(event),
        "status": status,
        "context": context or {},
    }


def ml_governance_payload(
    *,
    payload: dict[str, Any],
    experiment_name: str,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach canonical ML governance metadata without changing model semantics."""

    metadata = metadata_envelope(
        artifact_type=ArtifactKind.ML_REPORT,
        name=experiment_name,
        context={
            "model_version": payload.get("model_version"),
            "feature_schema_version": payload.get("feature_schema_version"),
            "temporal_valid": payload.get("temporal_valid"),
        },
    )
    return {
        **payload,
        "metadata": metadata,
        "experiment_name": slugify(experiment_name),
        "metrics": metrics or payload.get("validation_metrics", {}),
        "naming_convention": "lotoia_ml_<experiment>_<YYYYMMDDTHHMMSSZ>.<ext>",
    }
