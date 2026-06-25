# CORE_002 — Núcleo Soberano de Geração

## Visão Geral

O **CORE_002** é o motor soberano de geração de jogos da LotoIA, implantado via **ADR-046** (Núcleo Soberano LEI15). Ele substituiu o CANDIDATE_001 como o caminho oficial de geração após validação operacional.

**Label técnico rastreável:** `STRUCT_LEI15_CORE_CANDIDATE_002_<size>D_001`

**Modo de geração:** `LEI15_CORE_002_SOVEREIGN`

**Política:** `M-GER-044_SOVEREIGN_CONTROLLED`

## Pipeline de 5 Camadas

```
┌─────────────────────────────────────────────────────────────┐
│  L1: generation_cand_d — Pool CAND-D                        │
│  - build_candidate_pool() (N-C1..N-C6)                     │
│  - apply_critical_digit_layer() (reforço 07/12/23)         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  M-ML-072: Pool Estrutural 15D                              │
│  - build_ml_structural_15d_pool()                          │
│  - calibration_plan integration                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  M-STAT-002: Seleção DiverSa (v5)                           │
│  - prefix_cap: 21% (triplet 01-02-03)                      │
│  - suffix_cap: 21% (sufixo 23-24-25)                       │
│  - anti-clone overlap                                      │
│  - family diversity                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  L2: v1_selection_compose + M-CORE-003                      │
│  - pre_filter_pool_diversity()                             │
│  - compose_diverse_gp() (V1)                               │
│  - enforce_gp_diversity_cap() (M-CORE-003)                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  L4: anti_clone_gp                                          │
│  - overlap control (max 10)                                │
│  - architecture limit (max 12%)                            │
│  - V1-strong exception                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  L5: critical_digit_layer                                   │
│  - reforço suave (07/12/23)                                │
│  - penalização contextual (11/15/24/25)                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    GP FINAL COM METADADOS
```

## Formatos Suportados

| Formato | Dezenas | Label |
|---------|---------|-------|
| 15D | 15 dezenas | `STRUCT_LEI15_CORE_CANDIDATE_002_15D_001` |
| 16D | 16 dezenas | `STRUCT_LEI15_CORE_CANDIDATE_002_16D_001` |
| 17D | 17 dezenas | `STRUCT_LEI15_CORE_CANDIDATE_002_17D_001` |
| 18D | 18 dezenas | `STRUCT_LEI15_CORE_CANDIDATE_002_18D_001` |
| 19D | 19 dezenas | `STRUCT_LEI15_CORE_CANDIDATE_002_19D_001` |
| 20D | 20 dezenas | `STRUCT_LEI15_CORE_CANDIDATE_002_20D_001` |
| 21D | 21 dezenas | `STRUCT_LEI15_CORE_CANDIDATE_002_21D_001` |
| 22D | 22 dezenas | `STRUCT_LEI15_CORE_CANDIDATE_002_22D_001` |
| 23D | 23 dezenas | `STRUCT_LEI15_CORE_CANDIDATE_002_23D_001` |

**Formato padrão:** 15D (15 dezenas)

## Camadas Detalhadas

### L1: generation_cand_d — Pool CAND-D

**Arquivo:** `src/lotoia/generation/lei15_core_002.py` → `build_sovereign_pool()`

**Função:** Constrói o pool inicial de candidatos usando motor CAND-D (N-C1..N-C6)

**Componentes:**
- `build_candidate_pool()` — gera pool diversificado
- `apply_critical_digit_layer()` — reforço de dezenas críticas (07, 12, 23)

**Reforço de Dezenas Críticas:**
```python
_REINFORCE_DIGITS: frozenset[int] = frozenset({7, 12, 23})
_CONTEXTUAL_DISCOURAGE: frozenset[int] = frozenset({11, 15, 24, 25})
_NEVER_HARD_BLOCK: frozenset[int] = frozenset({15, 24, 25})
```

**Nota:** Dezena 16 foi removida em PR #322 (super-representada: 80% vs 55% oficial)

### L2: v1_selection_compose — Composição V1

**Arquivo:** `src/lotoia/generation/lei15_core_002.py` → `compose_sovereign_gp()`

**Função:** Compõe o GP (Grupo Principal) usando Realinhamento V1

