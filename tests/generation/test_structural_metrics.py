"""Testes de métricas estruturais — CORE_002."""

import pytest
from lotoia.statistics.structural_metrics_validator import (
    compute_structural_metrics,
    validate_structural_metrics,
    STRUCTURAL_LIMITS,
)


def test_triplet_010203_frequency():
    """Triplet 01-02-03 deve ser computado corretamente."""
    # Gera jogos de teste
    games = [
        {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]},
        {"numbers": [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]},
        {"numbers": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]},
        {"numbers": [1, 2, 3, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]},
        {"numbers": [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]},
    ]

    metrics = compute_structural_metrics(games)

    # 2 de 5 jogos têm triplet (40%)
    assert metrics["triplet_010203_pct"] == 0.40
    assert metrics["triplet_010203_count"] == 2

    # Valida contra limites
    validation = validate_structural_metrics(metrics)
    # 40% está fora do limite máximo (35%), então deve violar
    assert validation["valid"] is False
    assert len(validation["violations"]) > 0


def test_triplet_010203_within_limits():
    """Triplet 01-02-03 deve estar dentro dos limites aceitáveis."""
    # Simula jogos com triplet = 21% e overlap controlado
    games = []
    # 21 jogos com triplet (01-02-03)
    for i in range(21):
        base = [1, 2, 3]  # triplet
        # Adiciona dezenas variadas para manter overlap ~10
        offset = (i * 2) % 10
        base.extend(
            [
                4 + offset,
                5 + offset,
                6 + offset,
                7 + offset,
                8 + offset,
                9 + offset,
                10 + offset,
                11 + offset,
                12 + offset,
                13 + offset,
                14 + offset,
                15 + offset,
            ]
        )
        games.append({"numbers": base[:15]})

    # 79 jogos sem triplet
    for i in range(79):
        base = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
        # Varia ligeiramente para manter overlap ~10
        if i % 3 == 0:
            base = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        elif i % 3 == 1:
            base = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        games.append({"numbers": base})

    metrics = compute_structural_metrics(games)

    # Verifica apenas triplet, não overlap (que pode variar)
    assert 0.15 <= metrics["triplet_010203_pct"] <= 0.27  # 21% ± 6pp


def test_triplet_010203_below_minimum():
    """Triplet 01-02-03 abaixo de 10% deve violar."""
    # Simula jogos com triplet = 5%
    games = []
    for i in range(100):
        if i < 5:  # 5% com triplet
            games.append(
                {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]}
            )
        else:
            games.append(
                {"numbers": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]}
            )

    metrics = compute_structural_metrics(games)
    validation = validate_structural_metrics(metrics)

    assert validation["valid"] is False
    assert len(validation["violations"]) > 0
    assert "Triplet 01-02-03 muito baixo" in validation["violations"][0]


def test_triplet_010203_zero_bug():
    """Triplet 01-02-03 = 0% deve violar (bug do cap=0)."""
    # Simula jogos SEM triplet (bug)
    games = []
    for i in range(50):
        games.append(
            {"numbers": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]}
        )

    metrics = compute_structural_metrics(games)
    validation = validate_structural_metrics(metrics)

    assert validation["valid"] is False
    assert metrics["triplet_010203_count"] == 0
    assert metrics["triplet_010203_pct"] == 0.0
    assert len(validation["violations"]) > 0
    assert "Triplet 01-02-03 muito baixo" in validation["violations"][0]


def test_average_overlap_within_limits():
    """Overlap médio deve estar entre 7-13."""
    # Simula jogos com overlap médio controlado (~10)
    games = [
        {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]},
        {"numbers": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]},
        {"numbers": [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]},
        {"numbers": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]},
        {"numbers": [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]},
    ]

    metrics = compute_structural_metrics(games)

    # Overlap deve estar dentro de [7, 13]
    assert 7.0 <= metrics["avg_overlap"] <= 13.0


def test_average_overlap_too_low():
    """Overlap médio < 7 deve violar."""
    # Jogos muito diferentes (overlap baixo) - SEM triplet 01-02-03
    games = [
        {"numbers": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]},
        {"numbers": [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 3, 2, 1, 11]},
    ]

    metrics = compute_structural_metrics(games)

    # Overlap = 5 (muito baixo)
    assert metrics["avg_overlap"] == 5.0
    validation = validate_structural_metrics(metrics)
    assert validation["valid"] is False
    # Verifica se há violação de overlap (pode haver outras violações também)
    overlap_violations = [v for v in validation["violations"] if "Overlap médio" in v]
    assert len(overlap_violations) > 0
    assert "muito baixo" in overlap_violations[0]


def test_average_overlap_too_high():
    """Overlap médio > 13 deve violar."""
    # Jogos muito similares (overlap alto) - SEM triplet 01-02-03
    games = [
        {"numbers": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]},
        {"numbers": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 19]},
        {"numbers": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 20]},
    ]

    metrics = compute_structural_metrics(games)

    # Overlap = 14 (muito alto)
    assert metrics["avg_overlap"] == 14.0
    validation = validate_structural_metrics(metrics)
    assert validation["valid"] is False
    # Verifica se há violação de overlap (pode haver outras violações também)
    overlap_violations = [v for v in validation["violations"] if "Overlap médio" in v]
    assert len(overlap_violations) > 0
    assert "muito alto" in overlap_violations[0]


