#!/usr/bin/env python3
"""Verifica se o painel Railway em produção reflete o build e commit esperados.

Usado pelo workflow `.github/workflows/railway-panel-deploy-gate.yml` após push
em `main` que altera `dashboard/` ou `railway.toml`.

Exemplo:
  python scripts/checks/railway_panel_deploy_sync_check.py \\
    --url https://lotoia-production.up.railway.app \\
    --expected-sha b5dd3ba \\
    --expected-build institutional-adm-runtime-v3 \\
    --max-wait-seconds 900
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _fetch_panel_body(url: str, *, timeout: int = 45) -> str:
    request = urllib.request.Request(
        url.rstrip("/") + "/",
        headers={
            "User-Agent": "LotoIA-Panel-Deploy-Sync/1.0",
            "Accept": "text/html,application/xhtml+xml",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _sha_prefixes(expected_sha: str) -> tuple[str, ...]:
    normalized = str(expected_sha or "").strip().lower()
    if not normalized:
        return ()
    prefixes: list[str] = []
    for size in (7, 12, len(normalized)):
        prefix = normalized[:size]
        if prefix and prefix not in prefixes:
            prefixes.append(prefix)
    return tuple(prefixes)


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles if needle)


def validate_panel_body(
    body: str,
    *,
    expected_build: str,
    expected_sha: str,
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    evidence: dict[str, Any] = {
        "expected_build": expected_build,
        "expected_sha": expected_sha,
        "body_length": len(body),
    }

    build = str(expected_build or "").strip()
    if not build:
        errors.append("expected_build ausente")
    elif build not in body:
        deprecated_hits = sorted(
            marker
            for marker in (
                "institutional-adm-runtime-v1",
                "institutional-adm-runtime-v2",
                "institutional-adm-runtime-v3",
            )
            if marker in body
        )
        if deprecated_hits:
            errors.append(
                f"painel ainda expõe build obsoleto {deprecated_hits[0]!r} (esperado {build!r})"
            )
        else:
            errors.append(f"BUILD_MARKER {build!r} não encontrado no HTML do painel")

    sha_prefixes = _sha_prefixes(expected_sha)
    evidence["sha_prefixes_checked"] = sha_prefixes
    login_page = "Acesso Institucional" in body
    if sha_prefixes and not _contains_any(body, sha_prefixes) and not login_page:
        errors.append(
            f"commit esperado ({sha_prefixes[0]}) não encontrado no HTML — deploy Railway ainda desatualizado"
        )

    stale_copy_markers = (
        "Painel mínimo, isolado",
        "Home institucional leve, sem geração",
        "bloqueada na home",
    )
    stale_hits = [marker for marker in stale_copy_markers if marker in body]
    evidence["stale_copy_hits"] = stale_hits
    if stale_hits:
        errors.append(f"copy obsoleta ainda visível: {stale_hits[0]!r}")

    if "Jogos Gerados" not in body and "Acesso Institucional" not in body:
        errors.append("painel não expõe home institucional completa nem tela de login")

    return errors, evidence


def run_sync_check(
    *,
    url: str,
    expected_build: str,
    expected_sha: str,
    max_wait_seconds: int,
    poll_interval_seconds: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + max(0, max_wait_seconds)
    attempt = 0
    last_errors: list[str] = []
    last_evidence: dict[str, Any] = {}

    while True:
        attempt += 1
        started_at = datetime.now(UTC).isoformat()
        try:
            body = _fetch_panel_body(url)
            errors, evidence = validate_panel_body(
                body,
                expected_build=expected_build,
                expected_sha=expected_sha,
            )
            last_errors = errors
            last_evidence = {
                **evidence,
                "attempt": attempt,
                "checked_at": started_at,
                "fetch_status": "ok",
            }
            if not errors:
                return {
                    "status": "PASS",
                    "attempts": attempt,
                    "url": url,
                    "evidence": last_evidence,
                }
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_errors = [f"falha ao buscar painel: {exc}"]
            last_evidence = {
                "attempt": attempt,
                "checked_at": started_at,
                "fetch_status": "error",
                "error": str(exc),
            }

        if time.monotonic() >= deadline:
            break
        time.sleep(max(5, poll_interval_seconds))

    return {
        "status": "FAIL",
        "attempts": attempt,
        "url": url,
        "errors": last_errors,
        "evidence": last_evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica sync deploy painel Railway")
    parser.add_argument("--url", default="", help="URL do painel (default: LOOTOIA_PANEL_URL ou produção)")
    parser.add_argument("--expected-sha", default="", help="SHA completo ou curto do commit em main")
    parser.add_argument("--expected-build", default="", help="BUILD_MARKER esperado")
    parser.add_argument("--max-wait-seconds", type=int, default=900)
    parser.add_argument("--poll-interval", type=int, default=30)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from dashboard.institutional_build import BUILD_MARKER, LOTOIA_PANEL_PRODUCTION_URL

    url = str(args.url or "").strip() or str(
        __import__("os").getenv("LOOTOIA_PANEL_URL", "") or LOTOIA_PANEL_PRODUCTION_URL
    ).strip()
    expected_build = str(args.expected_build or "").strip() or BUILD_MARKER
    expected_sha = str(args.expected_sha or "").strip() or str(
        __import__("os").getenv("GITHUB_SHA", "") or ""
    ).strip()

    if not url:
        print("railway-panel-deploy-sync: FAIL — --url ausente")
        return 1
    if not expected_sha:
        print("railway-panel-deploy-sync: FAIL — --expected-sha ausente")
        return 1

    report = run_sync_check(
        url=url,
        expected_build=expected_build,
        expected_sha=expected_sha,
        max_wait_seconds=args.max_wait_seconds,
        poll_interval_seconds=args.poll_interval,
    )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"railway-panel-deploy-sync: {report['status']}")
        if report["status"] == "PASS":
            print(f"  url={url}")
            print(f"  attempts={report.get('attempts')}")
            print(f"  build={expected_build}")
            print(f"  sha={expected_sha[:12]}")
        else:
            for error in report.get("errors") or []:
                print(f"  FAIL: {error}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
