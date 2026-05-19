# Experiments Registry

Este diretorio armazena manifestos e schemas de experimentos cientificos do LotoIA.

## Status Atual

Baseline de governanca temporal. Nenhum treinamento, inferencia ou `score_ml` esta
implementado.

## Arquivos

- `experiment_manifest.schema.json`: contrato minimo de manifesto experimental.
- `registry.json`: indice institucional inicial de experimentos.
- `templates/experiment_manifest.template.json`: template para experimentos futuros.

## Regra

Manifestos devem ser validados pelos controles de `lotoia.experiments.temporal_governance`
antes de serem usados em qualquer avaliacao supervisionada futura.
