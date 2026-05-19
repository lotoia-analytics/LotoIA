# Supervised Dataset Governance

Esta pasta contem a governanca institucional do dataset supervisionado do LotoIA.

## Conteudo

- `registry.json`: indice oficial de datasets e manifests supervisionados.
- `datasets/`: manifests versionados de datasets supervisionados.
- `manifests/`: manifests de features, targets e contratos temporais.
- `schemas/`: schemas JSON documentais para os manifests.

## Escopo

A camada e declarativa e cientifica. Ela nao treina modelos, nao executa inferencia e nao
introduz `score_ml`.

## Contrato Temporal

Toda amostra supervisionada futura deve obedecer:

```text
feature_cutoff_contest < label_contest
```

Features sao construidas antes do target. Targets sao unidos apenas depois da
materializacao das features.
