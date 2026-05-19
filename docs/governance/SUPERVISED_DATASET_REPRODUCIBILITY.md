# Reproducibilidade de Datasets Supervisionados

## Status

Baseline institucional declarativa, sem dataset supervisionado materializado.

## Artefatos Oficiais

- Registry: `experiments/supervised_dataset/registry.json`
- Dataset manifest: `experiments/supervised_dataset/datasets/lotofacil_supervised_governance_v0_1_0.json`
- Feature manifest: `experiments/supervised_dataset/manifests/feature_manifest_v0_1_0.json`
- Target manifest: `experiments/supervised_dataset/manifests/target_manifest_v0_1_0.json`
- Contrato temporal: `experiments/supervised_dataset/manifests/temporal_feature_contract_v0_1_0.json`
- Schemas: `experiments/supervised_dataset/schemas/`

## Politica Temporal

Cada linha supervisionada futura deve declarar:

- `sample_id`;
- `feature_cutoff_contest`;
- `label_contest`;
- versao do dataset;
- versao dos manifests de features e targets.

A regra obrigatoria e:

```text
feature_cutoff_contest < label_contest
```

Features estatisticas devem ser calculadas apenas com concursos anteriores ao corte de
features. Targets podem ser unidos somente depois da materializacao das features.

## Politica de Versionamento

Cada dataset supervisionado deve possuir:

- `dataset_id`;
- `dataset_version`;
- snapshot de origem;
- manifest de features;
- manifest de targets;
- contrato temporal;
- lineage;
- politica de hash;
- referencia aos ADRs 001 a 007.

Mudancas em features, targets, janela temporal, snapshot de origem ou politica de hash
exigem nova versao de dataset.

## Proibicoes

Nesta etapa seguem proibidos:

- `score_ml`;
- treino supervisionado;
- inferencia supervisionada;
- outputs de modelo;
- targets como features;
- estatisticas globais calculadas com concursos futuros;
- alteracoes no benchmark engine, backtester, ranking hibrido ou gerador principal.

## Validacao Minima

Os validadores oficiais residem em:

```text
src/lotoia/experiments/supervised_dataset.py
```

Eles verificam:

- integridade de manifests;
- contrato temporal de features;
- targets validos;
- lineage supervisionado;
- duplicidade de amostras;
- leakage por `feature_cutoff_contest >= label_contest`;
- campos proibidos de execucao supervisionada real.
