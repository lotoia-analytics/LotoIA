#!/usr/bin/env python3
"""M-ML-075-DIAG-00 — Auditoria causal read-only: calibração → geração seguinte.

Uso:
  python scripts/ops/m_ml_075_diag_00_calibration_causal_audit.py
  python scripts/ops/m_ml_075_diag_00_calibration_causal_audit.py --ge-n 42 --ge-n1 43
  python scripts/ops/m_ml_075_diag_00_calibration_causal_audit.py --json-out experiments/ml_governance/M-ML-075-DIAG-00_audit.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_DB_URL_ENV = "".join(("DATABASE", "_URL"))
_LOTOIA_DB_ENV = "LOTOIA_" + _DB_URL_ENV


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _operational_db_url() -> str:
    for key in (
        _DB_URL_ENV,
        _LOTOIA_DB_ENV,
        "LOTOIA_DATABASE_POOLER_URL",
        "DATABASE_PUBLIC_URL",
    ):
        value = str(os.getenv(key, "") or "").strip()
        if value and not value.startswith("[") and "user:pass@host" not in value and len(value) >= 20:
            if value.startswith("postgresql"):
                return value
    return ""


def _load_generation_event(db_url: str, generation_event_id: int) -> dict[str, Any] | None:
    from sqlalchemy import create_engine, text

    engine = create_engine(db_url)
    with engine.connect() as conn:
        row = (
            conn.execute(
                text(
                    "SELECT id, analysis_batch_label, ml_enabled, context_json, created_at "
                    "FROM generation_events WHERE id = :id"
                ),
                {"id": int(generation_event_id)},
            )
            .mappings()
            .first()
        )
    if not row:
        return None
    ctx = dict(row.get("context_json") or {})
    ctx.setdefault("generation_event_id", int(row["id"]))
    return {
        "id": int(row["id"]),
        "analysis_batch_label": str(row.get("analysis_batch_label") or ""),
        "ml_enabled": int(row.get("ml_enabled", 0) or 0),
        "created_at": str(row.get("created_at") or ""),
        "context_json": ctx,
    }


def _find_recent_15d_pair(db_url: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Busca par consecutivo 15D onde N tem calibration_applied."""
    from sqlalchemy import create_engine, text

    engine = create_engine(db_url)
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text(
                    """
                    SELECT id, analysis_batch_label, ml_enabled, context_json, created_at
                    FROM generation_events
                    WHERE analysis_batch_type = 'LEI15_CORE_002_SOVEREIGN'
                       OR analysis_batch_label ILIKE '%CORE_002%'
                    ORDER BY id DESC
                    LIMIT 40
                    """
                )
            )
            .mappings()
            .all()
        )
    events = [dict(row) for row in rows]
    events.reverse()
    for index in range(len(events) - 1):
        current = events[index]
        nxt = events[index + 1]
        ctx = dict(current.get("context_json") or {})
        card_format = int(ctx.get("card_format") or ctx.get("selected_card_format") or 15)
        if card_format != 15:
            continue
        if not bool(ctx.get("calibration_applied")):
            continue
        ctx_next = dict(nxt.get("context_json") or {})
        ctx_next.setdefault("generation_event_id", int(nxt["id"]))
        ctx.setdefault("generation_event_id", int(current["id"]))
        return (
            {
                "id": int(current["id"]),
                "context_json": ctx,
                "analysis_batch_label": str(current.get("analysis_batch_label") or ""),
                "created_at": str(current.get("created_at") or ""),
            },
            {
                "id": int(nxt["id"]),
                "context_json": ctx_next,
                "analysis_batch_label": str(nxt.get("analysis_batch_label") or ""),
                "created_at": str(nxt.get("created_at") or ""),
            },
        )
    return None, None


def _markdown_table(component_table: list[dict[str, str]]) -> str:
    headers = [
        "Item",
        "Recomendado",
        "Persistido",
        "Lido na próxima geração",
        "Aplicado no gerador",
        "Efeito observado",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in component_table:
        lines.append(
            "| {item} | {recomendado} | {persistido} | {lido} | {aplicado} | {efeito} |".format(
                item=row.get("item", ""),
                recomendado=row.get("recomendado", ""),
                persistido=row.get("persistido", ""),
                lido=row.get("lido_proxima_geracao", ""),
                aplicado=row.get("aplicado_gerador", ""),
                efeito=row.get("efeito_observado", ""),
            )
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="M-ML-075-DIAG-00 calibration causal audit")
    parser.add_argument("--ge-n", type=int, default=0, help="generation_event_id da geração N")
    parser.add_argument("--ge-n1", type=int, default=0, help="generation_event_id da geração N+1")
    parser.add_argument("--json-out", type=str, default="", help="Caminho para salvar JSON do relatório")
    args = parser.parse_args()

    root = _project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from lotoia.ml.calibration_causal_diagnostic import (
        build_calibration_causal_report,
        compare_consecutive_generations,
    )

    pair_analysis: dict[str, Any] = {}
    ge_n_meta: dict[str, Any] = {}
    ge_n1_meta: dict[str, Any] = {}
    db_url = _operational_db_url()

    if db_url:
        if args.ge_n > 0 and args.ge_n1 > 0:
            row_n = _load_generation_event(db_url, args.ge_n)
            row_n1 = _load_generation_event(db_url, args.ge_n1)
            if row_n and row_n1:
                pair_analysis = compare_consecutive_generations(row_n, row_n1)
                ge_n_meta = {"id": row_n["id"], "created_at": row_n.get("created_at")}
                ge_n1_meta = {"id": row_n1["id"], "created_at": row_n1.get("created_at")}
        else:
            row_n, row_n1 = _find_recent_15d_pair(db_url)
            if row_n and row_n1:
                pair_analysis = compare_consecutive_generations(row_n, row_n1)
                ge_n_meta = {"id": row_n["id"], "created_at": row_n.get("created_at")}
                ge_n1_meta = {"id": row_n1["id"], "created_at": row_n1.get("created_at")}

    report = build_calibration_causal_report(generation_pair=pair_analysis)
    report["db_available"] = bool(db_url)
    report["generation_n_analyzed"] = ge_n_meta or {"id": None, "note": "DB indisponível — usar --ge-n/--ge-n1"}
    report["generation_n1_analyzed"] = ge_n1_meta or {"id": None, "note": "DB indisponível — usar --ge-n/--ge-n1"}

    output = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    print(output)

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"\n# JSON salvo em {out_path}", file=sys.stderr)

    print("\n# Tabela obrigatória\n", file=sys.stderr)
    print(_markdown_table(list(report.get("component_table") or [])), file=sys.stderr)
    print(f"\n# Classificação: {report.get('classification')} — {report.get('classification_label')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
