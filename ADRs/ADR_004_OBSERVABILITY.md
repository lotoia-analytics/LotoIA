# ADR 004 - Observability

## Contexto

A LotoIA passou a registrar geração, conferência, ML, relatórios, snapshots e auditoria institucional.
Era necessário consolidar a observabilidade como função governada da plataforma.

## Problema

Sem observabilidade institucional, a plataforma não teria:

- rastreabilidade operacional;
- métricas de saúde;
- trilha de auditoria;
- visibilidade de falhas;
- histórico de eventos relevantes.

## Decisão

Adotar uma camada de observability leve e institucional com:

- logs operacionais em SQLite;
- trilha de auditoria para ações e artefatos;
- métricas runtime e cloud health;
- eventos recentes por tipo;
- integração no dashboard.

## Alternativas Consideradas

1. Uso exclusivo de logs externos.
2. Monitoramento distribuído com ferramentas adicionais.
3. Ausência de persistência histórica de eventos.

Essas opções foram rejeitadas por complexidade, custo e perda de portabilidade.

## Impacto Arquitetural

- surgimento de uma camada formal de logs e auditoria;
- melhor visibilidade dos processos institucionais;
- preservação da simplicidade do runtime;
- compatibilidade com a persistência atual.

## Riscos

- crescimento indevido de tabelas de logs;
- excesso de informação não filtrada;
- necessidade de manter consultas leves no dashboard.

## Benefícios

- rastreabilidade completa;
- diagnóstico mais rápido;
- auditoria institucional;
- saúde operacional visível;
- suporte a governança cloud.

## Consequências Futuras

- novas ações operacionais devem ser registradas;
- os logs se tornam insumo para governança;
- snapshots e exports passam a integrar a trilha institucional.

