from __future__ import annotations

from datetime import UTC, datetime

from lotoia.database.database import (
    LotofacilOfficialHistory,
    ReconciliationGame,
    ReconciliationRun,
    create_database,
    get_session,
)
from lotoia.observability.card_structure_diagnostics import (
    EVIDENCE_LEVEL_LOCAL,
    EVIDENCE_LEVEL_STRUCTURAL_RECURRENT,
    load_card_structure_diagnostics_from_db,
    resolve_evidence_level,
)
from lotoia.statistics.card_structure import (
    analyze_stuck_games,
    compare_structure_profiles,
    compute_card_structure_metrics,
    compute_gaps,
    compute_gp_redundancy,
    compute_prefix,
    compute_suffix,
    format_dezena_group,
    resolve_cartao_final_from_game,
)

OFFICIAL_15 = [1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
CARD_13_HITS = [1, 2, 3, 4, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18]
CARD_14_HITS = [1, 2, 3, 4, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 19]


def test_calcula_prefixo_3_e_4() -> None:
    numbers = [4, 8, 12, 16, 20, 24, 1, 2, 3, 5, 6, 7, 9, 10, 11]
    assert format_dezena_group(compute_prefix(numbers, 3)) == "01-02-03"
    assert format_dezena_group(compute_prefix(numbers, 4)) == "01-02-03-04"


def test_calcula_sufixo_3_e_4() -> None:
    numbers = [4, 8, 12, 16, 20, 24, 1, 2, 3, 5, 6, 7, 9, 10, 11]
    assert format_dezena_group(compute_suffix(numbers, 3)) == "16-20-24"
    assert format_dezena_group(compute_suffix(numbers, 4)) == "12-16-20-24"


def test_calcula_gaps_e_sequencias() -> None:
    numbers = [1, 2, 3, 10, 15, 16, 17, 20, 21, 22, 23, 24, 25, 4, 5]
    metrics = compute_card_structure_metrics(numbers)
    assert compute_gaps(sorted(numbers)) == metrics["gaps_entre_dezenas"]
    assert metrics["maior_sequencia"] >= 3
    assert metrics["baixas_01_05"] >= 1
    assert metrics["pares"] + metrics["impares"] == 15


def test_calcula_faixas_baixas_medias_altas() -> None:
    metrics = compute_card_structure_metrics(OFFICIAL_15)
    assert metrics["baixas_01_05"] + metrics["medias_06_15"] + metrics["altas_16_25"] == 15


def test_calcula_dezenas_ausentes() -> None:
    metrics = compute_card_structure_metrics(OFFICIAL_15)
    assert len(metrics["dezenas_ausentes"]) == 10


def test_calcula_redundancia_gp() -> None:
    redundancy = compute_gp_redundancy([OFFICIAL_15, OFFICIAL_15, CARD_13_HITS])
    assert redundancy["sobreposicao_maxima"] == 15
    assert redundancy["cartoes_quase_repetidos"] >= 1


def test_compara_lotoia_vs_concursos_oficiais() -> None:
    comparison = compare_structure_profiles([CARD_13_HITS, CARD_14_HITS], [OFFICIAL_15, OFFICIAL_15])
    assert comparison["available"] is True
    assert comparison["estruturas_mais_geradas_pela_LotoIA"]
    assert comparison["estruturas_mais_frequentes_nos_concursos"]


def test_identifica_jogos_travados_em_13() -> None:
    stuck = analyze_stuck_games(
        [
            {
                "numbers": CARD_13_HITS,
                "hits": 13,
                "official_numbers": OFFICIAL_15,
                "game_index": 1,
            }
        ],
        official_numbers=OFFICIAL_15,
    )
    assert len(stuck["jogos_com_13_hits"]) == 1
    assert stuck["dezenas_faltantes_para_14"]


def test_identifica_dezenas_faltantes_para_14() -> None:
    stuck = analyze_stuck_games(
        [
            {
                "numbers": CARD_14_HITS,
                "hits": 14,
                "official_numbers": OFFICIAL_15,
                "game_index": 1,
            }
        ],
        official_numbers=OFFICIAL_15,
    )
    assert len(stuck["jogos_com_14_hits"]) == 1
    assert stuck["dezenas_faltantes_para_15"]


def test_resolve_cartao_final_from_game() -> None:
    assert resolve_cartao_final_from_game({"numbers": OFFICIAL_15}) == sorted(OFFICIAL_15)
    assert resolve_cartao_final_from_game({"cartao_final": "01 02 03"}) == [1, 2, 3]


def test_sem_efeito_operacional_payload_defaults() -> None:
    from lotoia.observability.card_structure_diagnostics import empty_card_structure_payload

    payload = empty_card_structure_payload()
    assert payload["operational_effect"] is False
    assert payload["generation_command"] is False
    assert payload["recalibration_command"] is False


def test_painel_mostra_base_do_diagnostico(tmp_path) -> None:
    db_path = tmp_path / "card_structure.db"
    create_database(db_path)
    with get_session(db_path) as session:
        session.add(
            LotofacilOfficialHistory(
                contest_number=3704,
                draw_date=datetime.now(UTC).date().isoformat(),
                numbers=" ".join(f"{number:02d}" for number in OFFICIAL_15),
                source="test",
            )
        )
        run = ReconciliationRun(
            generation_event_id=492,
            contest_id=3704,
            prize_count=0,
            total_hits=13,
            best_hits=13,
            created_at=datetime.now(UTC),
            payload={},
        )
        session.add(run)
        session.flush()
        session.add(
            ReconciliationGame(
                reconciliation_run_id=run.id,
                generation_event_id=492,
                contest_id=3704,
                game_index=1,
                numbers=CARD_13_HITS,
                hits=13,
                matched_numbers=sorted(set(CARD_13_HITS) & set(OFFICIAL_15)),
                prize_status="nao_premiado",
                prize_tier="",
                context_json={},
            )
        )
        session.commit()

    payload = load_card_structure_diagnostics_from_db(db_path)
    assert payload["available"] is True
    evidence = payload["evidence_base"]
    assert evidence["concursos_analisados"] == [3704]
    assert evidence["generation_event_ids"] == [492]
    assert evidence["reconciliation_run_ids"]
    assert payload["abertura"]["prefixo_3_mais_gerado"]
    assert payload["travamento_13_14"]["jogos_com_13_hits"]
    assert payload["redundancia_gp"]["sobreposicao_maxima"] == 0


def test_evidence_level_local_vs_structural_recurrent() -> None:
    assert resolve_evidence_level(total_geracoes=5, total_concursos=3) == EVIDENCE_LEVEL_LOCAL
    assert (
        resolve_evidence_level(total_geracoes=20, total_concursos=5)
        == EVIDENCE_LEVEL_STRUCTURAL_RECURRENT
    )


def test_payload_inclui_rankings_prefixo_sufixo_3_e_4() -> None:
    from lotoia.observability.card_structure_diagnostics import build_card_structure_payload

    payload = build_card_structure_payload(
        games=[{"numbers": CARD_13_HITS}, {"numbers": CARD_14_HITS}],
        official_cards=[OFFICIAL_15, OFFICIAL_15],
        official_contests=[3700, 3701],
        generation_event_ids=[1],
        reconciliation_run_ids=[10],
        contest_ids=[3700],
    )
    abertura = payload["abertura"]
    fechamento = payload["fechamento"]

    for key in (
        "lotoia_prefixo_3_ranking",
        "official_prefixo_3_ranking",
        "lotoia_prefixo_4_ranking",
        "official_prefixo_4_ranking",
    ):
        assert key in abertura
        assert isinstance(abertura[key], list)

    for key in (
        "lotoia_sufixo_3_ranking",
        "official_sufixo_3_ranking",
        "lotoia_sufixo_4_ranking",
        "official_sufixo_4_ranking",
    ):
        assert key in fechamento
        assert isinstance(fechamento[key], list)

    prefix4_top = abertura["prefixo_4_mais_gerado"]["estrutura"]
    assert any(row.get("estrutura") == prefix4_top for row in abertura["lotoia_prefixo_4_ranking"])
    suffix4_top = fechamento["sufixo_4_mais_gerado"]["estrutura"]
    assert any(row.get("estrutura") == suffix4_top for row in fechamento["lotoia_sufixo_4_ranking"])
    assert abertura["official_prefixo_4_ranking"]
    assert fechamento["official_sufixo_4_ranking"]
    assert payload["operational_effect"] is False
