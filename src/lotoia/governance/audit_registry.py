"""Architecture audit registry for institutional governance."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4


class DependencyGuardLike(Protocol):
    def audit_path(self, source_root: str | Path) -> tuple[Any, ...]:
        ...


class ContractRegistryLike(Protocol):
    def list(self) -> tuple[Any, ...]:
        ...


class _NoopDependencyGuard:
    def audit_path(self, source_root: str | Path) -> tuple[Any, ...]:
        return ()


class _EmptyContractRegistry:
    def list(self) -> tuple[Any, ...]:
        return ()


@dataclass(frozen=True, slots=True)
class ArchitectureAuditRecord:
    """One architecture audit run."""

    audit_id: str
    generated_at: str
    source_root: str
    contract_count: int
    violation_count: int
    violations: tuple[Any, ...]
    status: str


class AuditRegistry:
    """Run and retain architecture audits in memory for reporting/CI."""

    def __init__(
        self,
        *,
        dependency_guard: DependencyGuardLike | None = None,
        contract_registry: ContractRegistryLike | None = None,
    ) -> None:
        self.dependency_guard = dependency_guard or _NoopDependencyGuard()
        self.contract_registry = contract_registry or _EmptyContractRegistry()
        self._records: list[ArchitectureAuditRecord] = []

    def run(self, source_root: str | Path) -> ArchitectureAuditRecord:
        violations = self.dependency_guard.audit_path(source_root)
        record = ArchitectureAuditRecord(
            audit_id=str(uuid4()),
            generated_at=datetime.now(tz=UTC).isoformat(),
            source_root=str(source_root),
            contract_count=len(self.contract_registry.list()),
            violation_count=len(violations),
            violations=violations,
            status="passed" if not violations else "failed",
        )
        self._records.append(record)
        return record

    def list_records(self) -> tuple[ArchitectureAuditRecord, ...]:
        return tuple(self._records)

    def latest(self) -> ArchitectureAuditRecord | None:
        return self._records[-1] if self._records else None
