# Datasets Supervisionados

## Status

O LotoIA ainda nao possui dataset supervisionado operacional oficial. Este documento
define a estrutura minima para uma evolucao futura temporalmente valida.

## Campos Minimos Esperados

- `sample_id`: identificador reproduzivel da amostra;
- `feature_cutoff_contest`: ultimo concurso permitido para construcao de features;
- `label_contest`: concurso futuro usado para avaliacao;
- `dataset_version`: versao institucional do dataset;
- `feature_schema_version`: versao do contrato de features;
- `source_snapshot`: snapshot de dados usado na geracao.

## Regras

- `feature_cutoff_contest` deve ser menor que `label_contest`;
- features estatisticas devem ser recalculadas apenas com historico ate o corte;
- labels nao podem ser usados para criar features;
- `score_ml` nao faz parte da estrutura baseline;
- datasets devem ser versionados antes de qualquer benchmark supervisionado.

## Fora de Escopo Nesta Etapa

- treinamento;
- inferencia;
- selecao automatica de features;
- calibracao supervisionada;
- score supervisionado.
