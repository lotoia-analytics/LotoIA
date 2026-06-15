#!/usr/bin/env python3
"""Health-check da cadeia WhatsApp (backend + Evolution config)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]


def _backend_base_url() -> str:
    for env_name in ("LOTOIA_WHATSAPP_BACKEND_URL", "PUBLIC_API_URL", "NEXT_PUBLIC_API_URL"):
        value = os.getenv(env_name, "").strip().rstrip("/")
        if value:
            return value
    return ""


def run_check(*, backend_url: str = "") -> dict[str, Any]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from lotoia.clients.evolution_client import EvolutionApiClient
    from lotoia.database.adapter import InstitutionalDatabaseAdapter
    from lotoia.database.database import DEFAULT_DATABASE_PATH

    errors: list[str] = []
    warnings: list[str] = []
    evidence: dict[str, Any] = {"checked_at": datetime.now(UTC).isoformat()}

    adapter = InstitutionalDatabaseAdapter(DEFAULT_DATABASE_PATH)
    evidence["database_backend"] = adapter.backend
    evidence["database_source"] = adapter.database_source
    if adapter.backend != "postgresql":
        errors.append("DATABASE_URL ausente ou SQLite — WhatsApp exige PostgreSQL (Lei No 001)")

    evolution = EvolutionApiClient()
    evidence["evolution"] = {
        "configured": evolution.is_configured,
        "base_url": evolution.base_url or None,
        "instance": evolution.instance or None,
        "api_key_present": bool(evolution.api_key),
    }
    if not evolution.is_configured:
        errors.append("Evolution API não configurada (EVOLUTION_API_URL, EVOLUTION_API_KEY, EVOLUTION_INSTANCE_NAME)")

    base = (backend_url or _backend_base_url()).strip().rstrip("/")
    evidence["backend_url"] = base or None
    if not base:
        warnings.append("URL do backend não informada — use --backend-url ou LOTOIA_WHATSAPP_BACKEND_URL")
    else:
        try:
            import urllib.request

            for path in ("/health", "/whatsapp/status"):
                url = f"{base}{path}"
                with urllib.request.urlopen(url, timeout=15) as response:
                    body = response.read().decode("utf-8", errors="replace")
                    payload = json.loads(body) if body.strip().startswith("{") else {"raw": body[:200]}
                evidence[path] = {"status_code": response.status, "body": payload}
                if path == "/health" and str(payload.get("status", "")).lower() != "ok":
                    errors.append(f"/health retornou status inesperado: {payload}")
        except Exception as exc:
            errors.append(f"backend inacessível em {base}: {exc}")

    webhook_url = f"{base}/whatsapp/webhook" if base else ""
    evidence["expected_webhook_url"] = webhook_url or None
    if webhook_url:
        parsed = urlparse(webhook_url)
        if parsed.hostname and "localhost" in (parsed.hostname or ""):
            errors.append("webhook aponta para localhost — Evolution não alcança")

    return {
        "checklist_id": "WHATSAPP_STACK_HEALTH",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "evidence": evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="WhatsApp stack health-check")
    parser.add_argument("--backend-url", default="", help="URL pública do backend FastAPI")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = run_check(backend_url=args.backend_url)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"whatsapp-stack-health: {report['status']}")
        for warning in report.get("warnings", []):
            print(f"  WARN: {warning}")
        for error in report.get("errors", []):
            print(f"  FAIL: {error}")
        evidence = report.get("evidence") or {}
        if evidence.get("expected_webhook_url"):
            print(f"  webhook: {evidence['expected_webhook_url']}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
