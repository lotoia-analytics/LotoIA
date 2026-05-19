# Rastreabilidade Experimental

## Objetivo

Garantir que todo experimento possa ser auditado, reproduzido e comparado com benchmarks
temporais anteriores.

## Manifesto Minimo

Um experimento deve declarar:

- `experiment_id`;
- `created_at`;
- `dataset_version`;
- `code_version`;
- `temporal_split`;
- `benchmark_reference`;
- `reproducibility`.

## Campos Proibidos Na Baseline

- `score_ml`;
- `trained_model_path`;
- `inference_enabled`.

Esses campos indicariam execucao supervisionada real, o que permanece fora de escopo
nesta etapa.
