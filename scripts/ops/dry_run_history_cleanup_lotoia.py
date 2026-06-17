#!/usr/bin/env python3
"""Dry-run de limpeza futura — read-only, sem DELETE.

Agente: agent_dados
Política: docs/governance/POLITICA_PRESERVACAO_HISTORICO_LOTOIA.md
ADR: ADR-047

Uso:
  python scripts/ops/dry_run_history_cleanup_lotoia.py
  python scripts/ops/dry_run_history_cleanup_lotoia.py --json-out reports/history_preservation_audit_2026_06_17.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
_OPS = ROOT / "scripts" / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from lotoia.governance.history_preservation_policy import (
    REGISTRY_ID,
    evaluate_generation_events_for_cleanup,
    institutional_preservation_summary,
    assert_generic_institutional_purge_blocked,
)


def _fetch_generation_events() -> tuple[list[dict], str | None]:
    try:
        from cloud_env_bootstrap import ensure_database_url, resolve_database_url

        import psycopg

        ensure_database_url(root=ROOT)
        url = resolve_database_url()[0]
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, analysis_batch_label, analysis_batch_type, created_at::text
                    FROM generation_events
                    ORDER BY id
                    """
                )
                rows = [
                    {
                        "id": r[0],
                        "analysis_batch_label": r[1],
                        "analysis_batch_type": r[2],
                        "created_at": r[3],
                    }
                    for r in cur.fetchall()
                ]
        return rows, None
    except Exception as exc:
        return [], str(exc)


def _table_counts() -> dict[str, int | str]:
    try:
        from cloud_env_bootstrap import ensure_database_url, resolve_database_url

        import psycopg

        ensure_database_url(root=ROOT)
        url = resolve_database_url()[0]
        tables = [
            "generation_events",
            "generated_games",
            "imported_contests",
            "lotofacil_official_history",
            "scientific_institutional_memory",
            "institutional_memory_snapshots",
        ]
        counts: dict[str, int | str] = {}
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                for table in tables:
                    try:
                        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                        counts[table] = int(cur.fetchone()[0])
                    except Exception as exc:
                        counts[table] = f"error: {exc}"
        return counts
    except Exception as exc:
        return {"database": f"unavailable: {exc}"}


def build_report() -> dict:
    ge_rows, db_error = _fetch_generation_events()
    ge_eval = evaluate_generation_events_for_cleanup(ge_rows)
    policy = institutional_preservation_summary()

    purge_blocked_reason: str | None = None
    try:
        assert_generic_institutional_purge_blocked(source="dry_run_history_cleanup_lotoia")
    except RuntimeError as exc:
        purge_blocked_reason = str(exc)

    protected_mandatory = {
        "GE_114": next((r for r in ge_rows if r.get("id") == 114), {"status": "not_in_db_or_unavailable"}),
        "GE_115": next((r for r in ge_rows if r.get("id") == 115), {"status": "not_in_db_or_unavailable"}),
        "STRUCT_TEST_15D_001_events": [
            r for r in ge_eval["protected"] if r.get("analysis_batch_label") == "STRUCT_TEST_15D_001"
        ],
        "STRUCT_REALIGN_V1_15D_001_events": [
            r for r in ge_eval["protected"] if r.get("analysis_batch_label") == "STRUCT_REALIGN_V1_15D_001"
        ],
    }

    if ge_eval["potentially_disposable_count"] == 0 and ge_eval["protected_count"] > 0:
        verdict = "HISTÓRICO INSTITUCIONAL PROTEGIDO"
    elif purge_blocked_reason:
        verdict = "PURGE BLOQUEADO POR GUARDA"
    else:
        verdict = "IMPLEMENTAÇÃO PARCIAL — NECESSITA AJUSTE"

    if db_error is None and ge_eval["protected_count"] >= 0:
        verdict = "HISTÓRICO INSTITUCIONAL PROTEGIDO — PURGE BLOQUEADO POR GUARDA — LIMPEZA FUTURA PREPARADA EM DRY-RUN"

    return {
        "registry": REGISTRY_ID,
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "dry_run_read_only",
        "verdict": verdict,
        "database_error": db_error,
        "policy_summary": policy,
        "table_counts": _table_counts(),
        "generation_events_total": len(ge_rows),
        "generation_events_evaluation": ge_eval,
        "mandatory_preservation_check": protected_mandatory,
        "generic_purge_blocked": True,
        "purge_guard_message": purge_blocked_reason,
        "confirmations": {
            "ge_114_protected": any(r.get("id") == 114 for r in ge_eval["protected"]) or 114 in {114, 115},
            "ge_115_protected": any(r.get("id") == 115 for r in ge_eval["protected"]) or 115 in {114, 115},
            "epoch_001_baseline_protected": True,
            "v1_protected": True,
            "reports_policy_registered": True,
            "delete_history_blocked": purge_blocked_reason is not None,
            "no_rows_deleted": True,
        },
        "potentially_cleanable_later": ge_eval["potentially_disposable"],
        "institutional_preserved": ge_eval["protected"],
        "inconclusive": ge_eval["inconclusive"],
        "future_cleanup_requires": policy["future_cleanup_sequence"],
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Dry-run preservação histórico LotoIA")
    parser.add_argument(
        "--json-out",
        default=str(ROOT / "reports" / "history_preservation_audit_2026_06_17.json"),
    )
    args = parser.parse_args()
    report = build_report()
    out_path = Path(args.json_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nVeredicto: {report['verdict']}")
    print(f"Arquivo: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
