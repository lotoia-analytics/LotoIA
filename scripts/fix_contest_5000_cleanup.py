"""
Limpeza cirúrgica do banco — concurso fantasma 5000
Operações:
  1. Deletar concursos fantasma da lotofacil_official_history (3801, 3802, 3901, 3902, 4001, 5000)
  2. Deletar registro de imported_contests com contest_number=5000
  3. Corrigir target_contest dos jogos elegíveis (game_conference_eligible=true) → 3717
  4. Deletar jogos não elegíveis e sem valor (game_conference_eligible=false, null com status crítico)
  5. Corrigir context_json dos jogos elegíveis: atualizar target_contest e limpar parent_lot_verdict

Lei 001: toda operação é transacional — ou tudo passa ou nada é aplicado.
"""
import psycopg2
import json

DB = "postgresql://postgres:gbkOvFoWDNlEWyywiqGtareFHpXALtzN@shortline.proxy.rlwy.net:32647/railway"
NEXT_REAL_CONTEST = 3717
PHANTOM_CONTESTS = [3801, 3802, 3901, 3902, 4001, 5000]


def cleanup():
    conn = psycopg2.connect(DB)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("=" * 70)
        print("LIMPEZA CIRÚRGICA — CONCURSOS FANTASMA")
        print("=" * 70)

        # ── 1. Deletar concursos fantasma da tabela oficial ──────────────────
        cur.execute(
            "DELETE FROM lotofacil_official_history "
            "WHERE contest_number = ANY(%s)",
            (PHANTOM_CONTESTS,)
        )
        deleted_official = cur.rowcount
        print(f"\n[1] Deletados {deleted_official} concursos fantasma de lotofacil_official_history")

        # ── 2. Deletar imported_contests fantasma ────────────────────────────
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='imported_contests' ORDER BY ordinal_position"
        )
        cols = [r[0] for r in cur.fetchall()]
        if 'contest_number' in cols:
            cur.execute(
                "DELETE FROM imported_contests WHERE contest_number = ANY(%s)",
                (PHANTOM_CONTESTS,)
            )
            deleted_imported = cur.rowcount
            print(f"[2] Deletados {deleted_imported} registros de imported_contests")
        else:
            print(f"[2] imported_contests não tem coluna contest_number — pulando")

        # ── 3. Identificar jogos elegíveis para recuperação ──────────────────
        # Elegíveis: game_conference_eligible=true OU null (sem veredicto explícito)
        # Não elegíveis: game_conference_eligible=false E game_quality_status='critical'
        cur.execute(
            """
            SELECT id,
                   context_json->>'game_conference_eligible' as eligible,
                   context_json->>'game_quality_status' as quality
            FROM generated_games
            WHERE target_contest = 5000
            """
        )
        rows = cur.fetchall()

        eligible_ids = []
        delete_ids = []
        for row_id, eligible, quality in rows:
            if eligible == 'true':
                eligible_ids.append(row_id)
            elif eligible == 'false' and quality == 'critical':
                delete_ids.append(row_id)
            else:
                # null eligible — recuperar (podem ser jogos antigos sem o campo)
                eligible_ids.append(row_id)

        print(f"\n[3] Jogos target=5000:")
        print(f"    Elegíveis para recuperação: {len(eligible_ids)}")
        print(f"    Para deletar (não elegíveis + críticos): {len(delete_ids)}")

        # ── 4. Deletar jogos não elegíveis ───────────────────────────────────
        if delete_ids:
            cur.execute(
                "DELETE FROM generated_games WHERE id = ANY(%s)",
                (delete_ids,)
            )
            print(f"[4] Deletados {cur.rowcount} jogos não elegíveis")
        else:
            print(f"[4] Nenhum jogo para deletar")

        # ── 5. Corrigir target_contest dos jogos elegíveis → 3717 ────────────
        if eligible_ids:
            cur.execute(
                "UPDATE generated_games SET target_contest = %s WHERE id = ANY(%s)",
                (NEXT_REAL_CONTEST, eligible_ids)
            )
            updated_target = cur.rowcount
            print(f"[5] Atualizados {updated_target} jogos: target_contest 5000 → {NEXT_REAL_CONTEST}")
        else:
            print(f"[5] Nenhum jogo elegível para atualizar")

        # ── 6. Corrigir context_json dos jogos elegíveis ─────────────────────
        # Remover parent_lot_verdict=REPROVADO e parent_lot_status=pending_structural_review
        # Atualizar target_contest no context_json
        if eligible_ids:
            cur.execute(
                "SELECT id, context_json FROM generated_games WHERE id = ANY(%s)",
                (eligible_ids,)
            )
            game_rows = cur.fetchall()
            fixed_count = 0
            for game_id, ctx in game_rows:
                if not ctx:
                    continue
                changed = False
                # Corrigir parent_lot_verdict
                if ctx.get('parent_lot_verdict') == 'REPROVADO':
                    ctx['parent_lot_verdict'] = 'PENDENTE_REVISAO'
                    changed = True
                if ctx.get('parent_lot_status') == 'pending_structural_review':
                    ctx['parent_lot_status'] = 'recovered_from_phantom_contest'
                    changed = True
                # Marcar como recuperado
                ctx['phantom_contest_fix_applied'] = True
                ctx['original_target_contest'] = 5000
                ctx['corrected_target_contest'] = NEXT_REAL_CONTEST
                changed = True

                if changed:
                    cur.execute(
                        "UPDATE generated_games SET context_json = %s WHERE id = %s",
                        (json.dumps(ctx), game_id)
                    )
                    fixed_count += 1

            print(f"[6] Corrigidos context_json de {fixed_count} jogos")

        # ── 7. Corrigir generation_events ligados ────────────────────────────
        # Os generation_events não têm target_contest diretamente, mas o context_json pode ter
        cur.execute(
            """
            SELECT id, context_json FROM generation_events
            WHERE id IN (
                SELECT DISTINCT generation_event_id FROM generated_games
                WHERE target_contest = %s
            )
            """,
            (NEXT_REAL_CONTEST,)
        )
        evt_rows = cur.fetchall()
        evt_fixed = 0
        for evt_id, ctx in evt_rows:
            if not ctx:
                continue
            if isinstance(ctx, str):
                ctx = json.loads(ctx)
            ctx['phantom_contest_fix_applied'] = True
            ctx['original_target_contest'] = 5000
            ctx['corrected_target_contest'] = NEXT_REAL_CONTEST
            cur.execute(
                "UPDATE generation_events SET context_json = %s WHERE id = %s",
                (json.dumps(ctx), evt_id)
            )
            evt_fixed += 1
        print(f"[7] Corrigidos context_json de {evt_fixed} generation_events")

        # ── 8. Verificar estado final ────────────────────────────────────────
        cur.execute("SELECT COUNT(*) FROM generated_games WHERE target_contest = 5000")
        remaining_5000 = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM generated_games WHERE target_contest = {NEXT_REAL_CONTEST}")
        total_3717 = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM lotofacil_official_history "
            "WHERE contest_number = ANY(%s)", (PHANTOM_CONTESTS,)
        )
        remaining_phantom = cur.fetchone()[0]

        print(f"\n[8] Estado final:")
        print(f"    jogos target=5000 restantes: {remaining_5000} (deve ser 0)")
        print(f"    jogos target={NEXT_REAL_CONTEST}: {total_3717}")
        print(f"    concursos fantasma restantes: {remaining_phantom} (deve ser 0)")

        if remaining_5000 > 0 or remaining_phantom > 0:
            conn.rollback()
            print("\n❌ ROLLBACK — estado inconsistente detectado")
            return False

        # ── COMMIT ───────────────────────────────────────────────────────────
        conn.commit()
        print("\n✅ COMMIT — limpeza aplicada com sucesso")
        return True

    except Exception as e:
        conn.rollback()
        print(f"\n❌ ROLLBACK — erro: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    cleanup()