**Componentes:**
- `pre_filter_pool_diversity()` — pré-filtro de diversidade
- `compose_diverse_gp()` — composição V1
- `enforce_gp_diversity_cap()` — limites de diversidade
- `apply_anti_clone_gp()` — anti-clones por overlap

### L3: v1_strong_shield — Escudo V1 Strong

**Arquivo:** `src/lotoia/generation/lei15_core_structural_payload.py`

**Função:** Protege padrões estruturais fortes (V1 strong patterns)

**Componentes:**
- `is_v1_strong_pattern()` — detecta padrões fortes
- `apply_core_traceability_payload()` — anexa payload de rastreabilidade

### L4: anti_clone_gp — Anti-Clone por Overlap

**Arquivo:** `src/lotoia/generation/lei15_core_002.py` → `apply_anti_clone_gp()`

**Função:** Limita redundância no GP via controle de overlap

**Parâmetros:**
```python
_GP_MAX_OVERLAP: int = 10  # overlap máximo permitido
_GP_MAX_ARCH_PCT: float = 0.12  # limite de arquitetura compartilhada
```

**Exceção:** Padrões V1-strong são isentos do anti-clone

**Relaxamento progressivo por tamanho de lote:**
- Lotes ≥20 jogos: overlap +1
- Lotes ≥35 jogos: overlap +2
- Lotes ≥50 jogos: overlap +3

### L5: critical_digit_layer — Reforço de Dezenas Críticas

**Arquivo:** `src/lotoia/generation/lei15_core_002.py` → `apply_critical_digit_layer()`

**Função:** Reforço suave de dezenas críticas; penalização contextual

**Lógica:**
```python
boost = sum(2.5 for d in _REINFORCE_DIGITS if d in nums)  # 07, 12, 23
penalty = (len(discourage_present) - 3) * 1.5  # se ≥4 de {11, 15, 24, 25}
```

**Resultado:** Ajuste no `profile_score` de cada jogo

## Módulos Estatísticos Integrados

### M-STAT-002 — Seleção DiverSa do Top Slice

**Arquivo:** `src/lotoia/statistics/diverse_top_slice_selection.py`

**Função:** Seleção estatística diversa do pool antes do portão M-ML-073

