# ADR 001 - Paradigma Híbrido Estatístico Incremental

## Status
Aceito

---

## Contexto

O projeto LotoIA evoluiu de sistema estatístico experimental para plataforma analítica modular com infraestrutura supervisionada preparada.

Foi identificado que:
- o núcleo de valor do sistema está na engenharia estatística estrutural;
- e não em modelos preditivos opacos.

A auditoria arquitetural consolidada demonstrou que:
- a base estatística já possui maturidade relevante;
- o benchmark temporal já oferece validação importante;
- o sistema híbrido atual possui boa interpretabilidade;
- e a expansão prematura de Machine Learning poderia aumentar:
  - acoplamento,
  - overfitting,
  - leakage temporal,
  - e perda de rastreabilidade científica.

Também foi identificado que:
- a previsibilidade causal em sistemas lotéricos é estruturalmente limitada;
- o valor do sistema está na priorização probabilística e estrutural;
- e não em “previsão determinística” de concursos.

---

## Decisão

O LotoIA adotará oficialmente:

- estatística estrutural como núcleo do sistema;
- benchmark temporal como mecanismo principal de validação;
- ranking híbrido interpretável como mecanismo de priorização;
- ML supervisionado apenas como camada incremental auxiliar.

Machine Learning:
- não substituirá o ranking estatístico;
- não atuará como mecanismo preditivo central;
- não poderá operar sem validação temporal;
- e deverá permanecer interpretável e cientificamente auditável.

A evolução supervisionada deverá:
- respeitar separação temporal;
- impedir leakage;
- utilizar walk-forward validation;
- possuir versionamento de datasets;
- possuir versionamento de modelos;
- possuir rastreabilidade experimental.

---

## Princípios Arquiteturais Oficiais

### 1. Estatística Estrutural é o Núcleo

A engenharia estatística do LotoIA passa a ser oficialmente considerada:
- o principal diferencial técnico do sistema;
- a principal fonte de interpretabilidade;
- e o núcleo matemático da plataforma.

---

### 2. ML é Incremental e Auxiliar

Modelos supervisionados:
- não substituem o sistema estatístico;
- não definem isoladamente o ranking;
- e devem atuar apenas como camada incremental de rerank probabilístico.

---

### 3. Benchmark é Fonte de Verdade

Toda evolução:
- estatística,
- estrutural,
- espacial,
- supervisionada,
deve obrigatoriamente ser validada por benchmark temporal reproduzível.

---

### 4. Leakage Temporal é Proibido

Nenhuma feature, score, dataset ou modelo poderá:
- utilizar informação futura;
- reutilizar estatísticas globais em contexto histórico;
- ou misturar treino e inferência temporal.

---

### 5. Interpretabilidade Tem Prioridade

O projeto prioriza:
- auditabilidade;
- rastreabilidade;
- consistência estatística;
- estabilidade temporal;
sobre:
- complexidade excessiva;
- modelos opacos;
- ou sofisticação artificial.

---

## Consequências

### Positivas

- maior robustez arquitetural;
- menor risco de overfitting;
- benchmark mais confiável;
- evolução científica sustentável;
- melhor integração entre estatística e ML;
- maior capacidade de auditoria;
- menor acoplamento futuro.

---

### Negativas

- evolução supervisionada mais lenta;
- maior necessidade de governança científica;
- necessidade de versionamento formal;
- maior disciplina arquitetural obrigatória.

---

## Impacto Arquitetural

Este ADR estabelece oficialmente que o LotoIA evolui como:

### Plataforma Estatística Estrutural com Assistência Supervisionada Incremental

E NÃO como:
- sistema preditivo baseado exclusivamente em IA;
- mecanismo de previsão determinística;
- ou plataforma ML-first.

---

## Roadmap Derivado

As próximas evoluções deverão priorizar:

1. Consolidação do scoring engine único;
2. Separação entre estatística e persistência;
3. Temporal Context API;
4. Spatial Intelligence Layer;
5. Walk-forward validation formal;
6. Governança experimental;
7. Registry supervisionado;
8. score_ml incremental interpretável.

---

## Status Institucional

Este ADR torna-se referência oficial para:
- decisões arquiteturais futuras;
- integração com Codex;
- snapshots estratégicos;
- benchmark científico;
- governança supervisionada;
- e evolução estrutural do projeto LotoIA.