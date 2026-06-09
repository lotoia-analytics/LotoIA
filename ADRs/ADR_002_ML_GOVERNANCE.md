# ADR 002 - ML Governance

## Contexto

A LotoIA incorporou `score_ml` como camada operacional de apoio ao reranking.
Esse ML é interpretável, incremental e subordinado à análise estatística estrutural.

## Problema

Era necessário introduzir ML sem:

- vazamento temporal;
- substituição da lógica estatística;
- opacidade de modelo;
- perda de rastreabilidade;
- quebra da governança científica.

## Decisão

Adotar um pipeline de ML governado com:

- extração de features explícitas;
- calibração linear interpretável;
- reranking supervisionado;
- walk-forward validation;
- snapshots de modelo;
- experiment tracking;
- versionamento de features e modelo.

## Alternativas Consideradas

1. Usar modelos complexos e opacos.
2. Treinar sobre toda a amostra sem validação temporal.
3. Substituir o ranking estatístico por ML.

Essas alternativas foram rejeitadas por violarem temporal safety, interpretabilidade e o posicionamento oficial da plataforma.

## Impacto Arquitetural

- o ML permanece como camada auxiliar;
- a validação temporal passa a ser obrigatória para experimentos;
- os artefatos de ML passam a ser versionados e auditáveis;
- o dashboard exibe o score ML sem alterar a base estatística.

## Riscos

- risco de uso indevido do score ML como substituto da ciência estrutural;
- risco de vazamento temporal se a governança não for respeitada;
- risco de excesso de confiança em métricas isoladas.

## Benefícios

- reranking interpretável;
- experimentação segura;
- comparabilidade histórica;
- snapshots auditáveis;
- transparência dos pesos e contribuições.

## Consequências Futuras

- novos modelos devem manter a mesma disciplina de governança;
- features e versões precisam ser registradas;
- relatórios e snapshots devem acompanhar qualquer evolução supervisionada.

