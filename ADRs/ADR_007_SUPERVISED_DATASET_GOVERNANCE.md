# ADR 007 - Governanca Oficial do Dataset Supervisionado

## Status

Aceito

---

## Contexto

Os ADRs 001 a 006 definiram o LotoIA como uma plataforma estatistica estrutural com
assistencia supervisionada incremental. Tambem estabeleceram que ML nao pode substituir a
analise estatistica, que o namespace oficial e `src/lotoia`, que qualquer evolucao
supervisionada depende de validade temporal e que o benchmark temporal e a referencia
cientifica central.

Antes de qualquer treinamento real, o projeto precisa governar datasets supervisionados
com manifests, contratos temporais, lineage e regras de reproducibilidade.

---

## Decisao

O LotoIA adota governanca oficial para datasets supervisionados como camada institucional
de preparacao, sem implementar treinamento, inferencia ou `score_ml`.

A partir deste ADR, todo dataset supervisionado deve declarar:

- registry supervisionado;
- manifest de features;
- manifest de targets;
- contrato temporal de features;
- lineage de dataset;
- versao de dataset;
- politica de reproducibilidade;
- proibicoes explicitas contra leakage e execucao supervisionada real nesta etapa.

---

## Regras

- Toda logica reutilizavel deve residir em `src/lotoia`.
- Artefatos institucionais devem residir em `experiments/supervised_dataset`.
- Features supervisionadas devem declarar `feature_cutoff_contest`.
- Targets devem declarar `label_contest`.
- A relacao temporal obrigatoria e `feature_cutoff_contest < label_contest`.
- Features nao podem usar targets, estatisticas futuras ou draws posteriores ao corte.
- Datasets, manifests e contratos devem ser versionados.
- Lineage deve declarar snapshot de origem, transformacoes e politica temporal.

---

## Fora de Escopo

Permanecem proibidos nesta consolidacao:

- `score_ml`;
- treinamento supervisionado real;
- inferencia supervisionada real;
- modelos supervisionados reais;
- alteracao do benchmark engine;
- alteracao do backtester;
- alteracao do ranking hibrido;
- alteracao do gerador principal.

---

## Impacto

Este ADR nao altera o comportamento operacional do LotoIA. Ele cria uma base auditavel
para construcao futura de datasets supervisionados temporalmente validos e comparaveis
ao benchmark cientifico.

---

## Riscos Residuais

- O dataset supervisionado inicial permanece declarativo.
- Ainda nao ha materializacao de linhas supervisionadas oficiais.
- Reprodutibilidade total ainda depende de snapshots imutaveis e versao de codigo real.
- Validadores atuais cobrem contratos e manifests, mas nao substituem auditoria estatistica
  futura sobre cada feature materializada.
