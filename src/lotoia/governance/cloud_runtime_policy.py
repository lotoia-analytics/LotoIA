"""Cloud-only runtime policy for Railway production (Lei No 001)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from lotoia.database.adapter import InstitutionalDatabaseAdapter, is_operational_database_path
from lotoia.database.env_resolution import (
    COMPAT_DATABASE_PUBLIC_URL_ENV,
    database_url_resolution_issue,
    is_invalid_database_url_literal,
    promote_resolved_database_url_to_env,
    resolve_institutional_database_url_from_env,
)

_LOCALHOST_MARKERS = ("localhost", "127.0.0.1", "0.0.0.0", "::1")


@dataclass(frozen=True)
class CloudRuntimePolicyResult:
    cloud_runtime: bool
    auth_required: bool
    postgresql_required: bool
    database_source: str
    backend: str
    violations: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.violations


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def is_cloud_production_runtime() -> bool:
    if _truthy_env("LOTOIA_CLOUD_ONLY"):
        return True
    if os.getenv("APP_ENV", "").strip().lower() == "production":
        return True
    if os.getenv("RAILWAY_ENVIRONMENT", "").strip():
        return True
    if os.getenv("RAILWAY_PROJECT_ID", "").strip():
        return True
    if os.getenv("RAILWAY_SERVICE_ID", "").strip():
        return True
    if os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip():
        return True
    if os.getenv("RAILWAY_SERVICE_NAME", "").strip():
        return True
    return False


def is_auth_required() -> bool:
    if _truthy_env("LOTOIA_AUTH_REQUIRED"):
        return True
    if os.getenv("LOTOIA_AUTH_REQUIRED", "").strip().lower() in {"0", "false", "no", "off"}:
        return False
    return is_cloud_production_runtime()


def _is_localhost_database_url(database_url: str) -> bool:
    parsed = urlparse(database_url)
    host = (parsed.hostname or "").strip().lower()
    return any(marker in host for marker in _LOCALHOST_MARKERS)


def evaluate_cloud_runtime_policy(db_path: Path) -> CloudRuntimePolicyResult:
    cloud_runtime = is_cloud_production_runtime()
    auth_required = is_auth_required()
    postgresql_required = cloud_runtime or _truthy_env("LOTOIA_CLOUD_ONLY")
    violations: list[str] = []

    raw_database_url = os.getenv("DATABASE_URL", "").strip()
    env_url, env_source = resolve_institutional_database_url_from_env()

    if not env_url and is_operational_database_path(db_path):
        if raw_database_url and is_invalid_database_url_literal(raw_database_url):
            violations.append(
                database_url_resolution_issue(raw_database_url, source="DATABASE_URL")
                or "DATABASE_URL inválido"
            )
        else:
            violations.append("DATABASE_URL ausente — PostgreSQL obrigatório (Lei No 001)")
        return CloudRuntimePolicyResult(
            cloud_runtime=cloud_runtime,
            auth_required=auth_required,
            postgresql_required=postgresql_required,
            database_source="blocked",
            backend="blocked",
            violations=tuple(violations),
        )

    if raw_database_url and is_invalid_database_url_literal(raw_database_url) and cloud_runtime:
        if not env_url:
            violations.append(
                "DATABASE_URL contém valor literal inválido — configure "
                "${{Postgres.DATABASE_URL}} no Railway (M-PLAT-063)"
            )

    promote_resolved_database_url_to_env()
    adapter = InstitutionalDatabaseAdapter(db_path)
    if postgresql_required:
        issue = database_url_resolution_issue(env_url, source=env_source or "DATABASE_URL")
        if issue and env_source != COMPAT_DATABASE_PUBLIC_URL_ENV:
            violations.append(issue)
        elif _is_localhost_database_url(env_url):
            violations.append("DATABASE_URL aponta para localhost — proibido em runtime cloud")
        if adapter.backend != "postgresql":
            violations.append(f"backend={adapter.backend} — PostgreSQL obrigatório em runtime cloud")
        if adapter.database_source in {"sqlite_fallback", "sqlite_ephemeral"}:
            violations.append(f"fonte {adapter.database_source} detectada — Lei No 001 violada")
    elif is_operational_database_path(db_path) and adapter.backend != "postgresql":
        violations.append(
            f"backend={adapter.backend} em path operacional — PostgreSQL obrigatório (Lei No 001)"
        )

    return CloudRuntimePolicyResult(
        cloud_runtime=cloud_runtime,
        auth_required=auth_required,
        postgresql_required=postgresql_required,
        database_source=adapter.database_source,
        backend=adapter.backend,
        violations=tuple(violations),
    )


def enforce_cloud_runtime_policy(db_path: Path) -> CloudRuntimePolicyResult:
    result = evaluate_cloud_runtime_policy(db_path)
    if result.violations:
        joined = "; ".join(result.violations)
        raise RuntimeError(f"Cloud runtime policy violation: {joined}")
    return result


def cloud_runtime_policy_snapshot(db_path: Path) -> dict[str, Any]:
    result = evaluate_cloud_runtime_policy(db_path)
    return {
        "cloud_runtime": result.cloud_runtime,
        "auth_required": result.auth_required,
        "postgresql_required": result.postgresql_required,
        "database_source": result.database_source,
        "backend": result.backend,
        "violations": list(result.violations),
        "status": "PASS" if result.ok else "FAIL",
    }
