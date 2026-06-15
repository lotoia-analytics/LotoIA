#!/usr/bin/env python3
"""Validação Lei No 001: zero leitura local em runtime cloud."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN_LOCAL_SOURCES = (
    "sqlite_fallback",
)

FORBIDDEN_LOCALHOST_MARKERS = ("localhost", "127.0.0.1", "0.0.0.0", "::1")


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _is_cloud_runtime() -> bool:
    if _truthy_env("LOTOIA_CLOUD_ONLY"):
        return True
    if os.getenv("APP_ENV", "").strip().lower() == "production":
        return True
    if os.getenv("RAILWAY_ENVIRONMENT", "").strip():
        return True
    if os.getenv("RAILWAY_PROJECT_ID", "").strip():
        return True
    return False


def run_validation(*, strict: bool = False) -> dict[str, Any]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from lotoia.database.adapter import InstitutionalDatabaseAdapter
    from lotoia.governance.cloud_runtime_policy import evaluate_cloud_runtime_policy
    from lotoia.database.database import DEFAULT_DATABASE_PATH

    errors: list[str] = []
    warnings: list[str] = []
    evidence: dict[str, Any] = {
        "checked_at": datetime.now(UTC).isoformat(),
        "cloud_runtime_detected": _is_cloud_runtime(),
        "strict_mode": strict,
    }

    adapter = InstitutionalDatabaseAdapter(DEFAULT_DATABASE_PATH)
    evidence["adapter_backend"] = adapter.backend
    evidence["database_source"] = adapter.database_source
    evidence["database_host"] = adapter.database_host

    if adapter.database_source in FORBIDDEN_LOCAL_SOURCES:
        if strict or _is_cloud_runtime():
            errors.append(f"fonte proibida detectada: {adapter.database_source}")
        else:
            warnings.append(f"fonte local detectada: {adapter.database_source} (aceitável apenas em dev local)")

    if adapter.backend == "sqlite":
        if strict or _is_cloud_runtime():
            errors.append("backend sqlite detectado — Lei No 001 exige PostgreSQL em cloud")
        else:
            warnings.append("backend sqlite em ambiente não-cloud (aceitável para dev local)")

    host = (adapter.database_host or "").lower()
    if host and any(marker in host for marker in FORBIDDEN_LOCALHOST_MARKERS):
        errors.append(f"DATABASE_URL aponta para host local: {host}")

    policy = evaluate_cloud_runtime_policy(DEFAULT_DATABASE_PATH)
    evidence["cloud_policy"] = {
        "cloud_runtime": policy.cloud_runtime,
        "auth_required": policy.auth_required,
        "postgresql_required": policy.postgresql_required,
        "violations": list(policy.violations),
    }
    if policy.violations and (strict or policy.cloud_runtime):
        errors.extend(list(policy.violations))

    default_csv = ROOT / "data" / "raw" / "historico_lotofacil.csv"
    evidence["default_csv_exists"] = default_csv.exists()
    if (strict or _is_cloud_runtime()) and default_csv.exists():
        warnings.append(
            "CSV local presente no filesystem — aceitável apenas como backup/auditoria, não como fonte operacional"
        )

    return {
        "lei": "LEI_001_FONTE_UNICA_DA_VERDADE",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "evidence": evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validação Lei No 001 — zero leitura local")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Falha se SQLite ou violações forem detectadas mesmo fora de runtime cloud.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args()

    report = run_validation(strict=args.strict)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"lei-001-zero-local-read: {report['status']}")
        for warning in report.get("warnings", []):
            print(f"  WARN: {warning}")
        for error in report.get("errors", []):
            print(f"  FAIL: {error}")
        evidence = report.get("evidence") or {}
        print(f"  backend: {evidence.get('adapter_backend', '-')}")
        print(f"  database_source: {evidence.get('database_source', '-')}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
