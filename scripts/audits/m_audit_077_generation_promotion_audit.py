#!/usr/bin/env python3
"""M-AUDIT-077 — Auditoria read-only GE 025→040 sem jogos válidos promovidos.

Uso:
  export DATABASE_URL="$DATABASE_PUBLIC_URL"
  python scripts/audits/m_audit_077_generation_promotion_audit.py
  python scripts/audits/m_audit_077_generation_promotion_audit.py --start 25 --end 40 --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MISSION_ID = "M-AUDIT-077"


def _postgres_configured() -> bool:
    from lotoia.database.env_resolution import is_postgresql_database_url, resolve_institutional_database_url_from_env

    url, _source = resolve_institutional_database_url_from_env()
    return bool(url) and is_postgresql_database_url(url)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M-AUDIT-077 — auditoria promoção GE 025→040")
    parser.add_argument("--start", type=int, default=25, help="Sequência operacional inicial (ex.: 25 → 025)")
    parser.add_argument("--end", type=int, default=40, help="Sequência operacional final (ex.: 40 → 040)")
    parser.add_argument("--json", action="store_true", help="Emitir JSON completo")
    parser.add_argument("--json-out", type=str, default="", help="Gravar JSON em arquivo")
    args = parser.parse_args(argv)

    if not _postgres_configured():
        payload = {
            "mission_id": MISSION_ID,
            "status": "SKIP",
            "reason": "PostgreSQL não configurado neste runtime (export DATABASE_URL / DATABASE_PUBLIC_URL)",
            "functional_changes": False,
            "purge_executed": False,
        }
        if args.json or args.json_out:
            text = json.dumps(payload, ensure_ascii=False, indent=2)
            if args.json_out:
                Path(args.json_out).write_text(text, encoding="utf-8")
            if args.json:
                print(text)
        else:
            print(f"{MISSION_ID}: SKIP — PostgreSQL não configurado")
        return 0

    from lotoia.audits.m_audit_077_generation_promotion import audit_operational_generation_range

    report = audit_operational_generation_range(
        operational_start=int(args.start),
        operational_end=int(args.end),
    )
    report["status"] = "OK"

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"=== {MISSION_ID} — Auditoria GE {args.start:03d}→{args.end:03d} ===")
    print(f"Lotes auditados: {report.get('lots_audited')} | GE ids: {report.get('target_generation_event_ids')}")
    summary = dict(report.get("summary") or {})
    print(
        f"Jogos no intervalo: {summary.get('total_games_in_range')} | "
        f"lotes elegíveis: {summary.get('lots_eligible_analytical_or_conference')} | "
        f"jogos aceitáveis: {summary.get('games_structurally_acceptable_in_range')}"
    )
    questions = dict(report.get("central_questions") or {})
    print()
    print("PERGUNTAS CENTRAIS:")
    for key in sorted(questions):
        print(f"  {key}: {questions[key]}")
    print()
    for lot in report.get("lots") or []:
        gc = dict(lot.get("game_classification") or {})
        seq = lot.get("operational_sequence")
        label = f"{int(seq):03d}" if seq else "—"
        print(
            f"GE {label} (id={lot.get('generation_event_id')}) | "
            f"jogos={lot.get('total_jogos_gerados')} únicos={lot.get('total_jogos_unicos')} | "
            f"sim={lot.get('similaridade_media'):.3f} max_ov={lot.get('sobreposicao_maxima')} "
            f"div={lot.get('score_diversidade'):.3f} | "
            f"veredito={lot.get('ml_verdict')} tier={lot.get('gp_quality_tier') or '—'} | "
            f"status={lot.get('lot_operational_status')} block={lot.get('promotion_block_reason') or '—'} | "
            f"aceit/aten/crit={gc.get('acceptable')}/{gc.get('attention')}/{gc.get('critical')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
