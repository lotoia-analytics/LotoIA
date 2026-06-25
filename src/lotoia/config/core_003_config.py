"""Configuração centralizada do CORE_003 — Pipeline Simplificado.

Substitui a configuração fragmentada do CORE_002 por uma configuração unificada
com presets de calibração pré-definidos.
"""

from __future__ import annotations

from typing import Any, Literal

# Tipo para presets de calibração
CalibrationPreset = Literal["conservador", "equilibrado", "agressivo"]

# Configuração principal do CORE_003
CORE_003_CONFIG: dict[str, Any] = {
    # Janela histórica para cálculos estatísticos
    "historical_window": 300,  # últimos 300 concursos
    # Formatos suportados
    "formats": {
        "15D": {"dezenas": 15, "target_contest": None},
        "16D": {"dezenas": 16, "target_contest": None},
        "17D": {"dezenas": 17, "target_contest": None},
        "18D": {"dezenas": 18, "target_contest": None},
        "19D": {"dezenas": 19, "target_contest": None},
        "20D": {"dezenas": 20, "target_contest": None},
        "21D": {"dezenas": 21, "target_contest": None},
        "22D": {"dezenas": 22, "target_contest": None},
        "23D": {"dezenas": 23, "target_contest": None},
    },
    # Políticas estruturais consolidadas
    "structural_policy": {
        # Triplet 01-02-03: frequência histórica 21%
        "triplet_010203": {
            "freq": 0.21,
            "min_cap": 1,
            "max_cap": None,  # calculado dinamicamente
        },
        # Suffix 23-24-25: frequência histórica 21.67%
        "suffix_232425": {
            "freq": 0.2167,
            "min_cap": 1,
            "max_cap": None,
        },
        # Overlap entre jogos
        "overlap": {
            "max": 10,
            "relaxation_thresholds": [20, 35, 50],  # tamanhos de lote
            "relaxation_increments": [1, 2, 3],
        },
        # Arquitetura (prefixo + sufixo)
        "architecture": {
            "max_share_pct": 0.12,
        },
    },
    # Dezenas críticas
    "critical_digits": {
        "reinforce": [7, 12, 23],  # reforço suave (+boost)
        "discourage": [11, 15, 24, 25],  # penalização contextual
        "never_block": [15, 24, 25],  # nunca bloquear completamente
    },
    # Presets de calibração (10 parâmetros essenciais)
    "calibration_presets": {
        "conservador": {
            "overlap_penalty": 1.10,
            "diversity_floor": 0.75,
            "critical_digit_boost": 2.0,
            "critical_digit_boost_multiplier": 0.8,
            "max_overlap": 11,
            "min_triplet_pct": 0.10,
            "max_triplet_pct": 0.30,
            "min_suffix_pct": 0.10,
            "max_suffix_pct": 0.30,
            "pool_multiplier": 2.5,
        },
        "equilibrado": {
            "overlap_penalty": 1.15,
            "diversity_floor": 0.78,
            "critical_digit_boost": 2.5,
            "critical_digit_boost_multiplier": 1.0,
            "max_overlap": 10,
            "min_triplet_pct": 0.15,
            "max_triplet_pct": 0.27,
            "min_suffix_pct": 0.15,
            "max_suffix_pct": 0.27,
            "pool_multiplier": 3.0,
        },
        "agressivo": {
            "overlap_penalty": 1.20,
            "diversity_floor": 0.80,
            "critical_digit_boost": 3.0,
            "critical_digit_boost_multiplier": 1.2,
            "max_overlap": 9,
            "min_triplet_pct": 0.18,
            "max_triplet_pct": 0.24,
            "min_suffix_pct": 0.18,
            "max_suffix_pct": 0.24,
            "pool_multiplier": 3.5,
        },
    },
    # Limites de validação (usados por structural_metrics_validator)
    "validation_limits": {
        "triplet_010203_pct": {
            "min": 0.10,
            "max": 0.35,
            "target": 0.21,
            "tolerance": 0.06,
        },
        "avg_overlap": {
            "min": 7.0,
            "max": 13.0,
            "target": 10.0,
        },
        "diversity_score": {
            "min": 0.70,
            "target": 0.78,
        },
    },
}


def get_calibration_preset(preset: CalibrationPreset) -> dict[str, Any]:
    """Retorna configuração de um preset específico.

    Args:
        preset: Nome do preset (conservador, equilibrado, agressivo)

    Returns:
        Dicionário com parâmetros do preset

    Raises:
        ValueError: Se preset não existir
    """
    presets = CORE_003_CONFIG["calibration_presets"]
    if preset not in presets:
        raise ValueError(
            f"Preset '{preset}' não encontrado. "
            f"Opções disponíveis: {list(presets.keys())}"
        )
    return presets[preset].copy()


def get_format_config(format: str) -> dict[str, Any]:
    """Retorna configuração de um formato específico.

    Args:
        format: Formato (15D, 17D, etc.)

    Returns:
        Dicionário com configuração do formato

    Raises:
        ValueError: Se formato não existir
    """
    formats = CORE_003_CONFIG["formats"]
    if format not in formats:
        raise ValueError(
            f"Formato '{format}' não encontrado. "
            f"Opções disponíveis: {list(formats.keys())}"
        )
    return formats[format].copy()


def get_structural_policy() -> dict[str, Any]:
    """Retorna políticas estruturais consolidadas."""
    return CORE_003_CONFIG["structural_policy"].copy()


def get_critical_digits() -> dict[str, Any]:
    """Retorna configuração de dezenas críticas."""
    return CORE_003_CONFIG["critical_digits"].copy()


def get_validation_limits() -> dict[str, Any]:
    """Retorna limites de validação de métricas."""
    return CORE_003_CONFIG["validation_limits"].copy()
