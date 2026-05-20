# ADR 005 - Institutional Governance

## Contexto

A LotoIA evoluiu para uma plataforma com dashboard institucional, lead intelligence, historical intelligence, reports engine, analytics intelligence, ML intelligence, ML governance e observability.

## Problema

A maturidade da plataforma exigia uma governança institucional explícita para:

- rastrear decisões arquiteturais;
- garantir temporal safety;
- preservar modularidade;
- manter snapshots e artefatos;
- documentar a evolução operacional.

## Decisão

Instituir uma governança baseada em:

- documentação formal;
- ADRs para decisões relevantes;
- experiment tracking para ML;
- snapshots para relatórios e modelos;
- trilha de auditoria para ações operacionais;
- observabilidade institucional contínua.

## Alternativas Consideradas

1. Crescimento informal sem documentação.
2. Governança apenas por código.
3. Registros dispersos em notas e relatórios soltos.

Essas opções foram rejeitadas porque reduzem rastreabilidade e aumentam o risco de regressão.

## Impacto Arquitetural

- decisões passam a ser auditáveis;
- a evolução fica documentada;
- o histórico institucional pode ser revisitado;
- o modelo de operação torna-se mais robusto.

## Riscos

- manutenção documental insuficiente;
- inconsistência entre documentação e implementação;
- excesso de dispersão sem padrão comum.

## Benefícios

- clareza institucional;
- rastreabilidade;
- auditabilidade;
- previsibilidade de evolução;
- alinhamento entre arquitetura e operação.

## Consequências Futuras

- novas mudanças estruturais devem gerar ADR;
- novos modelos e dashboards precisam ser documentados;
- a plataforma permanece governada por princípios explícitos e verificáveis.

