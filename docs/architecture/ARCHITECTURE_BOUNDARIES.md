# Architecture Boundaries

## Objetivo

Este documento define as fronteiras institucionais do LotoIA durante o
FREEZE ARQUITETURAL INSTITUCIONAL V1.

Ele nao cria novas features, nao altera runtime e nao modifica logica cientifica. Sua funcao
e impedir overlap, preservar modularidade e orientar reconciliacao futura entre sandbox e
core.

---

## Fonte de Verdade Arquitetural

O namespace oficial do sistema e:

```text
src/lotoia
```

Qualquer logica de negocio reutilizavel, validada e institucional deve viver no namespace
oficial. Estruturas fora dele podem existir como interface, operacao, persistencia,
experimento, relatorio, historico ou sandbox, mas nao devem se tornar centros paralelos de
decisao cientifica.

---

## Boundaries por Dominio

### Estatistica Estrutural

Boundary oficial:

```text
src/lotoia/statistics
```

Responsabilidades:

- calculos estatisticos estruturais;
- combinacoes, frequencias, padroes e metricas interpretaveis;
- scoring estatistico e hibrido quando nao supervisionado;
- logica temporal estatistica sem leakage.

Restricoes:

- nao acessar persistencia diretamente quando houver loader ou repositorio adequado;
- nao gerar artefatos finais de relatorio;
- nao incorporar treinamento supervisionado;
- nao depender de dashboard, backend ou scripts.

### Validacao Temporal e Benchmark

Boundaries oficiais:

```text
src/lotoia/backtesting
src/lotoia/benchmark
src/lotoia/experiments
experiments
```

Responsabilidades:

- backtesting temporalmente valido;
- benchmark cientifico reproduzivel;
- governanca temporal;
- registries, manifestos e datasets versionados.

Restricoes:

- proibido usar estatisticas globais que incluam futuro;
- proibido misturar treino, validacao e teste sem corte temporal;
- proibido substituir benchmark por avaliacao pontual.

### Machine Learning Incremental

Boundary oficial:

```text
src/lotoia/ml
```

Responsabilidades:

- assistencia supervisionada incremental;
- score auxiliar interpretavel;
- rerank supervisionado comparavel;
- features supervisionadas governadas;
- avaliacao compativel com walk-forward.

Restricoes:

- ML nao substitui estatistica estrutural;
- ML nao define sozinho a decisao final;
- modelos opacos nao sao aceitos sem ADR especifico;
- todo dataset e modelo deve ser versionado;
- qualquer validacao supervisionada deve ser temporalmente correta.

### Dados e Persistencia

Boundaries oficiais:

```text
src/lotoia/data
src/lotoia/database
src/lotoia/storage
src/lotoia/persistence
data
```

Responsabilidades:

- carregamento de dados;
- repositorios;
- armazenamento de artefatos;
- sincronizacao e persistencia;
- dados brutos, derivados e institucionais.

Restricoes:

- nao conter logica estatistica;
- nao conter decisao de scoring;
- nao treinar modelos;
- nao gerar benchmark por conta propria;
- nao reclassificar dados temporais sem manifestos.

### Interfaces e Operacao

Boundaries externos ao core:

```text
backend
dashboard
scripts
lotoia_runtime.py
```

Responsabilidades:

- exposicao operacional;
- execucao de comandos;
- visualizacao;
- orquestracao de fluxos existentes.

Restricoes:

- nao conter logica cientifica primaria;
- nao duplicar regras de scoring;
- nao criar atalhos que ignorem benchmark, anti-leakage ou registries;
- nao virar fonte de verdade arquitetural.

### Governanca, Observabilidade e Confiabilidade

Boundaries oficiais ou condicionais:

```text
src/lotoia/governance
src/lotoia/observability
src/lotoia/reliability
```

Responsabilidades:

- politicas institucionais;
- registros de decisao;
- telemetria, logs e metricas;
- estabilidade operacional.

Restricoes:

- governanca nao deve alterar comportamento cientifico sem ADR;
- observabilidade nao deve produzir decisao estatistica;
- confiabilidade nao deve mascarar falhas cientificas ou temporais.

---

## Boundaries de Artefatos

```text
ADRs         decisoes arquiteturais
docs         documentacao institucional
experiments  governanca experimental e versionamento
reports      saidas e relatorios
snapshots    marcos institucionais
tests        validacao automatizada
```

Essas areas nao devem receber logica runtime central.

---

## Regra Anti-Overlap

Um modulo so pode ter uma responsabilidade primaria. Quando uma responsabilidade parecer
pertencer a dois modulos, a decisao deve seguir esta ordem:

1. preservar o core estatistico em `src/lotoia/statistics`;
2. manter persistencia separada de logica cientifica;
3. manter ML como camada auxiliar;
4. manter experimentos versionados fora do runtime central;
5. registrar decisao em ADR antes de expandir fronteiras.

---

## Reconciliacao Sandbox x Core

Estruturas paralelas ou historicas devem ser tratadas como sandbox ate classificacao formal.

Exemplos de superficies que exigem cuidado:

```text
lotoia
src/database
src/statistics
src/ingestion
notebooks
diagnostico
audit
audit_full
backups
codex_context
```

Elas nao devem ser promovidas, migradas ou removidas durante o freeze sem plano institucional.
Qualquer reconciliacao futura deve:

- declarar origem e destino;
- mapear imports afetados;
- preservar pytest;
- validar ausencia de leakage;
- produzir benchmark quando comportamento cientifico for afetado;
- registrar resultado em ADR ou snapshot.
