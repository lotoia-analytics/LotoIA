# ADR 003 - Cloud Runtime

## Contexto

A LotoIA é distribuída com suporte a Streamlit Cloud e precisa manter execução estável em ambiente leve.
O runtime precisa preservar a experiência institucional sem depender de infraestrutura adicional complexa.

## Problema

Era necessário garantir:

- compatibilidade com Streamlit Cloud;
- SQLite operacional;
- persistência local estável;
- comportamento previsível em deploy;
- suporte a relatórios, logs e snapshots.

## Decisão

Manter o runtime cloud atual com:

- Streamlit como interface principal;
- SQLite como persistência operacional;
- artefatos em `reports/`;
- logs e auditoria persistidos localmente;
- sem migração forçada para serviços externos.

## Alternativas Consideradas

1. Migrar para um backend distribuído.
2. Adotar banco gerenciado externo.
3. Introduzir fila assíncrona e orquestração adicional.

Essas alternativas foram descartadas por aumentarem a fragilidade do deploy e desnecessariamente alterarem a operação atual.

## Impacto Arquitetural

- runtime permanece simples e previsível;
- persistência continua coerente com a implantação atual;
- observability e snapshots permanecem compatíveis com a plataforma cloud;
- o dashboard mantém o fluxo já validado.

## Riscos

- limitação natural de SQLite em cenários concorrentes;
- dependência da disciplina de escrita em disco;
- necessidade de manter artefatos enxutos.

## Benefícios

- deploy mais estável;
- menor complexidade operacional;
- manutenção simplificada;
- compatibilidade com o fluxo atual;
- menor risco de regressão.

## Consequências Futuras

- novas funcionalidades cloud devem preservar o mesmo modelo leve;
- logs e snapshots precisam continuar auditáveis;
- qualquer mudança de runtime exige nova ADR.

