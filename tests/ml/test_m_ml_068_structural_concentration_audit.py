"""M-ML-068 — auditoria de concentração estrutural 17D."""

from __future__ import annotations

from lotoia.ml.structural_concentration_audit import (
    MISSION_ID,
    audit_17d_expansion,
    audit_base_diversity,
    audit_dezena_coverage,
    audit_prefix_suffix_concentration,
    audit_structural_concentration,
    classify_dezena_frequency,
    classify_structure_dominance,
    infer_root_cause,
)


def _card17(base: int) -> list[int]:
    return list(range(base, base + 17))


def test_detect_dominant_prefix() -> None:
    cards = [_card17(1)] * 12 + [_card17(2)] * 8
    report = audit_prefix_suffix_concentration(cards, total_games=20)
    dominant = dict(report.get("prefixo_mais_dominante") or {})
    assert dominant.get("frequencia") == 12
    assert dominant.get("level") == "critico"
    assert dominant.get("share_pct") == 60.0


def test_detect_dominant_suffix() -> None:
    cards = [sorted(list(range(1, 14)) + [23, 24, 25]) for _ in range(20)]
    report = audit_prefix_suffix_concentration(cards, total_games=20)
    dominant = dict(report.get("sufixo_mais_dominante") or {})
    assert dominant.get("estrutura") == "23-24-25"
    assert dominant.get("frequencia") == 20
    assert dominant.get("level") == "critico"


def test_dezena_frequency_17d() -> None:
    cards = [_card17(1) for _ in range(20)]
    coverage = audit_dezena_coverage(cards, game_size=17, total_games=20)
    assert coverage["media_esperada_por_dezena"] == 13.6
    assert len(coverage["tabela_dezenas"]) == 25
    assert coverage["subcobertura_count"] >= 5


def test_detect_severe_undercoverage() -> None:
    assert classify_dezena_frequency(5, expected=13.6) == "subcobertura_severa"
    assert classify_dezena_frequency(9, expected=13.6) == "subcobertura_moderada"
    assert classify_dezena_frequency(14, expected=13.6) == "aceitavel"
    assert classify_dezena_frequency(22, expected=13.6) == "excessiva_severa"


def test_detect_excessive_dezenas() -> None:
    cards = [_card17(1) for _ in range(20)]
    coverage = audit_dezena_coverage(cards, game_size=17, total_games=20)
    excessive = list(coverage.get("dezenas_excessivas") or [])
    assert any(row["frequencia"] == 20 for row in excessive)


def test_base_diversity_cluster() -> None:
    games = [
        {"core_numbers": list(range(1, 16)), "final_card_numbers": _card17(1)},
        {"core_numbers": list(range(1, 16)), "final_card_numbers": _card17(1)},
        {"core_numbers": list(range(1, 16)), "final_card_numbers": _card17(1)},
        {"core_numbers": list(range(1, 16)), "final_card_numbers": _card17(1)},
        {"core_numbers": list(range(1, 16)), "final_card_numbers": _card17(1)},
        {"core_numbers": list(range(2, 17)), "final_card_numbers": _card17(2)},
    ]
    report = audit_base_diversity(games, total_games=6)
    assert report["bases_unicas"] == 2
    assert report["base_excede_20pct"] is True


def test_17d_expansion_audit() -> None:
    core = list(range(1, 16))
    games = [
        {
            "core_numbers": core,
            "audited_reserve_numbers": [16, 17],
            "final_card_numbers": core + [16, 17],
        }
        for _ in range(6)
    ] + [
        {
            "core_numbers": list(range(2, 17)),
            "audited_reserve_numbers": [1, 25],
            "final_card_numbers": list(range(2, 17)) + [1, 25],
        }
    ]
    report = audit_17d_expansion(games)
    assert report["available"] is True
    assert report["nucleos_15d_unicos"] == 2
    assert report["par_adicionado_repetido"] is True


def test_infer_root_cause_prefix_dominance() -> None:
    report = {
        "prefixos_sufixos": {
            "prefixo_mais_dominante": {
                "estrutura": "01-02-03",
                "frequencia": 12,
                "total": 20,
                "share_pct": 60.0,
                "level": "critico",
            }
        },
        "redundancia": {"similaridade_media_entre_jogos": 0.69},
    }
    diag = infer_root_cause(report)
    assert diag["problema_detectado"] == "prefixo_dominante"
    assert diag["acoes_recomendadas"]


def test_full_audit_does_not_mutate_games() -> None:
    games = [
        {
            "core_numbers": list(range(1, 16)),
            "final_card_numbers": list(range(1, 18)),
            "origin": "institutional",
        }
        for _ in range(20)
    ]
    snapshot = [dict(game) for game in games]
    report = audit_structural_concentration(games, game_size=17, generation_event_id=999)
    assert report["mission_id"] == MISSION_ID
    assert report["quantidade_jogos"] == 20
    assert games == snapshot


def test_dominance_thresholds_for_20_game_lot() -> None:
    assert classify_structure_dominance(5, 20)["level"] == "aceitavel"
    assert classify_structure_dominance(7, 20)["level"] == "atencao"
    assert classify_structure_dominance(10, 20)["level"] == "alto"
    assert classify_structure_dominance(12, 20)["level"] == "critico"


def test_build_marker_v56() -> None:
    from dashboard.institutional_build import BUILD_MARKER

    assert BUILD_MARKER == "institutional-adm-runtime-v69"
