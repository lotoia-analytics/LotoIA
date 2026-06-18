#!/usr/bin/env python3
"""Audit and repair Railway DATABASE_URL for mission M-PLAT-063.

Complements docs/governance/M_PLAT_063_DATABASE_URL_RAILWAY.md.
Never prints full connection strings.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lotoia.database.env_resolution import (  # noqa: E402
    COMPAT_DATABASE_PUBLIC_URL_ENV,
    audit_database_env_from_os,
    is_invalid_database_url_literal,
    is_placeholder_database_url,
    is_postgresql_database_url,
    mask_database_url,
    promote_resolved_database_url_to_env,
    resolve_institutional_database_url_from_env,
)

MISSION_ID = "M-PLAT-063"
RAILWAY_DATABASE_REFERENCE = "${{Postgres.DATABASE_PUBLIC_URL}}"
RAILWAY_INTERNAL_REFERENCE = "${{Postgres.DATABASE_URL}}"
SOVEREIGN_SOURCES = frozenset({"DATABASE_URL", "LOTOIA_DATABASE_URL", "STREAMLIT_DATABASE_URL"})


def _audit_local_environment() -> dict[str, Any]:
    audit = audit_database_env_from_os()
    resolved_url, resolved_source = resolve_institutional_database_url_from_env()
    warnings: list[str] = []
    if audit.get("compat_fallback_active"):
        warnings.append(
            f"{COMPAT_DATABASE_PUBLIC_URL_ENV} em uso — configure DATABASE_URL como variável soberana"
        )
    return {
        "mission_id": MISSION_ID,
        "checked_at": datetime.now(UTC).isoformat(),
        "scope": "local_environment",
        **audit,
        "resolved_source": resolved_source or None,
        "resolved_url_masked": mask_database_url(resolved_url) if resolved_url else None,
        "warnings": warnings,
    }


def _railway_cli_available() -> bool:
    return shutil.which("railway") is not None


def _run_railway_json(args: list[str]) -> tuple[int, Any]:
    command = ["railway", *args, "--json"]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return completed.returncode, {
            "stderr": completed.stderr.strip(),
            "stdout": completed.stdout.strip(),
        }
    try:
        return 0, json.loads(completed.stdout or "null")
    except json.JSONDecodeError:
        return 0, completed.stdout.strip()


def _database_url_usable(value: str) -> bool:
    return bool(value) and not is_placeholder_database_url(value) and is_postgresql_database_url(value)


def _audit_railway_service_variables() -> dict[str, Any]:
    if not _railway_cli_available():
        return {"status": "SKIP", "reason": "Railway CLI indisponível"}
    if not os.getenv("RAILWAY_TOKEN", "").strip():
        return {
            "status": "SKIP",
            "reason": "RAILWAY_TOKEN ausente — autentique com `railway login` ou exporte RAILWAY_TOKEN",
        }

    returncode, payload = _run_railway_json(["variable", "list"])
    if returncode != 0:
        return {
            "status": "FAIL",
            "reason": "falha ao listar variáveis Railway",
            "details": payload,
        }

    variables: dict[str, str] = {}
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("key") or "").strip()
                value = str(item.get("value") or "").strip()
                if name:
                    variables[name] = value
    elif isinstance(payload, dict):
        variables = {str(k): str(v) for k, v in payload.items()}

    database_url = variables.get("DATABASE_URL", "")
    database_public_url = variables.get("DATABASE_PUBLIC_URL", "")
    misconfigured = [
        name
        for name, value in (
            ("DATABASE_URL", database_url),
            ("DATABASE_PUBLIC_URL", database_public_url),
        )
        if value
        and (
            is_invalid_database_url_literal(value)
            or is_placeholder_database_url(value)
            or not is_postgresql_database_url(value)
        )
    ]

    return {
        "status": "PASS" if _database_url_usable(database_url) else "FAIL",
        "database_url_present": bool(database_url),
        "database_url_usable": _database_url_usable(database_url),
        "database_url_masked": mask_database_url(database_url) if database_url else None,
        "database_public_url_present": bool(database_public_url),
        "database_public_url_usable": _database_url_usable(database_public_url),
        "misconfigured": misconfigured,
        "recommended_fix": RAILWAY_DATABASE_REFERENCE,
        "internal_reference": RAILWAY_INTERNAL_REFERENCE,
    }


def _repair_railway_database_url(*, use_internal_reference: bool) -> dict[str, Any]:
    if not _railway_cli_available():
        return {"status": "FAIL", "reason": "Railway CLI indisponível"}
    if not os.getenv("RAILWAY_TOKEN", "").strip():
        return {
            "status": "FAIL",
            "reason": "RAILWAY_TOKEN ausente — exporte o token do Railway antes de aplicar o fix",
        }

    target_value = RAILWAY_INTERNAL_REFERENCE if use_internal_reference else RAILWAY_DATABASE_REFERENCE
    completed = subprocess.run(
        [
            "railway",
            "variable",
            "set",
            f"DATABASE_URL={target_value}",
            "--skip-deploys",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return {
            "status": "FAIL",
            "reason": "falha ao atualizar DATABASE_URL no Railway",
            "stderr": completed.stderr.strip(),
            "stdout": completed.stdout.strip(),
        }

    return {
        "status": "PASS",
        "action": "DATABASE_URL atualizada via Railway CLI",
        "reference": target_value,
        "note": "Redeploy o serviço para aplicar a variável em runtime",
    }


def run_mission(
    *,
    apply_fix: bool = False,
    use_internal_reference: bool = False,
) -> dict[str, Any]:
    local_audit = _audit_local_environment()
    railway_audit = _audit_railway_service_variables()
    repair: dict[str, Any] | None = None

    if apply_fix:
        repair = _repair_railway_database_url(use_internal_reference=use_internal_reference)
        railway_audit = _audit_railway_service_variables()

    local_ok = (
        local_audit.get("status") == "PASS"
        and local_audit.get("sovereign_database_url_active")
    )
    railway_ok = railway_audit.get("status") == "PASS"
    repair_ok = repair is None or repair.get("status") == "PASS"

    overall = "PASS" if local_ok and (railway_ok or railway_audit.get("status") == "SKIP") and repair_ok else "FAIL"
    if local_audit.get("status") == "WARN":
        overall = "WARN"

    return {
        "mission_id": MISSION_ID,
        "validated_at": datetime.now(UTC).isoformat(),
        "status": overall,
        "local_audit": local_audit,
        "railway_audit": railway_audit,
        "repair": repair,
        "sovereign_var": "DATABASE_URL",
        "compat_var": COMPAT_DATABASE_PUBLIC_URL_ENV,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit/repair Railway DATABASE_URL (M-PLAT-063)")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument(
        "--apply-fix",
        action="store_true",
        help="Atualiza DATABASE_URL no Railway via CLI (requer RAILWAY_TOKEN)",
    )
    parser.add_argument(
        "--use-internal-reference",
        action="store_true",
        help="Usa ${{Postgres.DATABASE_URL}} em vez da URL pública",
    )
    parser.add_argument(
        "--promote-local",
        action="store_true",
        help="Promove URL resolvida para DATABASE_URL no ambiente local",
    )
    args = parser.parse_args()

    if args.promote_local:
        promote_resolved_database_url_to_env()

    report = run_mission(
        apply_fix=args.apply_fix,
        use_internal_reference=args.use_internal_reference,
    )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"{MISSION_ID}: {report['status']}")
        local = report["local_audit"]
        print(f"  local resolved_source: {local.get('resolved_source')}")
        print(f"  local status: {local.get('status')}")
        railway = report["railway_audit"]
        print(f"  railway status: {railway.get('status')}")
        if report.get("repair"):
            print(f"  repair status: {report['repair'].get('status')}")
        for warning in local.get("warnings", []):
            print(f"  WARN: {warning}")

    if report["status"] == "PASS":
        return 0
    if report["status"] == "WARN":
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
