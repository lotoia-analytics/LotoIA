"""
Auditoria completa do banco — concurso fantasma 5000
Mapeia todos os dados corrompidos antes da limpeza cirúrgica.
"""
import psycopg2
import json

DB = "postgresql://postgres:gbkOvFoWDNlEWyywiqGtareFHpXALtzN@shortline.proxy.rlwy.net:32647/railway"


def audit():
    conn = psycopg2.connect(DB)
    cur = conn.cursor()

    print("=" * 70)
    print("AUDITORIA — CONCURSO FANTASMA 5000")
    print("=" * 70)

    # 1. Verificar concurso 5000 na tabela oficial
    cur.execute(
        "SELECT contest_number, numbers, is_valid, created_at "
        "FROM lotofacil_official_history WHERE contest_number IN (5000, 3801, 3802, 3901, 3902, 4001) "
        "ORDER BY contest_number"
    )
    rows = cur.fetchall()
    print(f"\n[1] Concursos fantasma na lotofacil_official_history ({len(rows)} registros):")
    for r in rows:
        print(f"    contest={r[0]} | is_valid={r[3]} | nums={r[1]} | created={r[2]}")

    # 2. Jogos gerados com target_contest=5000
    cur.execute("SELECT COUNT(*) FROM generated_games WHERE target_contest = 5000")
    n_games = cur.fetchone()[0]
    print(f"\n[2] generated_games com target_contest=5000: {n_games} jogos")

    # 3. Eventos de geração ligados ao target 5000
    cur.execute(
        "SELECT id, created_at, channel, strategy, analysis_batch_label "
        "FROM generation_events "
        "WHERE id IN (SELECT DISTINCT generation_event_id FROM generated_games WHERE target_contest = 5000) "
        "ORDER BY created_at DESC"
    )
    rows = cur.fetchall()
    print(f"\n[3] generation_events ligados a target=5000 ({len(rows)} eventos):")
    for r in rows:
        print(f"    id={r[0]} | at={r[1]} | channel={r[2]} | strategy={r[3]} | label={r[4]}")

    # 4. Verificar imported_contests
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='imported_contests' ORDER BY ordinal_position"
    )
    cols = [r[0] for r in cur.fetchall()]
    if 'contest_number' in cols:
        cur.execute("SELECT * FROM imported_contests WHERE contest_number = 5000")
        rows = cur.fetchall()
        print(f"\n[4] imported_contests com contest_number=5000: {len(rows)} registros")
    else:
        print(f"\n[4] imported_contests colunas: {cols}")
        cur.execute("SELECT COUNT(*) FROM imported_contests")
        print(f"    Total imported_contests: {cur.fetchone()[0]}")

    # 5. Verificar check_events ligados a contest 5000
    cur.execute("SELECT COUNT(*) FROM check_events WHERE contest_id = 5000")
    n_checks = cur.fetchone()[0]
    print(f"\n[5] check_events com contest_id=5000: {n_checks}")

    # 6. Próximo concurso real disponível
    cur.execute(
        "SELECT MAX(contest_number) FROM lotofacil_official_history "
        "WHERE is_valid = 1 AND contest_number < 5000"
    )
    max_real = cur.fetchone()[0]
    print(f"\n[6] Último concurso real válido: {max_real}")
    print(f"    Próximo concurso alvo: {max_real + 1}")

    # 7. Verificar se há jogos com outros target_contest inválidos
    cur.execute(
        "SELECT target_contest, COUNT(*) as n "
        "FROM generated_games "
        "GROUP BY target_contest "
        "ORDER BY target_contest DESC"
    )
    rows = cur.fetchall()
    print(f"\n[7] Distribuição de target_contest em generated_games:")
    for r in rows:
        print(f"    target={r[0]} | jogos={r[1]}")

    # 8. Verificar game_conference_eligible nos jogos
    cur.execute(
        "SELECT "
        "  SUM(CASE WHEN context_json->>'game_conference_eligible' = 'true' THEN 1 ELSE 0 END) as eligible, "
        "  SUM(CASE WHEN context_json->>'game_conference_eligible' = 'false' THEN 1 ELSE 0 END) as not_eligible, "
        "  SUM(CASE WHEN context_json->>'game_conference_eligible' IS NULL THEN 1 ELSE 0 END) as null_eligible "
        "FROM generated_games WHERE target_contest = 5000"
    )
    r = cur.fetchone()
    print(f"\n[8] game_conference_eligible nos jogos target=5000:")
    print(f"    eligible={r[0]} | not_eligible={r[1]} | null={r[2]}")

    # 9. Verificar se o painel de conferência usa target_contest ou generation_event_id
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='check_events' ORDER BY ordinal_position"
    )
    print(f"\n[9] check_events colunas: {[r[0] for r in cur.fetchall()]}")

    conn.close()
    print("\n" + "=" * 70)
    print("AUDITORIA CONCLUÍDA")
    print("=" * 70)


if __name__ == "__main__":
    audit()
