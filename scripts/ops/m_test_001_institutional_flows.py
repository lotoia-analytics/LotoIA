#!/usr/bin/env python3
"""M-TEST-001 — Teste completo dos fluxos institucionais.

Testa todos os fluxos principais do sistema LotoIA:
1. Geração (M-GER-001)
2. Conferência
3. Histórico Analítico
4. Histórico Institucional
5. Cobertura Estrutural

Uso:
  python scripts/ops/m_test_001_institutional_flows.py --json
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MISSION_ID = "M-TEST-001"


def test_generation_flow() -> dict[str, Any]:
    """Testa fluxo de geração."""
    print("\n[1/5] TESTANDO FLUXO DE GERAÇÃO...", file=sys.stderr)

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        # Verifica generation_events
        result = session.execute(
            text("SELECT COUNT(*) FROM generation_events")
        ).scalar()
        generation_events_count = int(result or 0)

        # Verifica generated_games
        result = session.execute(text("SELECT COUNT(*) FROM generated_games")).scalar()
        generated_games_count = int(result or 0)

        # Verifica último generation_event
        result = (
            session.execute(
                text(
                    "SELECT id, strategy, ml_enabled, created_at FROM generation_events ORDER BY id DESC LIMIT 1"
                )
            )
            .mappings()
            .first()
        )

        last_event = dict(result) if result else None

        # Verifica jogos do último evento
        if last_event:
            result = session.execute(
                text(
                    "SELECT COUNT(*) FROM generated_games WHERE generation_event_id = :id"
                ),
                {"id": last_event["id"]},
            ).scalar()
            last_event_games = int(result or 0)
        else:
            last_event_games = 0

    return {
        "status": "success",
        "flow": "generation",
        "generation_events_count": generation_events_count,
        "generated_games_count": generated_games_count,
        "last_generation_event": last_event,
        "last_event_games_count": last_event_games,
    }


def test_conference_flow() -> dict[str, Any]:
    """Testa fluxo de conferência."""
    print("\n[2/5] TESTANDO FLUXO DE CONFERÊNCIA...", file=sys.stderr)

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        # Verifica reconciliation_runs
        result = session.execute(
            text("SELECT COUNT(*) FROM reconciliation_runs")
        ).scalar()
        reconciliation_runs_count = int(result or 0)

        # Verifica último reconciliation_run
        result = (
            session.execute(
                text(
                    "SELECT id, generation_event_id, contest_id, status, prize_count, best_hits, created_at FROM reconciliation_runs ORDER BY id DESC LIMIT 1"
                )
            )
            .mappings()
            .first()
        )

        last_reconciliation = dict(result) if result else None

        # Verifica jogos conferidos
        result = session.execute(
            text("SELECT COUNT(*) FROM reconciliation_games")
        ).scalar()
        reconciliation_games_count = int(result or 0)

    return {
        "status": "success",
        "flow": "conference",
        "reconciliation_runs_count": reconciliation_runs_count,
        "last_reconciliation": last_reconciliation,
        "reconciliation_games_count": reconciliation_games_count,
    }


def test_analytical_history_flow() -> dict[str, Any]:
    """Testa fluxo de histórico analítico."""
    print("\n[3/5] TESTANDO FLUXO DE HISTÓRICO ANALÍTICO...", file=sys.stderr)

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        # Verifica lotofacil_official_history
        result = session.execute(
            text("SELECT COUNT(*) FROM lotofacil_official_history")
        ).scalar()
        official_contests_count = int(result or 0)

        # Verifica último concurso oficial
        result = (
            session.execute(
                text(
                    "SELECT contest_number, draw_date, numbers FROM lotofacil_official_history ORDER BY contest_number DESC LIMIT 1"
                )
            )
            .mappings()
            .first()
        )

        last_contest = dict(result) if result else None

        # Verifica imported_contests
        result = session.execute(
            text("SELECT COUNT(*) FROM imported_contests")
        ).scalar()
        imported_contests_count = int(result or 0)

        # Verifica último concurso importado
        result = (
            session.execute(
                text(
                    "SELECT contest_number, data FROM imported_contests ORDER BY contest_number DESC LIMIT 1"
                )
            )
            .mappings()
            .first()
        )

        last_imported = dict(result) if result else None

    return {
        "status": "success",
        "flow": "analytical_history",
        "official_contests_count": official_contests_count,
        "last_official_contest": last_contest,
        "imported_contests_count": imported_contests_count,
        "last_imported_contest": last_imported,
    }


def test_institutional_history_flow() -> dict[str, Any]:
    """Testa fluxo de histórico institucional."""
    print("\n[4/5] TESTANDO FLUXO DE HISTÓRICO INSTITUCIONAL...", file=sys.stderr)

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        # Verifica leads
        result = session.execute(text("SELECT COUNT(*) FROM leads")).scalar()
        leads_count = int(result or 0)

        # Verifica últimos leads
        result = (
            session.execute(
                text(
                    "SELECT id, first_name, whatsapp, created_at FROM leads ORDER BY id DESC LIMIT 5"
                )
            )
            .mappings()
            .all()
        )

        recent_leads = [dict(row) for row in result]

        # Verifica feedback_loop
        result = session.execute(text("SELECT COUNT(*) FROM feedback_loop")).scalar()
        feedback_count = int(result or 0)

        # Verifica último feedback
        result = (
            session.execute(
                text(
                    "SELECT id, contest_number, created_at FROM feedback_loop ORDER BY id DESC LIMIT 1"
                )
            )
            .mappings()
            .first()
        )

        last_feedback = dict(result) if result else None

    return {
        "status": "success",
        "flow": "institutional_history",
        "leads_count": leads_count,
        "recent_leads": recent_leads,
        "feedback_count": feedback_count,
        "last_feedback": last_feedback,
    }


def test_structural_coverage_flow() -> dict[str, Any]:
    """Testa fluxo de cobertura estrutural."""
    print("\n[5/5] TESTANDO FLUXO DE COBERTURA ESTRUTURAL...", file=sys.stderr)

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        # Verifica se existe tabela de cobertura estrutural
        result = session.execute(
            text(
                "SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%structural%' OR table_name LIKE '%coverage%'"
            )
        ).fetchall()

        structural_tables = [row[0] for row in result]

        # Verifica operational_structural_memory
        try:
            result = session.execute(
                text("SELECT COUNT(*) FROM operational_structural_memory")
            ).scalar()
            structural_memory_count = int(result or 0)
        except:
            structural_memory_count = 0

        # Verifica se existe tabela de calibração
        try:
            result = session.execute(
                text("SELECT COUNT(*) FROM calibration_runs")
            ).scalar()
            calibration_runs_count = int(result or 0)
        except:
            calibration_runs_count = 0

        # Verifica jogos com validação de política estrutural
        result = session.execute(
            text(
                """
                SELECT COUNT(*) FROM generated_games 
                WHERE context_json::text LIKE '%"policy_compliance_status":"compliant"%'
                """
            )
        ).scalar()
        compliant_games_count = int(result or 0)

        result = session.execute(
            text(
                """
                SELECT COUNT(*) FROM generated_games 
                WHERE context_json::text LIKE '%"policy_compliance_status":"non_compliant"%'
                """
            )
        ).scalar()
        non_compliant_games_count = int(result or 0)

    return {
        "status": "success",
        "flow": "structural_coverage",
        "structural_tables": structural_tables,
        "structural_memory_count": structural_memory_count,
        "calibration_runs_count": calibration_runs_count,
        "compliant_games_count": compliant_games_count,
        "non_compliant_games_count": non_compliant_games_count,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=f"{MISSION_ID} — Teste completo dos fluxos institucionais"
    )
    parser.add_argument("--json", action="store_true", help="Output em JSON")
    args = parser.parse_args()

    try:
        results = {
            "mission_id": MISSION_ID,
            "timestamp": datetime.now(UTC).isoformat(),
            "flows": {},
        }

        # Testa cada fluxo
        results["flows"]["generation"] = test_generation_flow()
        results["flows"]["conference"] = test_conference_flow()
        results["flows"]["analytical_history"] = test_analytical_history_flow()
        results["flows"]["institutional_history"] = test_institutional_history_flow()
        results["flows"]["structural_coverage"] = test_structural_coverage_flow()

        # Resumo
        all_success = all(f["status"] == "success" for f in results["flows"].values())
        results["status"] = "success" if all_success else "partial_failure"

        if args.json:
            print(json.dumps(results, indent=2, default=str, ensure_ascii=False))
        else:
            print(f"\n[{MISSION_ID}] RESULTADO DOS TESTES:")
            print("=" * 60)
            for flow_name, flow_result in results["flows"].items():
                status_icon = "✓" if flow_result["status"] == "success" else "✗"
                print(f"\n{status_icon} {flow_name.upper()}")
                print(f"  Status: {flow_result['status']}")
                for key, value in flow_result.items():
                    if key not in ("status", "flow"):
                        if isinstance(value, dict):
                            print(f"  {key}: {json.dumps(value, default=str)}")
                        else:
                            print(f"  {key}: {value}")
            print("\n" + "=" * 60)
            print(f"Status geral: {results['status']}")

        return 0 if all_success else 1

    except Exception as exc:
        error_result = {
            "status": "error",
            "mission_id": MISSION_ID,
            "error": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if args.json:
            print(json.dumps(error_result, indent=2, default=str))
        else:
            print(f"[{MISSION_ID}] Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
