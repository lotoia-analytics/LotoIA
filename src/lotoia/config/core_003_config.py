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
    # Formatos com geradores nativos (Fase 3)
    "native_formats": {"15D", "17D", "18D", "20D", "23D"},
    # Políticas nativas por formato (Fase 3 — Geração Nativa)
    "native_format_policies": {
        "15D": {
            "parity_targets": [(7, 8), (8, 7)],
            "repeat_min": 7,
            "repeat_max": 10,
            "sum_range": (180, 220),
            "overlap_target": 10.0,
        },
        "17D": {
            "parity_targets": [(9, 8), (8, 9)],
            "repeat_min": 8,
            "repeat_max": 11,
            "sum_range": (200, 250),
            "overlap_target": 11.3,
        },
        "18D": {
            "parity_targets": [(9, 9), (10, 8), (8, 10)],
            "repeat_min": 8,
            "repeat_max": 12,
            "sum_range": (210, 260),
            "overlap_target": 12.0,
        },
        "20D": {
            "parity_targets": [(10, 10), (11, 9), (9, 11)],
            "repeat_min": 9,
            "repeat_max": 14,
            "sum_range": (230, 280),
            "overlap_target": 13.3,
        },
        "23D": {
            "parity_targets": [(12, 11), (11, 12)],
            "repeat_min": 10,
            "repeat_max": 16,
            "sum_range": (260, 310),
            "overlap_target": 15.3,
        },
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
        "avg_overlap_by_format": {
            "15D": {"min": 7.0, "max": 13.0, "target": 10.0},
            "16D": {"min": 7.5, "max": 14.0, "target": 10.7},
            "17D": {"min": 8.0, "max": 15.0, "target": 11.3},
            "18D": {"min": 8.5, "max": 16.0, "target": 12.0},
            "19D": {"min": 9.0, "max": 17.0, "target": 12.7},
            "20D": {"min": 9.5, "max": 18.0, "target": 13.3},
            "21D": {"min": 10.0, "max": 19.0, "target": 14.0},
            "22D": {"min": 10.5, "max": 20.0, "target": 14.7},
            "23D": {"min": 11.0, "max": 22.0, "target": 15.3},
        },
        "triplet_by_format": {
            "15D": {"min": 0.10, "max": 0.35, "target": 0.21},
            "16D": {"min": 0.10, "max": 0.50, "target": 0.25},
            "17D": {"min": 0.10, "max": 0.60, "target": 0.30},
            "18D": {"min": 0.10, "max": 0.60, "target": 0.35},
            "19D": {"min": 0.10, "max": 0.65, "target": 0.40},
            "20D": {"min": 0.10, "max": 0.70, "target": 0.45},
            "21D": {"min": 0.10, "max": 0.75, "target": 0.50},
            "22D": {"min": 0.10, "max": 0.90, "target": 0.55},
            "23D": {"min": 0.10, "max": 0.95, "target": 0.60},
        },
        "diversity_score": {
            "min": 0.70,
            "target": 0.78,
        },
    },
    # Intervalos de confiança estatística (Fase 1)
    "confidence_intervals": {
        "triplet_010203": {
            "value": 0.21,
            "confidence_interval": [0.164, 0.256],
            "confidence_level": 0.95,
            "sample_size": 300,
            "margin_of_error": 0.046,
            "last_updated": "2026-06-25",
        },
        "suffix_232425": {
            "value": 0.2167,
            "confidence_interval": [0.170, 0.263],
            "confidence_level": 0.95,
            "sample_size": 300,
            "margin_of_error": 0.047,
            "last_updated": "2026-06-25",
        },
        "paridade_8_7": {
            "value": 0.35,
            "confidence_interval": [0.296, 0.404],
            "confidence_level": 0.95,
            "sample_size": 300,
            "margin_of_error": 0.054,
            "last_updated": "2026-06-25",
        },
        "soma_180_220": {
            "value": 0.60,
            "confidence_interval": [0.545, 0.655],
            "confidence_level": 0.95,
            "sample_size": 300,
            "margin_of_error": 0.055,
            "last_updated": "2026-06-25",
        },
    },
}


def get_calibration_preset(preset: CalibrationPreset) -> dict[str, Any]:
    presets = CORE_003_CONFIG["calibration_presets"]
    if preset not in presets:
        raise ValueError(
            f"Preset '{preset}' não encontrado. "
            f"Opções disponíveis: {list(presets.keys())}"
        )
    return presets[preset].copy()


def get_format_config(format: str) -> dict[str, Any]:
    formats = CORE_003_CONFIG["formats"]
    if format not in formats:
        raise ValueError(
            f"Formato '{format}' não encontrado. "
            f"Opções disponíveis: {list(formats.keys())}"
        )
    return formats[format].copy()


def get_native_format_policy(format: str) -> dict[str, Any] | None:
    """Retorna políticas nativas para um formato (Fase 3).
    
    Returns:
        Dict com políticas nativas ou None se formato não tem gerador nativo.
    """
    return CORE_003_CONFIG["native_format_policies"].get(format)


def is_native_format(format: str) -> bool:
    """Verifica se formato tem gerador nativo (Fase 3)."""
    return format in CORE_003_CONFIG["native_formats"]


def get_structural_policy() -> dict[str, Any]:
    return CORE_003_CONFIG["structural_policy"].copy()


def get_critical_digits() -> dict[str, Any]:
    return CORE_003_CONFIG["critical_digits"].copy()


def get_validation_limits() -> dict[str, Any]:
    return CORE_003_CONFIG["validation_limits"].copy()


def get_confidence_intervals() -> dict[str, Any]:
    return CORE_003_CONFIG["confidence_intervals"].copy()


def get_confidence_interval(metric: str) -> dict[str, Any] | None:
    return CORE_003_CONFIG["confidence_intervals"].get(metric)
