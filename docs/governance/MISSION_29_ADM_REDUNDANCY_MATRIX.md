# Mission 29 - ADM Redundancy Matrix

## Goal

This matrix is the operational decision layer for simplifying the ADM without changing the scientific core, workflows, reconciliation, telemetry, observability, or ML governance.

## Decision Model

| Action | Meaning |
| --- | --- |
| `permanecer` | Keep visible in the daily operator flow |
| `recolher` | Keep available but reduce prominence or move to advanced surfaces |
| `ocultar` | Hide by default and expose only when needed |
| `remover` | Remove if a page or widget is duplicative or no longer needed |
| `isolar` | Keep separate from operational flow, especially for experiments |

## Current Recommendations

| Page | Category | Usage | Action |
| --- | --- | --- | --- |
| `geracao_jogos` | operacional | alto | permanecer |
| `conferir_jogos` | operacional | alto | permanecer |
| `reconciliacao_operacional` | operacional | alto | permanecer |
| `workflows` | operacional | alto | permanecer |
| `jogo_expandido_experimental` | operacional | medio | recolher |
| `estatisticas_historicas` | analitica | medio | recolher |
| `historical_intelligence` | analitica | medio | recolher |
| `analytics_intelligence` | analitica | medio | recolher |
| `ml_intelligence` | analitica | baixo | recolher |
| `relatorios` | analitica | medio | recolher |
| `ml_governance` | governanca | medio | recolher |
| `observability` | governanca | medio | recolher |
| `backtesting` | analitica | baixo | ocultar |
| `calibracao_experimental` | analitica | baixo | ocultar |
| `benchmark_cientifico` | governanca | baixo | ocultar |
| `historico_experimental` | operacional | baixo | ocultar |
| `reports_engine` | governanca | baixo | ocultar |

## Notes

- The default operational sidebar should prioritize only the pages marked as `permanecer`.
- `recolher` pages stay accessible through analytical mode.
- `ocultar` pages remain available for governance or diagnostic use, but should not dominate the daily flow.
- No scientific logic was modified in this matrix.
