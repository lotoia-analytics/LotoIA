#!/usr/bin/env python3
"""M-LEAD-001 — Gestão de leads dormentes e reativação.

Problema: 217 leads cadastrados, apenas 2 ativos (0.9%).
215 leads dormentes sem nenhuma geração.

Solução:
1. Identifica leads dormentes (sem generation_events)
2. Classifica por tempo de inatividade
3. Gera relatório de reativação
4. Opcionalmente marca leads como inactive ou remove

Uso:
  python scripts/ops/m_lead_001_dormant_cleanup.py --analyze --json
  python scripts/ops/m_lead_001_dormant_cleanup.py --report --json
  python scripts/ops/m_lead_001_dormant_cleanup.py --mark-inactive --days 90 --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MISSION_ID = "M-LEAD-001"


def _resolve_database_url() -> str:
    """Resolve PostgreSQL URL (Lei No 001)."""
    for key in (
        "DATABASE_URL",
        "LOTOIA_DATABASE_URL",
        "LOTOIA_DATABASE_POOLER_URL",
        "DATABASE_PUBLIC_URL",
    ):
        value = str(os.getenv(key, "") or "").strip()
        if (
            value
            and not value.startswith("[")
            and "user:pass@host" not in value
            and len(value) >= 20
        ):
            return value.replace("postgresql+psycopg://", "postgresql://").replace(
                "postgresql+psycopg2://", "postgresql://"
            )
    raise RuntimeError(
        f"[{MISSION_ID}] PostgreSQL não configurado. Defina DATABASE_URL."
    )


def analyze_leads() -> dict[str, Any]:
    """Analisa situação dos leads."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        # Total de leads
        total = session.execute(text("SELECT COUNT(*) FROM leads")).scalar()

        # Leads com gerações
        active = session.execute(
            text(
                """
                SELECT COUNT(DISTINCT lead_id) as active_leads
                FROM generation_events
                WHERE lead_id IS NOT NULL
                """
            )
        ).scalar()

        # Leads sem gerações (dormentes)
        dormant = total - active

        # Detalhes dos leads ativos
        active_details = (
            session.execute(
                text(
                    """
                SELECT 
                    l.id, l.first_name, l.whatsapp, l.created_at,
                    COUNT(ge.id) as gen_count,
                    MIN(ge.created_at) as first_gen,
                    MAX(ge.created_at) as last_gen
                FROM leads l
                JOIN generation_events ge ON ge.lead_id = l.id
                GROUP BY l.id, l.first_name, l.whatsapp, l.created_at
                ORDER BY gen_count DESC
                """
                )
            )
            .mappings()
            .all()
        )

        # Leads dormentes - amostra
        dormant_sample = (
            session.execute(
                text(
                    """
                SELECT 
                    l.id, l.first_name, l.whatsapp, l.created_at,
                    CURRENT_TIMESTAMP - l.created_at as age
                FROM leads l
                WHERE l.id NOT IN (
                    SELECT DISTINCT lead_id FROM generation_events WHERE lead_id IS NOT NULL
                )
                ORDER BY l.created_at DESC
                LIMIT 20
                """
                )
            )
            .mappings()
            .all()
        )

    return {
        "status": "success",
        "mission_id": MISSION_ID,
        "summary": {
            "total_leads": int(total),
            "active_leads": int(active),
            "dormant_leads": int(dormant),
            "active_rate": round(int(active) / max(1, int(total)) * 100, 2),
        },
        "active_details": [
            {
                "id": int(l["id"]),
                "name": l["first_name"],
                "whatsapp": l["whatsapp"],
                "created_at": str(l["created_at"]),
                "gen_count": int(l["gen_count"]),
                "first_gen": str(l["first_gen"]),
                "last_gen": str(l["last_gen"]),
            }
            for l in active_details
        ],
        "dormant_sample": [
            {
                "id": int(l["id"]),
                "name": l["first_name"],
                "whatsapp": l["whatsapp"],
                "created_at": str(l["created_at"]),
                "age_days": int(l["age"].days) if l["age"] else 0,
            }
            for l in dormant_sample
        ],
    }


