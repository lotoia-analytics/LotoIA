# ADR 008 - Incremental Interpretable score_ml

## Status

Aceito

---

## Contexto

Os ADRs 001 a 007 consolidaram o LotoIA como plataforma estatistica estrutural com
assistencia supervisionada incremental. As etapas anteriores proibiram `score_ml` enquanto
faltavam governanca temporal, benchmark cientifico e governanca de dataset supervisionado.

Com essas bases criadas, o projeto pode introduzir a primeira camada oficial de `score_ml`
desde que ela permaneca auxiliar, interpretavel, comparavel ao benchmark estatistico e
temporalmente auditavel.

---

## Decisao

O LotoIA adota `score_ml` como camada incremental auxiliar de rerank supervisionado
interpretavel.

`score_ml`:

- nao substitui o ranking estatistico;
- nao substitui o score hibrido principal;
- nao substitui o benchmark oficial;
- pode anotar candidatos com score supervisionado auxiliar;
- pode produzir rerank supervisionado somente como saida comparavel;
- deve declarar feature attribution;
- deve declarar calibracao supervisionada;
- deve ser validado por politica temporal e walk-forward;
- deve permanecer simples, auditavel e reprodutivel.

---

## Implementacao Inicial

A primeira implementacao oficial usa baseline linear interpretavel:

- features candidatas estaticas ou ja produzidas pelo fluxo estatistico;
- coeficientes explicitos;
- score normalizado entre 0 e 100;
- attribution por contribuicao linear de cada feature;
- calibracao supervisionada simples por covariancia nao negativa quando linhas governadas
  estiverem disponiveis;
- versao de modelo e versao de schema de features declaradas.

Nao ha deep learning, AutoML, modelo opaco ou tuning agressivo.

---

## Integracao Operacional

O generator pode anexar `score_ml` quando `ml_enabled=true`, mas continua ordenando pelos
criterios oficiais de ranking hibrido.

O rerank supervisionado explicito fica separado para benchmark e comparabilidade, evitando
substituicao acidental do mecanismo estatistico principal.

---

## Governanca Temporal

Toda linha supervisionada usada por `score_ml` deve declarar:

```text
feature_cutoff_contest < scoring_contest
feature_cutoff_contest < label_contest, quando label existir
```

Validacao supervisionada deve ser walk-forward compativel. O benchmark estatistico continua
sendo a referencia principal de comparacao.

---

## Artefatos Oficiais

Logica reutilizavel:

```text
src/lotoia/ml/score_ml.py
src/lotoia/experiments/supervised_scoring.py
```

Artefatos institucionais:

```text
experiments/supervised_scoring/
```

Relatorio tecnico:

```text
reports/SCORE_ML_INCREMENTAL_REPORT.md
```

---

## Riscos Residuais

- A baseline linear pode capturar apenas relacoes fracas e instaveis.
- O valor cientifico depende de datasets supervisionados materializados sem leakage.
- Comparacoes futuras precisam ser executadas por walk-forward real, nao por avaliacao
  aleatoria ou global.
- O score auxiliar pode ser mal interpretado como previsao se dashboards ou relatorios nao
  preservarem sua natureza incremental.

---

## Status Institucional

Este ADR libera a primeira camada oficial de `score_ml` incremental interpretavel do LotoIA,
mantendo a primazia da estatistica estrutural e do benchmark temporal cientifico.
