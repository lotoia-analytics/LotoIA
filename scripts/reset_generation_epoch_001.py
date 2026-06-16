"""
RESET_GENERATION_EPOCH_001
==========================
Reseta a camada operacional de gerações/conferências da LotoIA.

Preserva integralmente:
  - lotofacil_official_history
  - leads / usuários
  - configurações institucionais
  - ADRs / governança
  - leis / pesos / filtros

Apaga (em ordem de FK):
  expansion_events               -> generation_events.id
  institutional_validated_expansions -> generation_events.id
  lotoia_client_generations      -> generation_events.id
  ml_usage_events                -> generation_events.id
  reconciliation_events          -> generation_events.id
  report_events                  -> generation_events.id
  reconciliation_runs            (generation_event_id sem FK formal)
  generated_games                (generation_event_id sem FK formal)
  institutional_output_signatures(generation_event_id sem FK formal)
  generation_events              (tabela raiz)

Uso:
  # dry-run (padrão, sem apagar nada):
  python scripts/reset_generation_epoch_001.py

  # reset real:
  set RESET_CONFIRMATION=RESET_GENERATION_EPOCH_001
  python scripts/reset_generation_epoch_001.py --execute
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg

# ─── configuração ─────────────────────────────────────────────────────────────
CONFIRMATION_TOKEN = "RESET_GENERATION_EPOCH_001"

# Ordem de deleção (filhas antes da raiz)
DELETE_ORDER: list[str] = [
    "expansion_events",
    "institutional_validated_expansions",
    "lotoia_client_generations",
    "ml_usage_events",
    "reconciliation_events",
    "report_events",
    "reconciliation_runs",
    "generated_games",
    "institutional_output_signatures",
    "generation_events",
]

# Tabelas oficiais que NUNCA podem ser apagadas
PROTECTED_TABLES: set[str] = {
    "lotofacil_official_history",
    "leads",
    "users",
    "admin_users",
    "adr_registry",
    "governance_policies",
    "analysis_batch_definitions",
}

# Sequências a resetar após deleção (somente tabelas operacionais)
SEQUENCES_TO_RESET: list[str] = [
    "generation_events_id_seq",
    "generated_games_id_seq",
    "reconciliation_runs_id_seq",
    "institutional_output_signatures_id_seq",
    "expansion_events_id_seq",
    "institutional_validated_expansions_id_seq",
    "lotoia_client_generations_id_seq",
    "ml_usage_events_id_seq",
    "reconciliation_events_id_seq",
    "report_events_id_seq",
]

BACKUP_DIR = Path("data/backups")


def resolve_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        sys.exit("ABORT: DATABASE_URL não definido.")
    if "sqlite" in url.lower():
        sys.exit("ABORT: DATABASE_URL contém sqlite. Proibido.")
    return url.replace("postgresql+psycopg://", "postgresql://")


def count_table(cur: psycopg.Cursor, table: str) -> int:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table};")
        return int(cur.fetchone()[0])
    except Exception:
        return -1


def create_backup(url: str) -> Path:
    """Backup lógico JSON das tabelas operacionais."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    backup_path = BACKUP_DIR / f"pre_epoch_001_{ts}.json"

    backup: dict = {"created_at": ts, "tables": {}}
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            for table in DELETE_ORDER:
                try:
                    cur.execute(f"SELECT * FROM {table} LIMIT 50000;")
                    cols = [d[0] for d in cur.description]
                    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
                    backup["tables"][table] = {"columns": cols, "rows": len(rows), "data": rows}
                except Exception as ex:
                    backup["tables"][table] = {"error": str(ex)}
                    conn.rollback()

    # Serializar com suporte a datetime
    def default_serializer(obj):
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        return str(obj)

    backup_path.write_text(
        json.dumps(backup, indent=2, default=default_serializer, ensure_ascii=False),
        encoding="utf-8",
    )
    size_kb = backup_path.stat().st_size // 1024
    print(f"[E2] Backup criado: {backup_path}  ({size_kb} KB)")
    return backup_path


def print_inventory(label: str, cur: psycopg.Cursor) -> dict[str, int]:
    print(f"\n[{label}] Contagens:")
    counts: dict[str, int] = {}
    for table in DELETE_ORDER:
        n = count_table(cur, table)
        counts[table] = n
        tag = "rows" if n >= 0 else "TABELA NÃO EXISTE"
        print(f"  {table:<45} {n if n >= 0 else '':>8} {tag}")

    print(f"\n[{label}] Tabelas oficiais (PRESERVAR):")
    for t in ["lotofacil_official_history", "leads"]:
        n = count_table(cur, t)
        print(f"  {t:<45} {n:>8} rows (INTOCADO)")
    return counts


def execute_reset(url: str, dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "EXECUÇÃO REAL"
    print(f"\n{'='*60}")
    print(f"  RESET_GENERATION_EPOCH_001  [{mode}]")
    print(f"{'='*60}\n")

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            pre = print_inventory("E3-PRE", cur)

        if dry_run:
            print("\n[DRY-RUN] Nenhuma alteração foi feita. Use --execute para executar.")
            return

        # Reset real — tudo em transação
        with conn.transaction():
            with conn.cursor() as cur:
                deleted: dict[str, int] = {}
                for table in DELETE_ORDER:
                    n = pre.get(table, -1)
                    if n < 0:
                        print(f"  SKIP {table} (tabela não existe)")
                        continue
                    if n == 0:
                        print(f"  SKIP {table} (já vazia)")
                        deleted[table] = 0
                        continue
                    try:
                        cur.execute(f"DELETE FROM {table};")
                        deleted[table] = cur.rowcount
                        print(f"  DELETED {table}: {cur.rowcount} rows")
                    except Exception as ex:
                        print(f"  ERRO em {table}: {ex}")
                        raise  # força rollback

                # Reset sequências
                print("\n[E7] Resetando sequências:")
                for seq in SEQUENCES_TO_RESET:
                    try:
                        cur.execute(f"ALTER SEQUENCE IF EXISTS {seq} RESTART WITH 1;")
                        print(f"  RESET SEQ {seq}")
                    except Exception as ex:
                        print(f"  SKIP SEQ {seq}: {ex}")

        # Validação pós-reset (fora da transação)
        with conn.cursor() as cur:
            print_inventory("E8-POS", cur)

    print("\n[OK] RESET_GENERATION_EPOCH_001 concluído.")


def main() -> None:
    dry_run = "--execute" not in sys.argv

    if not dry_run:
        token = os.environ.get("RESET_CONFIRMATION", "").strip()
        if token != CONFIRMATION_TOKEN:
            sys.exit(
                f"ABORT: RESET_CONFIRMATION deve ser '{CONFIRMATION_TOKEN}'.\n"
                f"  set RESET_CONFIRMATION={CONFIRMATION_TOKEN}"
            )

    url = resolve_url()
    print(f"[E1] DATABASE_URL: {url[:60]}...")

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            print(f"[E1] {cur.fetchone()[0][:70]}")

    if dry_run:
        print("\n[E2] Backup pulado no dry-run.")
    else:
        create_backup(url)

    execute_reset(url, dry_run=dry_run)


if __name__ == "__main__":
    main()
