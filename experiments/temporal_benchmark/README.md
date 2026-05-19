# Temporal Benchmark Registry

Este diretorio registra a primeira consolidacao cientifica do benchmark temporal do
LotoIA.

## Escopo

- baseline temporal estatistico;
- estrutura inicial para benchmark supervisionado futuro;
- contrato de walk-forward validation;
- snapshots versionados de dataset;
- manifests reproduziveis;
- rastreabilidade temporal.

## Fora de Escopo

- treinamento supervisionado real;
- inferencia supervisionada real;
- `score_ml`;
- alteracao de ranking estatistico;
- alteracao do benchmark operacional;
- alteracao do backtester principal.

## Artefatos

- `registry.json`: indice institucional.
- `datasets/lotofacil_historico_v0_1_0_2026_05_16.json`: snapshot canonico inicial.
- `manifests/temporal_baseline_v0_1_0.json`: manifesto de baseline temporal.

## Regra de Comparabilidade

Experimentos futuros so devem ser comparados ao baseline se usarem manifestos completos,
splits temporalmente validos e dataset snapshot versionado.
