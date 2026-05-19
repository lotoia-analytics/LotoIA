# ADR 005 - Governanca Cientifica Temporal

## Status
Aceito

---

## Contexto

Os ADRs 001, 002, 003 e 004 estabeleceram que o LotoIA e uma plataforma estatistica
estrutural com assistencia supervisionada incremental, que o namespace oficial e
`src/lotoia`, que imports ambiguos devem ser controlados e que o rerank supervisionado
permanece apenas como placeholder sem `score_ml`.

A evolucao supervisionada exige formalizacao temporal antes de qualquer treinamento real.
Sem essa camada, o projeto fica exposto a leakage temporal, benchmarks nao reproduziveis,
datasets supervisionados ambiguos e perda de rastreabilidade cientifica.

---

## Decisao

O LotoIA adota governanca temporal formal como prerequisito para qualquer experimento
supervisionado.

A partir deste ADR:

- toda divisao treino/teste deve ser temporal e explicita;
- validacao walk-forward passa a ser o desenho oficial para modelos supervisionados futuros;
- features supervisionadas devem declarar o concurso de corte;
- labels supervisionados devem ocorrer depois do corte de features;
- manifestos experimentais devem declarar dataset, codigo, benchmark e split temporal;
- qualquer uso de `score_ml`, inferencia real ou treinamento permanece proibido nesta etapa.

---

## Regras Arquiteturais

### Namespace Oficial

Toda logica reutilizavel de governanca temporal deve residir no namespace oficial:

```text
src/lotoia
```

Estruturas fora de `src/lotoia` podem armazenar documentos, manifestos, outputs e registros,
mas nao devem conter logica operacional oficial.

### Separacao de Responsabilidades

- `src/lotoia/experiments`: validadores e primitivas de governanca experimental.
- `experiments/registry`: manifestos, schemas e indice institucional de experimentos.
- `docs`: documentacao cientifica e arquitetural.
- `reports`: relatorios tecnicos gerados.

### Proibicoes Nesta Etapa

- treinamento supervisionado real;
- inferencia supervisionada real;
- criacao de `score_ml`;
- alteracao do benchmark engine;
- alteracao do backtester;
- alteracao do ranking hibrido;
- alteracao do scoring estatistico.

---

## Politica Temporal

Um split temporal valido deve obedecer:

```text
train_start <= train_end < test_start <= test_end
```

Um registro supervisionado valido deve obedecer:

```text
feature_cutoff_contest < label_contest
```

Uma validacao walk-forward deve usar janelas de treino historicas e janelas de teste futuras,
sem reprocessamento de estatisticas com informacao posterior ao corte.

---

## Consequencias

### Positivas

- reduz risco de leakage temporal;
- cria base verificavel para datasets supervisionados;
- torna experimentos rastreaveis e reproduziveis;
- preserva a primazia do benchmark temporal;
- mantem ML como camada auxiliar futura.

### Negativas

- adiciona disciplina documental obrigatoria;
- aumenta custo de preparacao antes de qualquer modelo;
- exige versionamento consistente de datasets e manifestos.

---

## Impacto

Este ADR nao altera comportamento operacional atual. Ele cria apenas base documental,
validadores minimos e estrutura de registry para evolucao supervisionada futura.
