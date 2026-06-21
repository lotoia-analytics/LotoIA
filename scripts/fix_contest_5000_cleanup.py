"""
Limpeza cirúrgica do banco — concurso fantasma 5000
Operações:
  1. Deletar concursos fantasma da lotofacil_official_history
  2. Deletar registro de imported_contests fantasma
  3. Corrigir target_contest dos jogos elegíveis → próximo concurso real
  4. Deletar jogos não elegíveis e sem valor (game_conference_eligible=false, null com status crítico)
  5. Corrigir context_json dos jogos elegíveis

Lei 001: toda operação é transacional — ou tudo passa ou nada é aplicado.
Requer DATABASE_URL / DATABASE_PUBLIC_URL / LOTOIA_DATABASE_URL no ambiente.
"""
from __future__ import annotations

import json
import os
import sys

import psycopg2

from lotoia.clients.conference_utils import PHANTOM_TARGET_CONTEST_NUMBERS, resolve_next_target_contest

PHANTOM_CONTESTS = sorted(PHANTOM_TARGET_CONTEST_NUMBERS | {3801, 3802, 3901, 3902, 4001})
PHANTOM_TARGET_LIST = sorted(PHANTOM_TARGET_CONTEST_NUMBERS)


def _database_url() -> str:
    for key in ("DATABASE_URL", "DATABASE_PUBLIC_URL", "LOTOIA_DATABASE_URL"):
        value = str(os.environ.get(key, "") or "").strip()
        if value and value != key:
            return value
    raise SystemExit(
        "DATABASE_URL (ou DATABASE_PUBLIC_URL / LOTOIA_DATABASE_URL) é obrigatório — "
        "não use credenciais hardcoded."
    )


def cleanup() -> bool:
    next_real = resolve_next_target_contest()
    if next_real is None or next_real <= 0:
        raise SystemExit("Não foi possível resolver o próximo concurso real a partir do PostgreSQL.")

    conn = psycopg2.connect(_database_url())
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("=" * 70)
        print("LIMPEZA CIRÚRGICA — CONCURSOS FANTASMA")
        print(f"Próximo concurso alvo: {next_real}")
        print("=" * 70)

        cur.execute(
            "DELETE FROM lotofacil_official_history WHERE contest_number = ANY(%s)",
            (PHANTOM_CONTESTS,),
        )
        print(f"\n[1] Deletados {cur.rowcount} concursos fantasma de lotofacil_official_history")

        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='imported_contests' ORDER BY ordinal_position"
        )
        cols = [r[0] for r in cur.fetchall()]
        if "contest_number" in cols:
            cur.execute(
                "DELETE FROM imported_contests WHERE contest_number = ANY(%s)",
                (PHANTOM_CONTESTS,),
            )
            print(f"[2] Deletados {cur.rowcount} registros de imported_contests")
        else:
            print("[2] imported_contests não tem coluna contest_number — pulando")

        cur.execute(
            """
            SELECT id,
                   context_json->>'game_conference_eligible' as eligible,
                   context_json->>'game_quality_status' as quality
            FROM generated_games
            WHERE target_contest = ANY(%s)
            """,
            (PHANTOM_TARGET_LIST,),
        )
        rows = cur.fetchall()

        eligible_ids: list[int] = []
        delete_ids: list[int] = []
        for row_id, eligible, quality in rows:
            if eligible == "true":
                eligible_ids.append(row_id)
            elif eligible == "false" and quality == "critical":
                delete_ids.append(row_id)
            else:
                eligible_ids.append(row_id)

        print(f"\n[3] Jogos target fantasma:")
        print(f"    Elegíveis para recuperação: {len(eligible_ids)}")
        print(f"    Para deletar (não elegíveis + críticos): {len(delete_ids)}")

        if delete_ids:
            cur.execute("DELETE FROM generated_games WHERE id = ANY(%s)", (delete_ids,))
            print(f"[4] Deletados {cur.rowcount} jogos não elegíveis")
        else:
            print("[4] Nenhum jogo para deletar")

        if eligible_ids:
            cur.execute(
                "UPDATE generated_games SET target_contest = %s WHERE id = ANY(%s)",
                (next_real, eligible_ids),
            )
            print(f"[5] Atualizados {cur.rowcount} jogos: target fantasma → {next_real}")
        else:
            print("[5] Nenhum jogo elegível para atualizar")

        if eligible_ids:
            cur.execute(
                "SELECT id, context_json FROM generated_games WHERE id = ANY(%s)",
                (eligible_ids,),
            )
            fixed_count = 0
            for game_id, ctx in cur.fetchall():
                if not ctx:
                    continue
                if ctx.get("parent_lot_verdict") == "REPROVADO":
                    ctx["parent_lot_verdict"] = "PENDENTE_REVISAO"
                if ctx.get("parent_lot_status") == "pending_structural_review":
                    ctx["parent_lot_status"] = "recovered_from_phantom_contest"
                ctx["phantom_contest_fix_applied"] = True
                ctx["original_target_contest"] = PHANTOM_TARGET_LIST[0]
                ctx["corrected_target_contest"] = next_real
                cur.execute(
                    "UPDATE generated_games SET context_json = %s WHERE id = %s",
                    (json.dumps(ctx), game_id),
                )
                fixed_count += 1
            print(f"[6] Corrigidos context_json de {fixed_count} jogos")

        cur.execute(
            """
            SELECT id, context_json FROM generation_events
            WHERE id IN (
                SELECT DISTINCT generation_event_id FROM generated_games
                WHERE target_contest = %s
            )
            """,
            (next_real,),
        )
        evt_fixed = 0
        for evt_id, ctx in cur.fetchall():
            if not ctx:
                continue
            if isinstance(ctx, str):
                ctx = json.loads(ctx)
            ctx["phantom_contest_fix_applied"] = True
            ctx["original_target_contest"] = PHANTOM_TARGET_LIST[0]
            ctx["corrected_target_contest"] = next_real
            cur.execute(
                "UPDATE generation_events SET context_json = %s WHERE id = %s",
                (json.dumps(ctx), evt_id),
            )
            evt_fixed += 1
        print(f"[7] Corrigidos context_json de {evt_fixed} generation_events")

        cur.execute(
            "SELECT COUNT(*) FROM generated_games WHERE target_contest = ANY(%s)",
            (PHANTOM_TARGET_LIST,),
        )
        remaining_phantom_targets = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM generated_games WHERE target_contest = %s",
            (next_real,),
        )
        total_next_real = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM lotofacil_official_history WHERE contest_number = ANY(%s)",
            (PHANTOM_CONTESTS,),
        )
        remaining_phantom = cur.fetchone()[0]

        print(f"\n[8] Estado final:")
        print(f"    jogos target fantasma restantes: {remaining_phantom_targets} (deve ser 0)")
        print(f"    jogos target={next_real}: {total_next_real}")
        print(f"    concursos fantasma restantes: {remaining_phantom} (deve ser 0)")

        if remaining_phantom_targets > 0 or remaining_phantom > 0:
            conn.rollback()
            print("\n❌ ROLLBACK — estado inconsistente detectado")
            return False

        conn.commit()
        print("\n✅ COMMIT — limpeza aplicada com sucesso")
        return True

    except Exception as exc:
        conn.rollback()
        print(f"\n❌ ROLLBACK — erro: {exc}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    cleanup()
