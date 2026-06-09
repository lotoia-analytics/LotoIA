# ADR-042 - Politica de ML Assistivo

## Status

Accepted

## Contexto

O ecossistema LotoIA ja possui:

- paradigma hibrido estatistico incremental (ADR 001);
- governanca de ML e `score_ml` interpretavel (ADR 002, ADR 008);
- consolidacao de rerank sem substituicao do ranking oficial (ADR 004);
- governanca temporal, benchmark e datasets supervisionados (ADR 005 a 007);
- camada cientifica de ML governance (ADR 023).

Faltava um documento unico, operacional e auditavel que formalize o papel assistivo do ML
sem ambiguidade frente a Lei 15, a governanca institucional e os mecanismos de ranking.

## Decisao

Adotar oficialmente a **Politica de ML Assistivo LotoIA** em
`docs/governance/POLITICA_ML_ASSISTIVO.md` como contrato normativo para qualquer uso de ML
na plataforma.

As oito regras obrigatorias passam a valer como gate institucional:

1. ML nao substitui a Lei 15.
2. ML nao altera regras soberanas automaticamente.
3. ML nao gera jogos sem rastreabilidade.
4. ML nao opera como motor preditivo central.
5. ML pode auxiliar ranking, analise, clusterizacao, diagnostico e validacao.
6. Toda contribuicao de ML deve ser explicavel, testavel, reversivel e auditavel.
7. Toda evolucao por ML deve passar por validacao temporal.
8. Nenhum modelo pode ser promovido a componente institucional sem relatorio comparativo.

## Consequencias

Positivas:

- fronteira clara entre estatistica soberana e assistencia supervisionada;
- criterio unico para aprovar ou bloquear experimentos ML;
- alinhamento entre codigo, testes, ADRs e governanca operacional.

Negativas / trade-offs:

- maior rigor documental para novas propostas de ML;
- promocao de modelos mais lenta e dependente de evidencia comparativa.

## Conformidade

Modulos ML, experimentos supervisionados, dashboards e pipelines de promocao devem
referenciar esta politica em revisoes arquiteturais futuras.

Status institucional esperado:

`POLITICA_ML_ASSISTIVO_FORMALIZADA`
