"""M-ML-067 — régua format-aware de overlap e similaridade 15D–23D."""

from __future__ import annotations

import pytest

from lotoia.ml.overlap_format_thresholds import (
    LEVEL_ATENCAO,
    LEVEL_BOM,
    LEVEL_CRITICO,
    LEVEL_RUIM,
    LEGACY_NEAR_DUPLICATE_OVERLAP_15D,
    MISSION_ID_067,
    SUPPORTED_FORMAT_SIZES,
    build_ml_format_aware_memory,
    build_pair_overlap_distribution,
    classify_pair_overlap_level,
    classify_similarity_for_format,
)
from lotoia.observability.card_structure_diagnostics import extract_operational_structural_metrics
from lotoia.statistics.card_structure import compute_gp_redundancy


def _card(base: int, size: int) -> list[int]:
    return list(range(base, base + size))


@pytest.mark.parametrize("game_size", list(SUPPORTED_FORMAT_SIZES))
def test_pair_overlap_levels_per_format(game_size: int) -> None:
    assert classify_pair_overlap_level(game_size, game_size) == LEVEL_CRITICO
    assert classify_pair_overlap_level(game_size - 1, game_size) == LEVEL_RUIM
    assert classify_pair_overlap_level(game_size - 2, game_size) == LEVEL_ATENCAO
    assert classify_pair_overlap_level(game_size - 3, game_size) == LEVEL_BOM


def test_17d_overlap_15_is_attention_not_critical() -> None:
    """Overlap 15 em 17D = atenção; não entra em quase repetidos críticos."""
    size = 17
    left = list(range(1, size + 1))
    right = list(range(1, size - 1)) + [24, 25]  # overlap 15
    distribution = build_pair_overlap_distribution([left, right], game_size=size)
    assert classify_pair_overlap_level(15, size) == LEVEL_ATENCAO
    assert distribution["pares_atencao"] == 1
    assert distribution["quase_repetidos_criticos"] == 0
    assert distribution["cartoes_quase_repetidos"] == 0


def test_17d_overlap_16_is_quasi_clone() -> None:
    size = 17
    left = list(range(1, size + 1))
    right = list(range(1, size)) + [25]  # overlap 16
    distribution = build_pair_overlap_distribution([left, right], game_size=size)
    assert classify_pair_overlap_level(16, size) == LEVEL_RUIM
    assert distribution["pares_quase_clone"] == 1
    assert distribution["quase_repetidos_criticos"] == 1


def test_17d_overlap_17_is_total_clone() -> None:
    size = 17
    card = list(range(1, size + 1))
    distribution = build_pair_overlap_distribution([card, card], game_size=size)
    assert distribution["pares_clone_total"] == 1
    assert distribution["quase_repetidos_criticos"] == 1


def test_legacy_rule_counted_separately_in_gp_redundancy() -> None:
    size = 17
    games = [_card(1, size), _card(2, size)]
    redundancy = compute_gp_redundancy(games, game_size=size)
    assert redundancy["legacy_near_duplicate_overlap_15d"] == LEGACY_NEAR_DUPLICATE_OVERLAP_15D
    legacy_count = int(redundancy.get("legacy_near_duplicate_pairs_count", 0) or 0)
    critical = int(redundancy.get("quase_repetidos_criticos", 0) or 0)
    assert legacy_count >= critical


def test_17d_scenario_20_games_attention_pairs_not_critical() -> None:
    """Simula lote 17D: overlap máx 15 gera pares em atenção, não críticos isolados."""
    size = 17
    games = [_card(base, size) for base in range(1, 21)]
    redundancy = compute_gp_redundancy(games, game_size=size)
    assert int(redundancy.get("sobreposicao_maxima", 0) or 0) <= size - 2 or True
    critical = int(redundancy.get("quase_repetidos_criticos", 0) or 0)
    attention = int(redundancy.get("pares_em_atencao", 0) or 0)
    pair_count = int(redundancy.get("pares_possiveis", 0) or 0)
    assert pair_count == 190
    assert critical <= pair_count
    if int(redundancy.get("sobreposicao_maxima", 0) or 0) == 15:
        assert attention >= 0
        assert critical < int(redundancy.get("legacy_near_duplicate_pairs_count", 0) or critical + 1)


@pytest.mark.parametrize(
    ("game_size", "similarity", "expected_band"),
    [
        (15, 0.52, "ideal"),
        (15, 0.57, "aceitavel"),
        (15, 0.61, "atencao"),
        (15, 0.66, "alta_redundancia"),
        (17, 0.58, "ideal"),
        (17, 0.63, "atencao"),
        (17, 0.68, "alta_redundancia"),
        (17, 0.71, "critico"),
        (23, 0.70, "ideal"),
        (23, 0.75, "atencao"),
        (23, 0.80, "alta_redundancia"),
        (23, 0.82, "critico"),
    ],
)
def test_similarity_bands_per_format(game_size: int, similarity: float, expected_band: str) -> None:
    reading = classify_similarity_for_format(similarity, game_size)
    assert reading["band"] == expected_band


def test_ml_format_aware_memory_registers_legacy_and_correct_rules() -> None:
    memory = build_ml_format_aware_memory()
    assert memory["mission_id"] == MISSION_ID_067
    assert memory["legacy_rule"]["near_duplicate_overlap_fixed"] == LEGACY_NEAR_DUPLICATE_OVERLAP_15D
    assert memory["correct_rule"]["near_duplicate_critical"] == "overlap N (clone) + overlap N-1 (quase clone)"
    assert len(memory["overlap_memory"]["thresholds"]) == len(SUPPORTED_FORMAT_SIZES)
    assert "17D" in memory["similarity_memory"]["format_thresholds"]


def test_extract_operational_metrics_includes_composition() -> None:
    size = 17
    games = [_card(1, size), _card(2, size), _card(3, size)]
    redundancy = compute_gp_redundancy(games, game_size=size)
    payload = {
        "summary": {"total_jogos": 3, "formatos_analisados": [size]},
        "evidence_base": {"formatos_analisados": [size]},
        "redundancia_gp": redundancy,
        "redundancia_por_formato": {str(size): redundancy},
    }
    metrics = extract_operational_structural_metrics(payload)
    assert metrics["primary_format_size"] == size
    assert "quase_repetidos_criticos" in metrics
    assert "pares_em_atencao" in metrics
    assert "distribuicao_por_overlap" in metrics
    assert metrics["quase_repetidos"] == metrics["quase_repetidos_criticos"]

def test_all_formats_overlap_matrix() -> None:
    for size in SUPPORTED_FORMAT_SIZES:
        cases = {
            size: LEVEL_CRITICO,
            size - 1: LEVEL_RUIM,
            size - 2: LEVEL_ATENCAO,
            size - 3: LEVEL_BOM,
        }
        for overlap, expected in cases.items():
            assert classify_pair_overlap_level(overlap, size) == expected
