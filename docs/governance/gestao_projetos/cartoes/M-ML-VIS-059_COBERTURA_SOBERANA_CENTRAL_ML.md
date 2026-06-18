# M-ML-VIS-059 — Central ML usa 100% a leitura soberana da Cobertura Estrutural

| Campo | Valor |
|-------|-------|
| **Missão** | M-ML-VIS-059 |
| **Agentes** | agent_ml + agent_dados + agent_visual + agent_qualidade + agent_governanca |
| **Build ADM** | `institutional-adm-runtime-v41` |
| **Status** | CONCLUÍDA |

## Problema corrigido

Central ML exibia métricas divergentes (similaridade, overlap, quase repetidos) por recalcular/agregar via `build_ml_calibration_aggregate_context` e `_merge_ml_aggregate_metrics`.

## Solução

- `get_structural_coverage_snapshot()` — fonte única compartilhada (Cobertura + Central ML)
- `extract_operational_structural_metrics()` — extrator canônico do payload `redundancia_gp`
- Central ML consome snapshot soberano (escopo **Todos — CORE_002**), sem merge numérico paralelo
- UI exibe fonte, escopo, filtros, GEs, timestamp e checksum da leitura

## Restrições

- CORE_002, Lei 15, Lei 15A, `public_app` intactos
- Sem schema, sem purge
