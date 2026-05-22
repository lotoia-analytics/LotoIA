# Mission 29 - ADM Functional Inventory and Visual Simplification

## Scope

This inventory documents the current ADM surface so we can simplify the operator experience without changing the scientific core, benchmark, walk-forward, or ML governance.

## Functional Inventory

### Operational

- `geracao_jogos` - Gerar Jogos
- `conferir_jogos` - Jogos Passados
- `reconciliacao_operacional` - Simular Resultado
- `jogo_expandido_experimental` - Jogo Expandido

### Analytical

- `estatisticas_historicas` - Resultados Passados
- `historical_intelligence` - Historico
- `analytics_intelligence` - Analises
- `ml_intelligence` - ML
- `backtesting` - Backtesting
- `calibracao_experimental` - Ajustes Operacionais
- `benchmark_cientifico` - Comparativos Cientificos
- `historico_experimental` - Historico Operacional
- `relatorios` - Analiticas Persistidas
- `reports_engine` - Relatorios Tecnicos

### Governance

- `ml_governance` - Governanca ML
- `observability` - Monitoramento
- `workflows` - Automacao

## Redundancy Notes

- `relatorios` and `reports_engine` serve different surfaces and should remain distinct, but their labels are now explicit.
- `historico_experimental` previously duplicated the operational tone of other tests-oriented pages; it is now labeled as an operational history page.
- `backtesting`, `calibracao_experimental`, and `benchmark_cientifico` now use clearer labels to reduce ambiguity in the sidebar.

## Rendering Notes

- The sidebar remains mode-driven.
- The institutional cockpit stays collapsed by default.
- Lead Intelligence continues to degrade safely if cache or query resolution fails.
- No nested expanders were introduced.

## Constraints

- Do not change benchmark, baseline hard, walk-forward, ML governance, or reconciliation semantics.
- Do not remove runtime hardening.
- Preserve telemetry, observability, and institutional persistence.