**Versão atual:** `M-STAT-002-v5` (após correção PR #323)

**Políticas aplicadas:**
- Teto de dominância do triplet 01-02-03 (agora 21% — PR #323)
- Teto de dominância de sufixos
- Anti-clone por overlap
- Diversidade por família (prefixo + sufixo)

**Constantes centralizadas:**
```python
# Em src/lotoia/config/structural_policy_config.py
MAX_PREFIX_SUFFIX_SHARE = 0.21  # Frequência histórica do triplet (21%)
```

### M-CORE-003 — Política Anti-Viés de Prefixo/Sufixo

**Arquivo:** `src/lotoia/generation/m_core_003_prefix_suffix_policy.py`

**Função:** Política anti-viés baseada em frequências históricas

**Baseline:** últimos 300 concursos oficiais (atualizado em PR #323)

**Tabelas de frequência:**
```python
HISTORICAL_PREFIX_FREQ_PCT = {
    "01-02-03": 21.00,  # triplet dominante
    "01-02-04": 11.67,
    "02-03-04": 9.33,
    # ... (20 prefixos com freq ≥ 1%)
}

HISTORICAL_SUFFIX_FREQ_PCT = {
    "23-24-25": 21.67,  # sufixo dominante
    "22-23-25": 9.33,
    "22-24-25": 8.67,
    # ... (19 sufixos com freq ≥ 1%)
}
```

## Validação de Métricas

O sistema valida automaticamente as métricas pós-geração:

| Métrica | Mínimo | Target | Máximo |
|---------|--------|--------|--------|
| Triplet 01-02-03 | 10% | 21% | 35% |
| Suffix 23-24-25 | 10% | 21.67% | 35% |
| Overlap médio | 7.0 | 10.0 | 13.0 |
| Diversity score | 0.70 | 0.78 | 1.00 |

**Arquivo:** `src/lotoia/statistics/structural_metrics_validator.py`

Violações geram logs ERROR e são persistidas no `context_json`.

## Logs Estruturados

Cada camada gera logs estruturados para debug:

```
[CORE_002:L1] Pool construído | size=150 variant=D epoch=EPOCH_002 | triplet_010203=31 (20.7%) | suffix_232425=32 (21.3%)
[CORE_002:L4] Anti-clone aplicado | input=150 selected=50 target=50 rejected=100 game_size=15
[CORE_002:L5] Critical digit layer | pool=50 games_with_boost=48 games_with_penalty=2 | avg_boost=5.20 avg_penalty=0.00
[CORE_002] GP gerado | pool=150 gp=50 | triplet_010203=10/50 (20.0%) | suffix_232425=11/50 (22.0%) | avg_overlap=9.5 | anti_clone_rejected=100 | diversity=0.78
```

## Governança

### ADR-046 — Núcleo Soberano LEI15

**Arquivo:** `src/lotoia/governance/lei15_core_002_sovereign.py`

**Status:** `NUCLEO_SOBERANO_LEI15`

**Configuração:**
```python
@dataclass(frozen=True, slots=True)
class Core002SovereignConfig:
    mode: str = "sovereign"
    sovereign_core_status: str = "NUCLEO_SOBERANO_LEI15"
    candidate_origin_label: str = "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001"
    generation_blocked: bool = False  # ativo por padrão
    lei15a_blocked: bool = True  # Lei 15A bloqueada
    legacy_core_frozen: bool = True  # core legado congelado
    active_public_blocked: bool = True  # endpoints públicos bloqueados
    adr: str = "ADR-046"
    evidence_epoch: str = "EPOCH_001_LEI15_CORE_002"
```

## Metadados Anexados a Cada Jogo

Cada jogo gerado recebe:

```python
{
    "lei15_core_002_applied": True,
    "sovereign_core_status": "NUCLEO_SOBERANO_LEI15",
    "candidate_origin_label": "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
    "generation_cand_d_applied": True,
    "v1_selection_compose_applied": True,
    "v1_strong_shield_applied": True,
    "anti_clone_gp_applied": True,
    "critical_digit_layer_applied": True,
    "m_core_003_pre_filter_applied": True,
    "m_stat_002_diverse_top_slice_applied": True,
    
    "lei15_core_002_metadata": {
        "core_id": "LEI15_CORE_002",
        "adr": "ADR-046",
        "layers": [
            "generation_cand_d",
            "v1_selection_compose",
            "m_core_003_prefix_suffix_policy",
            "v1_strong_shield",
            "anti_clone_gp",
            "critical_digit_layer"
        ],
        "critical_digit_boost": 2.5,
        "critical_digit_penalty": 0.0,
    }
}
```

## Arquivos Principais

| Arquivo | Função |
|---------|--------|
| `src/lotoia/generation/lei15_core_002.py` | Motor principal CORE_002 (5 camadas) |
| `src/lotoia/governance/lei15_core_002_sovereign.py` | Governança e configuração soberana |
| `src/lotoia/generation/m_core_003_prefix_suffix_policy.py` | Política anti-viés prefixo/sufixo |
| `src/lotoia/statistics/diverse_top_slice_selection.py` | Seleção diverSa M-STAT-002 (v5) |
| `src/lotoia/statistics/structural_metrics_validator.py` | Validação de métricas estruturais |
| `src/lotoia/config/structural_policy_config.py` | Configuração centralizada |
| `src/lotoia/ml/structural_pool_15d_generator.py` | Pool estrutural M-ML-072 |
| `src/lotoia/ml/supervised_output_calibration.py` | Calibração supervisionada M-ML-073b |
| `src/lotoia/governance/analysis_batch_labels.py` | Labels e tipos de batch |
| `src/lotoia/generator/basic_generator.py` | Gerador base (integra CORE_002) |

## Status Operacional

- **Núcleo Soberano:** `NUCLEO_SOBERANO_LEI15` (ativo)
- **Geração:** Habilitada por padrão
- **Lei 15A:** Bloqueada (requer ordem institucional)
- **Core Legado:** Congelado (read-only)
- **Endpoints Públicos:** Bloqueados (ADR-047)
- **Dashboard ADM:** Único caminho autorizado de geração

## Referências

- [ADR-046](../adr/ADR-046_NUCLEO_SOBERANO_LEI15.md) — Núcleo Soberano LEI15
- [CHANGELOG](../../CHANGELOG.md) — Histórico de mudanças
- [README](../../README.md) — Visão geral do projeto
