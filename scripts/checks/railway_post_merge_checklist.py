#!/usr/bin/env python3
"""Checklist pós-merge Railway cloud-only (PR #98+).

Executa em sequência:
  1. Validação deploy GitHub/Railway + CI
  2. Health-check PostgreSQL cloud
  3. Validação Lei No 001 (zero leitura local)
  4. Validação Railway produção completa
  5. Migrations cloud (dry-run por padrão)
  6. Auditoria variáveis Railway obrigatórias

Uso no shell Railway (com DATABASE_URL):
  python scripts/checks/railway_post_merge_checklist.py

Uso local / CI (sem DATABASE_URL):
  python scripts/checks/railway_post_merge_checklist.py --deploy-only

Variáveis obrigatórias em produção:
  DATABASE_URL, LOTOIA_CLOUD_ONLY=1, LOTOIA_AUTH_REQUIRED=1,
  LOTOIA_ADMIN_EMAIL, LOTOIA_ADMIN_PASSWORD, APP_ENV=production
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_RAILWAY_VARS = (
    "DATABASE_URL",
    "LOTOIA_CLOUD_ONLY",
    "LOTOIA_AUTH_REQUIRED",
    "LOTOIA_ADMIN_EMAIL",
    "LOTOIA_ADMIN_PASSWORD",
    "APP_ENV",
)

RECOMMENDED_RAILWAY_VARS = (
    "EVOLUTION_API_URL",
    "EVOLUTION_API_KEY",
    "EVOLUTION_INSTANCE_NAME",
    "LOTOIA_BACKUP_RETENTION_DAYS",
)


def _run_step(name: str, command: list[str], *, env: dict[str, str] | None = None) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env or os.environ.copy(),
    )
    return {
        "name": name,
        "command": " ".join(command),
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "status": "PASS" if completed.returncode == 0 else "FAIL",
    }


def _audit_railway_variables() -> dict[str, Any]:
    present: dict[str, bool] = {}
    missing_required: list[str] = []
    missing_recommended: list[str] = []

    for var in REQUIRED_RAILWAY_VARS:
        value = os.getenv(var, "").strip()
        present[var] = bool(value)
        if not value:
            missing_required.append(var)

    for var in RECOMMENDED_RAILWAY_VARS:
        value = os.getenv(var, "").strip()
        present[var] = bool(value)
        if not value:
            missing_recommended.append(var)

    database_url = os.getenv("DATABASE_URL", "").strip()
    localhost_violation = any(
        marker in database_url.lower()
        for marker in ("localhost", "127.0.0.1", "0.0.0.0", "::1")
    ) if database_url else False

    return {
        "present": present,
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
        "localhost_violation": localhost_violation,
        "status": "PASS" if not missing_required and not localhost_violation else "FAIL",
    }


def run_checklist(
    *,
    deploy_only: bool = False,
    expected_sha: str = "",
    apply_migrations: bool = False,
) -> dict[str, Any]:
    python = sys.executable
    steps: list[dict[str, Any]] = []

    deploy_cmd = [python, "scripts/checks/railway_production_validation.py", "--deploy-only", "--json"]
    if expected_sha:
        deploy_cmd.extend(["--expected-sha", expected_sha])
    steps.append(_run_step("deploy_validation", deploy_cmd))

    var_audit = _audit_railway_variables()
    steps.append({"name": "railway_variables_audit", **var_audit})

    if not deploy_only:
        steps.append(
            _run_step(
                "postgresql_health_check",
                [python, "scripts/checks/postgresql_cloud_health_check.py", "--json"],
            )
        )
        steps.append(
            _run_step(
                "lei_001_validation",
                [python, "scripts/checks/lei_001_zero_local_read_validation.py", "--strict", "--json"],
            )
        )
        full_cmd = [python, "scripts/checks/railway_production_validation.py", "--json"]
        if expected_sha:
            full_cmd.extend(["--expected-sha", expected_sha])
        steps.append(_run_step("railway_full_validation", full_cmd))

        migration_cmd = [python, "scripts/ops/apply_cloud_migrations.py", "--json"]
        if not apply_migrations:
            migration_cmd.insert(-1, "--dry-run")
        steps.append(_run_step("cloud_migrations", migration_cmd))

    failed = [step for step in steps if step.get("status") == "FAIL"]
    return {
        "checklist_id": "RAILWAY_POST_MERGE_CLOUD_ONLY",
        "validated_at": datetime.now(UTC).isoformat(),
        "mode": "deploy_only" if deploy_only else "full",
        "expected_sha": expected_sha or None,
        "steps": steps,
        "status": "PASS" if not failed else "FAIL",
        "failed_steps": [step["name"] for step in failed],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Checklist pós-merge Railway cloud-only")
    parser.add_argument(
        "--deploy-only",
        action="store_true",
        help="Valida deploy/CI e variáveis sem exigir DATABASE_URL.",
    )
    parser.add_argument("--expected-sha", default="", help="SHA esperado em produção")
    parser.add_argument(
        "--apply-migrations",
        action="store_true",
        help="Aplica migrations (padrão: dry-run).",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args()

    report = run_checklist(
        deploy_only=args.deploy_only,
        expected_sha=args.expected_sha,
        apply_migrations=args.apply_migrations,
    )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"railway-post-merge-checklist: {report['status']}")
        for step in report["steps"]:
            name = step["name"]
            status = step.get("status", "?")
            print(f"  [{status}] {name}")
            if status == "FAIL":
                if step.get("missing_required"):
                    print(f"         missing: {', '.join(step['missing_required'])}")
                if step.get("stdout"):
                    print(f"         {step['stdout'][:200]}")
        if report.get("failed_steps"):
            print(f"  failed: {', '.join(report['failed_steps'])}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
