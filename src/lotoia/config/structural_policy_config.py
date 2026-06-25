"""Configuração centralizada de políticas estruturais — CORE_002.

Este módulo consolida todas as constantes estruturais usadas pelo pipeline CORE_002,
eliminando valores hardcoded duplicados em múltiplos arquivos.

Versão: 1.0.0
Baseline: últimos 300 concursos oficiais (concursos 3419–3718)
"""

from __future__ import annotations

from typing import Final

# Versão da configuração
CONFIG_VERSION: Final = "1.0.0"

# Janela histórica operacional
HISTORICAL_WINDOW: Final = 300  # últimos 300 concursos

# ============================================================================
# Políticas de prefixo/sufixo
# ============================================================================
STRUCTURAL_POLICY: Final = {
    "triplet_010203": {
        "label": "01-02-03",
        "historical_freq_pct": 0.21,  # 21% — últimos 300 concursos
        "min_cap": 1,
        "cap_formula": "ceil(pool_size * historical_freq_pct)",
    },
    "suffix_232425": {
        "label": "23-24-25",
        "historical_freq_pct": 0.2167,  # 21.67% — últimos 300 concursos
        "min_cap": 1,
        "cap_formula": "ceil(pool_size * historical_freq_pct)",
    },
    "overlap": {
        "max_overlap_15d": 10,
        "relaxation_thresholds": [20, 35, 50],  # tamanho do lote
        "relaxation_increments": [1, 2, 3],
    },
    "architecture": {
        "max_arch_share_pct": 0.12,
    },
}

# ============================================================================
# Dezenas críticas
# ============================================================================
CRITICAL_DIGITS: Final = {
    "reinforce": frozenset({7, 12, 23}),  # reforço suave (+2.5)
    "discourage": frozenset({11, 15, 24, 25}),  # penalização contextual
    "never_hard_block": frozenset({15, 24, 25}),  # nunca bloquear
}

# ============================================================================
# Limites de share (usado em múltiplos módulos)
# ============================================================================
MAX_PREFIX_SUFFIX_SHARE: Final = 0.21
DEFAULT_PREFIX_SHARE_LIMIT: Final = 0.21
