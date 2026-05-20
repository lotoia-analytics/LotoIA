# LotoIA - Documentação Institucional Oficial

## Visão Oficial

A LotoIA é uma plataforma estatística estrutural com assistência supervisionada incremental.
Seu foco institucional está em análise probabilística, priorização estrutural, validação temporal, interpretabilidade e benchmarking científico.

A camada de Machine Learning é auxiliar, governada e incremental.
Ela não substitui a análise estatística estrutural nem altera a filosofia oficial da plataforma.

## Princípios Institucionais

- Nunca quebrar a arquitetura modular do `src/`.
- Nunca introduzir vazamento temporal.
- Nunca substituir a análise estatística estrutural por ML opaco.
- Sempre manter benchmarking e validação temporal.
- Sempre preservar reprodutibilidade, versionamento e rastreabilidade.
- Sempre manter persistência separada da lógica estatística.

## Arquitetura

### Estrutura principal

- `src/`: lógica de negócio, ciência, ML, governança e domínio operacional.
- `dashboard/`: interface Streamlit institucional.
- `reports/`: relatórios, snapshots e artefatos exportados.
- `data/`: persistência e dados de suporte.
- `tests/`: validação automatizada.
- `experiments/`: governança de experimentos e validação supervisionada.

### Camadas funcionais

- Geração e conferência: pipeline operacional atual.
- Historical Intelligence: inteligência histórica de combinações.
- Analytics Intelligence: visual analytics institucional.
- ML Intelligence: score ML interpretável com reranking.
- ML Governance: governança de modelos, experimentos e snapshots.
- Observability: logs, auditoria e saúde cloud.
- Reports Engine: PDF, CSV e snapshots institucionais.

## Dashboard

O dashboard institucional é operado por `dashboard/admin_app.py`.
Ele concentra a navegação lateral premium e a experiência analítica da plataforma.

Sessões principais:

- Criar Jogos
- Resultados Passados
- Historical Intelligence
- Analytics Intelligence
- ML Intelligence
- ML Governance
- Observability
- Reports Engine
- Meus Testes
- Relatórios

## Machine Learning

O ML da LotoIA é interpretável e controlado.
Ele trabalha com:

- score ML por jogo;
- reranking supervisionado;
- walk-forward validation;
- snapshots de modelo;
- experiment tracking;
- feature governance.

O modelo é auxiliar e não substitui a inteligência estatística principal.

## Governança

A governança institucional cobre:

- rastreabilidade de geração e conferência;
- histórico de leads;
- histórico de combinações;
- versionamento de modelos;
- snapshots;
- auditoria operacional;
- observabilidade cloud.

## Observability

A observabilidade institucional registra:

- eventos de geração;
- eventos de conferência;
- eventos de ML;
- eventos de relatórios;
- eventos de snapshots;
- trilha de auditoria;
- saúde operacional e runtime.

## Cloud Runtime

A LotoIA preserva compatibilidade com Streamlit Cloud.

Características mantidas:

- runtime estável;
- SQLite operacional;
- persistência local compatível;
- relatórios exportáveis;
- snapshots institucionais;
- logs e auditoria.

## Compatibilidade

Este documento descreve a plataforma sem alterar:

- runtime;
- geração;
- conferência;
- analytics;
- ML;
- observability;
- persistência;
- estrutura `src/`.