def generate_reactivation_report() -> dict[str, Any]:
    """Gera relatório de reativação com recomendações."""
    analysis = analyze_leads()
    dormant_count = analysis["summary"]["dormant_leads"]

    recommendations = []

    if dormant_count > 100:
        recommendations.append(
            {
                "action": "cleanup_campaign",
                "priority": "high",
                "message": f"{dormant_count} leads dormentes. Considerar campanha de reativação ou limpeza.",
                "suggested_steps": [
                    "Enviar WhatsApp para leads com < 30 dias",
                    "Marcar como inactive leads com > 90 dias sem interação",
                    "Remover leads com whatsapp inválido",
                ],
            }
        )

    if analysis["summary"]["active_rate"] < 5:
        recommendations.append(
            {
                "action": "improve_onboarding",
                "priority": "high",
                "message": f"Taxa de ativação muito baixa ({analysis['summary']['active_rate']}%). Revisar fluxo de onboarding.",
            }
        )

    return {
        **analysis,
        "recommendations": recommendations,
    }


def mark_dormant_inactive(*, days_threshold: int = 90) -> dict[str, Any]:
    """Marca leads dormentes como inactive."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    cutoff_date = datetime.now(UTC) - timedelta(days=days_threshold)

    with get_session(DB_PATH) as session:
        # Busca leads dormentes antigos
        dormant = (
            session.execute(
                text(
                    """
                SELECT l.id
                FROM leads l
                WHERE l.id NOT IN (
                    SELECT DISTINCT lead_id FROM generation_events WHERE lead_id IS NOT NULL
                )
                AND l.created_at < :cutoff
                """
                ),
                {"cutoff": cutoff_date},
            )
            .scalars()
            .all()
        )

        if not dormant:
            return {
                "status": "skipped",
                "reason": "no_dormant_leads",
                "message": f"Nenhum lead dormente com > {days_threshold} dias encontrado.",
            }

        # Adiciona coluna status se não existir
        try:
            session.execute(
                text(
                    """
                ALTER TABLE leads ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active'
                """
                )
            )
        except:
            pass  # Coluna já existe

        # Marca como inactive
        session.execute(
            text(
                """
            UPDATE leads
            SET status = 'inactive'
            WHERE id = ANY(:ids)
            """
            ),
            {"ids": list(dormant)},
        )
        session.commit()

    return {
        "status": "success",
        "leads_marked_inactive": len(dormant),
        "days_threshold": days_threshold,
        "lead_ids": list(dormant),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"{MISSION_ID} — Gestão de leads dormentes e reativação"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analisa situação dos leads",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Gera relatório de reativação",
    )
    parser.add_argument(
        "--mark-inactive",
        action="store_true",
        help="Marca leads dormentes como inactive",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Threshold em dias para considerar dormente (default: 90)",
    )
    parser.add_argument("--json", action="store_true", help="Output em JSON")
    args = parser.parse_args()

    try:
        if args.analyze:
            result = analyze_leads()
        elif args.report:
            result = generate_reactivation_report()
        elif args.mark_inactive:
            result = mark_dormant_inactive(days_threshold=args.days)
        else:
            print(
                "Erro: especifique --analyze, --report ou --mark-inactive",
                file=sys.stderr,
            )
            return 1

        if args.json:
            print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
        else:
            if args.analyze or args.report:
                summary = result.get("summary", {})
                print(f"[{MISSION_ID}] Análise de Leads:")
                print(f"  Total: {summary.get('total_leads')}")
                print(f"  Ativos: {summary.get('active_leads')}")
                print(f"  Dormentes: {summary.get('dormant_leads')}")
                print(f"  Taxa ativação: {summary.get('active_rate')}%")
                print()
                print("  LEADS ATIVOS:")
                for l in result.get("active_details", []):
                    print(
                        f"    #{l['id']} {l['name']} | {l['gen_count']} gerações | última: {l['last_gen'][:10]}"
                    )
                print()
                print(f"  AMOSTRA DORMENTES ({len(result.get('dormant_sample', []))}):")
                for l in result.get("dormant_sample", []):
                    print(
                        f"    #{l['id']} {l['name']} | cadastrado: {l['created_at'][:10]} | {l['age_days']} dias"
                    )
                if args.report:
                    print()
                    print("  RECOMENDAÇÕES:")
                    for r in result.get("recommendations", []):
                        print(f"    [{r['priority'].upper()}] {r['message']}")
            elif args.mark_inactive:
                print(f"[{MISSION_ID}] Leads marcados inactive:")
                print(f"  Status: {result.get('status')}")
                print(f"  Leads marcados: {result.get('leads_marked_inactive')}")
                print(f"  Threshold: {result.get('days_threshold')} dias")

        return 0

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
