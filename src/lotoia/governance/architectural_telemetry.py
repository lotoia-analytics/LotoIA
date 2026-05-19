"""Architecture telemetry for structural evolution monitoring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .adr_registry import AdrRegistry
from .audit_registry import ArchitectureAuditRecord


@dataclass(frozen=True, slots=True)
class ArchitecturalTelemetrySnapshot:
    """Structural telemetry snapshot for governance dashboards."""

    module_count: int
    python_file_count: int
    adr_count: int
    accepted_adr_count: int
    audit_status: str
    violation_count: int
    violations_by_reason: dict[str, int]


class ArchitecturalTelemetry:
    """Build architecture telemetry from source tree, ADRs, and audits."""

    def __init__(self, adr_registry: AdrRegistry | None = None) -> None:
        self.adr_registry = adr_registry or AdrRegistry()

    def snapshot(
        self,
        *,
        source_root: str | Path,
        audit_record: ArchitectureAuditRecord | None = None,
    ) -> ArchitecturalTelemetrySnapshot:
        root = Path(source_root)
        files = tuple(root.rglob("*.py")) if root.exists() else ()
        modules = {
            ".".join(path.relative_to(root).with_suffix("").parts)
            for path in files
        }
        adr_records = self.adr_registry.list_records()
        violations = audit_record.violations if audit_record else ()
        return ArchitecturalTelemetrySnapshot(
            module_count=len(modules),
            python_file_count=len(files),
            adr_count=len(adr_records),
            accepted_adr_count=sum(
                1 for record in adr_records if record.status.lower() == "aceito"
            ),
            audit_status=audit_record.status if audit_record else "not_run",
            violation_count=len(violations),
            violations_by_reason=_violations_by_reason(violations),
        )


def _violations_by_reason(violations) -> dict[str, int]:
    counts: dict[str, int] = {}
    for violation in violations:
        counts[violation.reason] = counts.get(violation.reason, 0) + 1
    return counts