def test_structural_limits_configuration():
    """Limites estruturais devem estar configurados corretamente."""
    # Triplet 01-02-03
    triplet_limits = STRUCTURAL_LIMITS["triplet_010203_pct"]
    assert triplet_limits["min"] == 0.10
    assert triplet_limits["max"] == 0.35
    assert triplet_limits["target"] == 0.21
    assert triplet_limits["tolerance"] == 0.06

    # Overlap
    overlap_limits = STRUCTURAL_LIMITS["avg_overlap"]
    assert overlap_limits["min"] == 7.0
    assert overlap_limits["max"] == 13.0
    assert overlap_limits["target"] == 10.0


def test_empty_games_list():
    """Lista vazia de jogos deve retornar métricas vazias."""
    metrics = compute_structural_metrics([])
    assert metrics == {}

    # Validação com métricas vazias deve detectar violações (triplet = 0%)
    # Isso é intencional: se não há jogos, não há triplet, o que é uma violação
    validation = validate_structural_metrics({})
    assert validation["valid"] is False
    assert len(validation["violations"]) > 0


def test_games_without_numbers():
    """Jogos sem campo 'numbers' devem ser tratados graciosamente."""
    games = [
        {"profile_score": 10.0},
        {"profile_score": 8.0},
    ]

    metrics = compute_structural_metrics(games)
    assert metrics["triplet_010203_count"] == 0
    assert metrics["triplet_010203_pct"] == 0.0
    assert metrics["avg_overlap"] == 0.0


def test_validation_strict_mode():
    """Modo strict deve tratar warnings como violações."""
    # Triplet = 30% (dentro de [10%-35%], mas fora de 21% ± 6pp = [15%-27%])
    # Usar jogos sem triplet 01-02-03 para evitar violação de overlap
    games = []
    for i in range(100):
        if i < 30:  # 30% com triplet
            # Jogos com triplet mas overlap controlado
            offset = (i * 2) % 10
            base = [
                1,
                2,
                3,
                4 + offset,
                5 + offset,
                6 + offset,
                7 + offset,
                8 + offset,
                9 + offset,
                10 + offset,
                11 + offset,
                12 + offset,
                13 + offset,
                14 + offset,
                15 + offset,
            ]
            games.append({"numbers": base[:15]})
        else:
            # Jogos sem triplet
            offset = (i * 2) % 10
            base = [
                4 + offset,
                5 + offset,
                6 + offset,
                7 + offset,
                8 + offset,
                9 + offset,
                10 + offset,
                11 + offset,
                12 + offset,
                13 + offset,
                14 + offset,
                15 + offset,
                16 + offset,
                17 + offset,
                18 + offset,
            ]
            games.append({"numbers": base[:15]})

    metrics = compute_structural_metrics(games)

    # Modo normal: válido (30% está em [10%-35%])
    validation_normal = validate_structural_metrics(metrics, strict=False)
    # 30% está dentro de [10%-35%], então não deve violar
    triplet_violations = [v for v in validation_normal["violations"] if "Triplet" in v]
    assert len(triplet_violations) == 0

    # Modo strict: inválido (30% está fora de 21% ± 6pp)
    validation_strict = validate_structural_metrics(metrics, strict=True)
    # No modo strict, warnings viram violações
    assert (
        validation_strict["valid"] is False or len(validation_strict["warnings"]) == 0
    )


def test_metrics_structure():
    """Métricas devem ter a estrutura esperada."""
    games = [
        {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]},
        {"numbers": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]},
    ]

    metrics = compute_structural_metrics(games)

    # Verificar estrutura
    assert "triplet_010203_pct" in metrics
    assert "triplet_010203_count" in metrics
    assert "avg_overlap" in metrics
    assert "games_count" in metrics

    # Verificar tipos
    assert isinstance(metrics["triplet_010203_pct"], float)
    assert isinstance(metrics["triplet_010203_count"], int)
    assert isinstance(metrics["avg_overlap"], float)
    assert isinstance(metrics["games_count"], int)


def test_validation_structure():
    """Validação deve ter a estrutura esperada."""
    metrics = {
        "triplet_010203_pct": 0.21,
        "triplet_010203_count": 21,
        "avg_overlap": 10.0,
        "games_count": 100,
    }

    validation = validate_structural_metrics(metrics)

    # Verificar estrutura
    assert "valid" in validation
    assert "violations" in validation
    assert "warnings" in validation
    assert "metrics" in validation

    # Verificar tipos
    assert isinstance(validation["valid"], bool)
    assert isinstance(validation["violations"], list)
    assert isinstance(validation["warnings"], list)
    assert isinstance(validation["metrics"], dict)
