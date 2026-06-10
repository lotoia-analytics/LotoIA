#!/usr/bin/env python3
"""Validação institucional de produção Railway (baseline LOTOIA_INSTITUTIONAL_BASELINE_2026_06_10).

Modos:
  --deploy-only   Verifica deploy GitHub/Railway e CI (não exige DATABASE_URL).
  (padrão)        Verifica deploy + conectividade PostgreSQL operacional.

Uso em produção (Railway shell ou ambiente com DATABASE_URL):
  python scripts/checks/railway_production_validation.py
  python scripts/checks/railway_production_validation.py --expected-sha f263197
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
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_TABLES = (
    "generation_events",
    "generated_games",
    "reconciliation_runs",
    "reconciliation_games",
    "imported_contests",
    "lotofacil_official_history",
)

INSTITUTIONAL_DATABASE_ENV_VARS = (
    "DATABASE_URL",
    "LOTOIA_DATABASE_URL",
    "STREAMLIT_DATABASE_URL",
    "LOTOIA_DATABASE_POOLER_URL",
    "STREAMLIT_DATABASE_POOLER_URL",
)


def _mask_database_url(database_url: str) -> str:
    text = str(database_url or "").strip()
    if not text:
        return "-"
    if "@" not in text:
        return text if len(text) <= 96 else f"{text[:48]}...{text[-24:]}"
    scheme, remainder = text.split("://", maxsplit=1) if "://" in text else ("", text)
    if "@" not in remainder:
        return text if len(text) <= 96 else f"{text[:48]}...{text[-24:]}"
    credentials, host_part = remainder.split("@", maxsplit=1)
    if ":" in credentials:
        username = credentials.split(":", maxsplit=1)[0]
        masked_credentials = f"{username}:***"
    else:
        masked_credentials = "***"
    prefix = f"{scheme}://" if scheme else ""
    return f"{prefix}{masked_credentials}@{host_part}"


def _run_gh_json(args: list[str]) -> Any | None:
    try:
        completed = subprocess.run(
            ["gh", *args],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None


def _validate_deploy(expected_sha: str | None) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    evidence: dict[str, Any] = {"checked_at": datetime.now(UTC).isoformat()}

    deployments = _run_gh_json(
        [
            "api",
            "repos/lotoia-analytics/lotoia/deployments",
            "--jq",
            '.[0:5] | map({id, sha, created_at, environment, description})',
        ]
    )
    if not deployments:
        warnings.append("gh CLI indisponível ou sem acesso — deploy GitHub não verificado")
        return errors, warnings, evidence

    evidence["recent_deployments"] = deployments
    production_deployments = [
        item
        for item in deployments
        if isinstance(item, dict) and "production" in str(item.get("environment", "")).lower()
    ]
    if not production_deployments:
        errors.append("nenhum deploy Railway em ambiente production encontrado")
        return errors, warnings, evidence

    latest = production_deployments[0]
    evidence["latest_production_deploy"] = latest
    deployment_id = latest.get("id")
    deploy_sha = str(latest.get("sha", ""))[:7]

    if expected_sha:
        expected_prefix = expected_sha[:7]
        if deploy_sha != expected_prefix:
            errors.append(
                f"deploy production SHA={deploy_sha} difere do esperado {expected_prefix}"
            )

    if deployment_id:
        status = _run_gh_json(
            [
                "api",
                f"repos/lotoia-analytics/lotoia/deployments/{deployment_id}/statuses",
                "--jq",
                ".[0] | {state, created_at, environment}",
            ]
        )
        evidence["latest_deploy_status"] = status
        if not status or str(status.get("state", "")).lower() != "success":
            errors.append("último deploy Railway production não está em state=success")

    ci_runs = _run_gh_json(
        [
            "run",
            "list",
            "--branch",
            "main",
            "--workflow",
            "governance-gate.yml",
            "--limit",
            "1",
            "--json",
            "conclusion,status,headSha,createdAt",
        ]
    )
    if isinstance(ci_runs, list) and ci_runs:
        evidence["latest_governance_gate"] = ci_runs[0]
        if str(ci_runs[0].get("conclusion", "")).lower() != "success":
            errors.append("governance-gate em main não concluiu com success")
    else:
        warnings.append("governance-gate em main não verificado via gh")

    return errors, warnings, evidence


def _resolve_database_env() -> tuple[str, str]:
    for env_name in INSTITUTIONAL_DATABASE_ENV_VARS:
        value = os.getenv(env_name, "").strip()
        if value:
            return value, env_name
    return "", ""


def _validate_database() -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    evidence: dict[str, Any] = {}

    database_url, database_source = _resolve_database_env()
    if not database_url:
        errors.append(
            "DATABASE_URL (ou variante institucional) ausente — backend cai em sqlite local"
        )
        return errors, warnings, evidence

    evidence["database_source"] = database_source
    evidence["database_url_masked"] = _mask_database_url(database_url)

    parsed = urlparse(database_url)
    scheme = (parsed.scheme or "").lower()
    if not (scheme.startswith("postgres") or scheme == "postgresql"):
        errors.append(f"backend esperado postgresql, obtido scheme={scheme or 'unknown'}")
        return errors, warnings, evidence

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text

    from dashboard import institutional_app as admin_app
    from lotoia.database.adapter import InstitutionalDatabaseAdapter
    from lotoia.database.database import DEFAULT_DATABASE_PATH, get_engine

    adapter = InstitutionalDatabaseAdapter(DEFAULT_DATABASE_PATH)
    if adapter.backend != "postgresql":
        errors.append(f"InstitutionalDatabaseAdapter.backend={adapter.backend} (esperado postgresql)")

    engine = get_engine(DEFAULT_DATABASE_PATH)
    evidence["engine_url_masked"] = _mask_database_url(str(engine.url))
    evidence["database_host"] = parsed.hostname or "-"

    table_counts: dict[str, int] = {}
    table_errors: dict[str, str] = {}
    for table in REQUIRED_TABLES:
        try:
            with engine.connect() as connection:
                value = connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
            table_counts[table] = int(value or 0)
        except Exception as exc:
            table_errors[table] = str(exc)
            errors.append(f"falha ao consultar tabela {table}: {exc}")

    evidence["table_counts"] = table_counts
    evidence["table_errors"] = table_errors

    official_count = table_counts.get("lotofacil_official_history", 0)
    if official_count <= 0:
        errors.append("lotofacil_official_history vazia — histórico oficial não persistido")

    latest_contest = admin_app.get_latest_official_contest()
    evidence["latest_official_contest"] = (
        {
            "contest_number": latest_contest.get("contest_number"),
            "source": latest_contest.get("official_contest_source"),
        }
        if isinstance(latest_contest, dict)
        else None
    )
    if not latest_contest or not str(latest_contest.get("contest_number", "")).isdigit():
        errors.append("_get_latest_contest / get_latest_official_contest sem concurso oficial no DB")

    snapshot = admin_app._database_snapshot()
    evidence["runtime_audit_backend"] = snapshot.get("backend")
    evidence["runtime_audit_errors"] = snapshot.get("errors") or {}
    if str(snapshot.get("backend", "")).lower() != "postgresql":
        errors.append(f"Auditoria Runtime backend={snapshot.get('backend')} (esperado postgresql)")
    if snapshot.get("errors"):
        errors.append(f"Auditoria Runtime reportou erros de tabela: {snapshot.get('errors')}")

    return errors, warnings, evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Validação Railway produção LotoIA")
    parser.add_argument(
        "--deploy-only",
        action="store_true",
        help="Valida apenas deploy GitHub/Railway e CI (sem DATABASE_URL).",
    )
    parser.add_argument(
        "--expected-sha",
        default="",
        help="SHA curto ou completo do commit baseline esperado em produção.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emite resultado estruturado em JSON.",
    )
    args = parser.parse_args()

    all_errors: list[str] = []
    all_warnings: list[str] = []
    report: dict[str, Any] = {
        "baseline_id": "LOTOIA_INSTITUTIONAL_BASELINE_2026_06_10",
        "validated_at": datetime.now(UTC).isoformat(),
        "mode": "deploy_only" if args.deploy_only else "full",
    }

    deploy_errors, deploy_warnings, deploy_evidence = _validate_deploy(
        expected_sha=args.expected_sha or None
    )
    all_errors.extend(deploy_errors)
    all_warnings.extend(deploy_warnings)
    report["deploy"] = deploy_evidence

    if not args.deploy_only:
        db_errors, db_warnings, db_evidence = _validate_database()
        all_errors.extend(db_errors)
        all_warnings.extend(db_warnings)
        report["database"] = db_evidence
    else:
        report["database"] = {"skipped": True, "reason": "--deploy-only"}

    report["errors"] = all_errors
    report["warnings"] = all_warnings
    report["status"] = "PASS" if not all_errors else "FAIL"

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"railway-production-validation: {report['status']}")
        for warning in all_warnings:
            print(f"  WARN: {warning}")
        for error in all_errors:
            print(f"  FAIL: {error}")
        if report["status"] == "PASS":
            latest = (report.get("deploy") or {}).get("latest_production_deploy") or {}
            sha = str(latest.get("sha", ""))[:7]
            if sha:
                print(f"  deploy production SHA: {sha}")
            if not args.deploy_only:
                db = report.get("database") or {}
                print(f"  backend: {db.get('runtime_audit_backend', '-')}")
                counts = db.get("table_counts") or {}
                if counts:
                    print(f"  lotofacil_official_history rows: {counts.get('lotofacil_official_history', 0)}")

    return 0 if not all_errors else 1


if __name__ == "__main__":
    sys.exit(main())
