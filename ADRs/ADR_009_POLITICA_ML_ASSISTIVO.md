# ADR 009 - Politica de ML Assistivo

## Status

Aceito

---

## Contexto

As decisoes ADR 001 a 008 e ADR-023 consolidaram o LotoIA como plataforma estatistica
estrutural com assistencia supervisionada incremental.

Ainda assim, era necessario um artefato normativo unico que responda, sem ambiguidade:

- o que ML pode fazer na LotoIA;
- o que ML nao pode fazer;
- como promover ou bloquear evolucoes supervisionadas;
- como preservar a soberania da Lei 15 e do ranking auditavel.

## Decisao

Formalizar a **Politica de ML Assistivo LotoIA**:

- documento canonico: `docs/governance/POLITICA_ML_ASSISTIVO.md`
- ADR de registro: `docs/adr/ADR-042-POLITICA-ML-ASSISTIVO.md`

Machine Learning permanece permitido apenas como camada auxiliar incremental.

## Regras institucionais

1. ML nao substitui a Lei 15.
2. ML nao altera regras soberanas automaticamente.
3. ML nao gera jogos sem rastreabilidade.
4. ML nao opera como motor preditivo central.
5. ML pode auxiliar ranking, analise, clusterizacao, diagnostico e validacao.
6. Toda contribuicao de ML deve ser explicavel, testavel, reversivel e auditavel.
7. Toda evolucao por ML deve passar por validacao temporal.
8. Nenhum modelo pode ser promovido a componente institucional sem relatorio comparativo.

## Implementacao

Esta ADR nao introduz novo runtime ML.

Ela estabelece o contrato normativo que deve ser respeitado por:

- `src/lotoia/ml/`
- `src/lotoia/experiments/`
- `experiments/registry/`
- benchmarks, reranks e qualquer proposta de promocao institucional

## Status esperado

`POLITICA_ML_ASSISTIVO_FORMALIZADA`
