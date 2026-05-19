# Benchmark Temporal

## Fonte de Verdade

O benchmark temporal permanece a fonte principal de validacao cientifica do LotoIA,
conforme ADR 001. A governanca temporal adicionada neste ciclo nao altera o
`benchmark_engine` nem o `backtester`.

## Contrato Para Experimentos Futuros

Todo experimento supervisionado futuro deve declarar:

- split walk-forward utilizado;
- versao de dataset;
- referencia ao benchmark temporal comparavel;
- versao de codigo;
- politica de reproducibilidade;
- ausencia de leakage temporal.

## Comparabilidade

Resultados supervisionados futuros so poderao ser comparados ao baseline estatistico se
usarem janelas temporalmente equivalentes e manifestos completos.

## Consolidacao Cientifica Inicial

A primeira consolidacao formal esta registrada em:

- `ADRs/ADR_006_TEMPORAL_BENCHMARK.md`;
- `experiments/temporal_benchmark/registry.json`;
- `experiments/temporal_benchmark/manifests/temporal_baseline_v0_1_0.json`;
- `experiments/temporal_benchmark/datasets/lotofacil_historico_v0_1_0_2026_05_16.json`;
- `docs/governance/REPRODUCIBLE_TEMPORAL_BENCHMARK.md`.
