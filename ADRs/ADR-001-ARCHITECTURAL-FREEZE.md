# ADR-001 - Architectural Freeze Institucional V1

## Status

Aceito

---

## Contexto

O LotoIA consolidou-se como uma plataforma estatistica estrutural com assistencia
supervisionada incremental. O valor institucional do sistema esta na combinacao de:

- engenharia estatistica estrutural;
- validacao temporal;
- benchmark cientifico;
- interpretabilidade;
- governanca experimental;
- reproducibilidade de dados, modelos e relatorios.

A evolucao recente criou areas oficiais maduras em `src/lotoia`, mas tambem deixou
superficies paralelas, artefatos historicos, sandbox operacional e modulos auxiliares que
podem gerar ambiguidade arquitetural se evoluirem sem controle.

Este ADR estabelece um freeze arquitetural institucional para impedir crescimento horizontal
descontrolado, preservar a modularidade atual e preparar uma reconciliacao disciplinada entre
sandbox e core.

---

## Decisao

O LotoIA entra em **FREEZE ARQUITETURAL INSTITUCIONAL V1**.

Durante este freeze:

- nenhum modulo runtime novo deve ser criado sem ADR de expansao;
- nenhum modulo existente deve ter sua responsabilidade ampliada sem justificativa formal;
- nenhuma logica cientifica deve ser alterada por motivo de reorganizacao arquitetural;
- nenhuma feature deve ser adicionada como parte deste freeze;
- estruturas paralelas devem ser classificadas antes de qualquer migracao;
- qualquer reconciliacao entre sandbox e core deve preservar compatibilidade com pytest atual;
- benchmarking, validacao temporal e anti-leakage permanecem obrigatorios.

O namespace oficial continua sendo:

```text
src/lotoia
```

As demais superficies sao documentadas como areas externas, transitorias, experimentais ou
de suporte, conforme a classificacao oficial.

---

## Boundaries Institucionais

O freeze define os seguintes limites:

- `src/lotoia/statistics` contem logica estatistica estrutural.
- `src/lotoia/backtesting` e `src/lotoia/benchmark` contem validacao historica e comparacao.
- `src/lotoia/ml` contem apenas assistencia supervisionada incremental e interpretavel.
- `src/lotoia/data`, `src/lotoia/database`, `src/lotoia/storage` e `src/lotoia/persistence`
  nao devem incorporar logica cientifica.
- `experiments` governa manifestos, datasets versionados e registries experimentais.
- `reports` contem saidas institucionais e nao deve ser fonte de verdade runtime.
- `tests` valida comportamento e compatibilidade.
- `dashboard`, `backend`, `scripts` e `notebooks` sao superficies de interface, operacao ou
  exploracao, nao centros de logica cientifica.

---

## Politica de Freeze

Sao permitidas durante o freeze:

- documentacao institucional;
- classificacao de modulos;
- ADRs;
- inventario de fronteiras;
- ajustes de governanca que nao alterem runtime;
- testes existentes para confirmar compatibilidade.

Sao proibidas durante o freeze:

- novas features;
- novos algoritmos cientificos;
- mudancas em scoring, estatistica, ML, benchmark ou backtesting;
- migracoes de import sem plano formal;
- fusao informal entre sandbox e core;
- duplicacao de responsabilidade entre modulos;
- uso de dados futuros em qualquer fluxo temporal.

---

## Consequencias

### Positivas

- estabiliza a arquitetura oficial;
- reduz risco de overlap;
- cria base para reconciliacao controlada de estruturas paralelas;
- protege a logica cientifica existente;
- preserva compatibilidade com a suite pytest atual;
- evita expansao horizontal sem governanca.

### Custos

- novas capacidades ficam bloqueadas ate aprovacao institucional;
- migracoes exigem classificacao previa;
- experimentos precisam permanecer isolados ate graduacao formal;
- refatoracoes estruturais exigem plano, benchmark e validacao temporal quando afetarem
  comportamento cientifico.

---

## Artefatos Derivados

Este ADR e acompanhado por:

```text
docs/architecture/ARCHITECTURE_BOUNDARIES.md
docs/architecture/MODULE_CLASSIFICATION.md
docs/architecture/EXPANSION_POLICY.md
```

---

## Status Institucional

Este ADR torna-se a referencia oficial do freeze arquitetural V1 do LotoIA. Ele nao altera
runtime, nao expande modulos e nao modifica logica cientifica. Sua funcao e estabelecer a
governanca estrutural que orientara futuras reconciliacoes, expansoes e consolidacoes.
