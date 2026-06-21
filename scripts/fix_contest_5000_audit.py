"""
Auditoria completa do banco — concurso fantasma 5000
Mapeia todos os dados corrompidos antes da limpeza cirúrgica.

Requer DATABASE_URL / DATABASE_PUBLIC_URL / LOTOIA_DATABASE_URL no ambiente.
"""
from __future__ import annotations

import json
import os
import sys

import psycopg2

from lotoia.clients.conference_utils import PHANTOM_TARGET_CONTEST_NUMBERS, resolve_next_target_contest

PHANTOM_CONTESTS = sorted(PHANTOM_TARGET_CONTEST_NUMBERS | {3801, 3802, 3901, 3902, 4001})


def _database_url() -> str:
    for key in ("DATABASE_URL", "DATABASE_PUBLIC_URL", "LOTOIA_DATABASE_URL"):
        value = str(os.environ.get(key, "") or "").strip()
        if value and value != key:
            return value
    raise SystemExit(
        "DATABASE_URL (ou DATABASE_PUBLIC_URL / LOTOIA_DATABASE_URL) é obrigatório — "
        "não use credenciais hardcoded."
    )


def audit() -> None:
    conn = psycopg2.connect(_database_url())
    cur = conn.cursor()

    print("=" * 70)
    print("AUDITORIA — CONCURSO FANTASMA 5000")
    print("=" * 70)

    cur.execute(
        "SELECT contest_number, numbers, is_valid, created_at "
        "FROM lotofacil_official_history WHERE contest_number = ANY(%s) "
        "ORDER BY contest_number",
        (PHANTOM_CONTESTS,),
    )
    rows = cur.fetchall()
    print(f"\n[1] Concursos fantasma na lotofacil_official_history ({len(rows)} registros):")
    for r in rows:
        print(f"    contest={r[0]} | is_valid={r[2]} | nums={r[1]} | created={r[3]}")

    cur.execute("SELECT COUNT(*) FROM generated_games WHERE target_contest = ANY(%s)", (list(PHANTOM_TARGET_CONTEST_NUMBERS),))
    n_games = cur.fetchone()[0]
    print(f"\n[2] generated_games com target_contest fantasma: {n_games} jogos")

    cur.execute(
        "SELECT id, created_at, channel, strategy, analysis_batch_label "
        "FROM generation_events "
        "WHERE id IN (SELECT DISTINCT generation_event_id FROM generated_games WHERE target_contest = ANY(%s)) "
        "ORDER BY created_at DESC",
        (list(PHANTOM_TARGET_CONTEST_NUMBERS),),
    )
    rows = cur.fetchall()
    print(f"\n[3] generation_events ligados a target fantasma ({len(rows)} eventos):")
    for r in rows:
        print(f"    id={r[0]} | at={r[1]} | channel={r[2]} | strategy={r[3]} | label={r[4]}")

    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='imported_contests' ORDER BY ordinal_position"
    )
    cols = [r[0] for r in cur.fetchall()]
    if "contest_number" in cols:
        cur.execute("SELECT COUNT(*) FROM imported_contests WHERE contest_number = ANY(%s)", (PHANTOM_CONTESTS,))
        n_imported = cur.fetchone()[0]
        print(f"\n[4] imported_contests com contest_number fantasma: {n_imported} registros")
    else:
        print(f"\n[4] imported_contests colunas: {cols}")

    cur.execute(
        "SELECT COUNT(*) FROM check_events WHERE contest_id = ANY(%s)",
        (list(PHANTOM_TARGET_CONTEST_NUMBERS),),
    )
    n_checks = cur.fetchone()[0]
    print(f"\n[5] check_events com contest_id fantasma: {n_checks}")

    cur.execute(
        "SELECT MAX(contest_number) FROM lotofacil_official_history "
        "WHERE is_valid = 1"
    )
    max_real = cur.fetchone()[0]
    next_real = resolve_next_target_contest()
    print(f"\n[6] Último concurso real válido: {max_real}")
    print(f"    Próximo concurso alvo: {next_real}")

    cur.execute(
        "SELECT target_contest, COUNT(*) as n "
        "FROM generated_games "
        "GROUP BY target_contest "
        "ORDER BY target_contest DESC "
        "LIMIT 15"
    )
    rows = cur.fetchall()
    print(f"\n[7] Distribuição de target_contest em generated_games (top 15):")
    for r in rows:
        print(f"    target={r[0]} | jogos={r[1]}")

    cur.execute(
        "SELECT "
        "  SUM(CASE WHEN context_json->>'game_conference_eligible' = 'true' THEN 1 ELSE 0 END) as eligible, "
        "  SUM(CASE WHEN context_json->>'game_conference_eligible' = 'false' THEN 1 ELSE 0 END) as not_eligible, "
        "  SUM(CASE WHEN context_json->>'game_conference_eligible' IS NULL THEN 1 ELSE 0 END) as null_eligible "
        "FROM generated_games WHERE target_contest = ANY(%s)",
        (list(PHANTOM_TARGET_CONTEST_NUMBERS),),
    )
    r = cur.fetchone()
    print(f"\n[8] game_conference_eligible nos jogos target fantasma:")
    print(f"    eligible={r[0]} | not_eligible={r[1]} | null={r[2]}")

    cur.execute(
        "SELECT id, created_at, strategy, channel, analysis_batch_label, context_json "
        "FROM generation_events ORDER BY id DESC LIMIT 5"
    )
    print(f"\n[9] Últimos 5 generation_events:")
    for evt_id, created_at, strategy, channel, label, ctx in cur.fetchall():
        ctx_target = (ctx or {}).get("target_contest") if isinstance(ctx, dict) else None
        if isinstance(ctx, str):
            try:
                ctx_target = json.loads(ctx).get("target_contest")
            except json.JSONDecodeError:
                ctx_target = None
        print(
            f"    id={evt_id} | at={created_at} | strategy={strategy} | "
            f"channel={channel} | label={label} | ctx_target={ctx_target}"
        )

    conn.close()
    print("\n" + "=" * 70)
    print("AUDITORIA CONCLUÍDA")
    print("=" * 70)


if __name__ == "__main__":
    audit()
