# ADR 006 - Benchmark Temporal Cientifico

## Status
Aceito

---

## Contexto

Os ADRs 001 a 005 definiram o LotoIA como plataforma estatistica estrutural com
assistencia supervisionada incremental. Tambem definiram que o benchmark temporal e a
fonte principal de validacao cientifica e que qualquer evolucao supervisionada futura
depende de splits temporais, manifests, versionamento de datasets e rastreabilidade.

O projeto ja possui um benchmark operacional em `src/lotoia/benchmark`, mas faltava uma
camada institucional separada para declarar baselines temporais, snapshots de datasets,
manifests de comparabilidade e requisitos minimos de reproducibilidade.

---

## Decisao

O LotoIA adota o benchmark temporal cientifico como nucleo oficial de comparabilidade.

Esta consolidacao cria apenas infraestrutura cientifica incremental:

- registry formal de benchmark temporal;
- manifestos de baseline temporal;
- snapshot versionado de dataset historico;
- contrato inicial para benchmark supervisionado futuro;
- validadores reutilizaveis no namespace oficial `src/lotoia`;
- documentacao de reproducibilidade.

---

## Regras

- O benchmark operacional atual permanece inalterado.
- O backtester principal permanece inalterado.
- O gerador principal permanece inalterado.
- O ranking estatistico permanece inalterado.
- Nenhum `score_ml` sera criado nesta etapa.
- Nenhum modelo supervisionado real sera treinado nesta etapa.
- Nenhuma inferencia supervisionada real sera executada nesta etapa.

---

## Estrutura Oficial

Logica reutilizavel:

```text
src/lotoia/experiments/temporal_benchmark.py
```

Artefatos institucionais:

```text
experiments/temporal_benchmark/
```

Relatorios:

```text
reports/TEMPORAL_BENCHMARK_REPORT.md
```

---

## Politica de Comparabilidade

Um resultado futuro so sera comparavel ao baseline temporal se declarar:

- snapshot de dataset;
- versao de codigo;
- split temporal;
- politica de reproducibilidade;
- referencia ao benchmark estatistico;
- proibicao explicita de leakage temporal;
- ausencia de campos supervisionados proibidos durante a baseline.

---

## Consequencias

### Positivas

- formaliza o benchmark temporal como nucleo cientifico;
- reduz risco de comparacoes informais;
- cria base para walk-forward supervisionado futuro;
- preserva a separacao entre estatistica, persistencia e governanca experimental;
- melhora rastreabilidade institucional.

### Riscos Residuais

- o snapshot inicial ainda depende do historico CSV local;
- o benchmark supervisionado permanece declarativo;
- ainda nao ha registry de modelos porque modelos reais continuam fora de escopo;
- a reproducibilidade completa depende de ambiente Python e dependencias versionadas.

---

## Status Institucional

Este ADR consolida a primeira camada formal de benchmark temporal cientifico do LotoIA
sem alterar comportamento operacional atual.
