# Politica de ML Assistivo LotoIA

## Status

`POLITICA_ML_ASSISTIVO_FORMALIZADA`

Documento oficial. Ativo e obrigatorio para toda camada supervisionada, experimental
ou operacional que utilize Machine Learning na plataforma.

## Proposito

Formalizar que a LotoIA pode utilizar ML como camada auxiliar incremental, sem permitir
que modelos preditivos substituam a governanca institucional, a Lei 15 ou os mecanismos
auditaveis de ranking.

Esta politica nao altera regras soberanas de geracao. Ela define limites, usos permitidos,
obrigacoes de auditoria e criterios de promocao para qualquer contribuicao de ML.

## Posicionamento oficial

A LotoIA e uma plataforma estatistica estrutural com assistencia supervisionada incremental.

Machine Learning na LotoIA:

- e auxiliar, nao central;
- e incremental, nao substitutivo;
- e interpretavel, nao opaco;
- e comparavel, nao autonomo;
- e reversivel, nao irreversivel por padrao;
- e temporalmente validado, nao treinado sem walk-forward.

ML nao define a verdade operacional da plataforma. A estatistica estrutural, o benchmark
temporal e a governanca institucional permanecem soberanas.

## Regras obrigatorias

### Regra 1 - ML nao substitui a Lei 15

Nenhum modelo, score supervisionado, rerank, calibrador ou camada de IA pode substituir,
redefinir, relaxar ou contornar a Lei 15 como comando soberano da geracao institucional.

ML pode anotar, comparar, diagnosticar ou reranquear candidatos apenas como camada
subordinada. A selecao final soberana continua governada pela Lei 15 e pelos guardrails
institucionais vigentes.

### Regra 2 - ML nao altera regras soberanas automaticamente

Nenhum fluxo de ML pode:

- recalibrar leis automaticamente;
- promover pesos sem aprovacao institucional;
- mutar politicas em runtime silencioso;
- substituir ADRs, contratos ou guardrails por aprendizado online nao auditado.

Toda alteracao de regra soberana exige decisao arquivada, ADR ou processo institucional
explicito. ML observa e auxilia; nao comanda evolucao normativa.

### Regra 3 - ML nao gera jogos sem rastreabilidade

Nenhuma saida assistida por ML pode existir sem rastreabilidade minima:

- identificador de experimento ou execucao;
- versao de modelo e de dataset;
- modo de ativacao (`ml_enabled`, politica, manifesto);
- origem das features;
- janela temporal e cutoff de features;
- assinatura ou identificador do jogo/candidato afetado;
- papel do ML na saida (`annotate`, `rerank`, `diagnose`, `validate`).

Geracao institucional sem trilha auditavel e proibida.

### Regra 4 - ML nao opera como motor preditivo central

A LotoIA nao e um sistema de previsao deterministica de concursos.

E proibido posicionar ML como:

- motor principal de escolha de dezenas;
- substituto do ranking hibrido oficial;
- fonte unica de priorizacao;
- mecanismo de previsao do proximo concurso sem benchmark comparativo;
- decisor autonomo de promocao operacional.

O valor institucional permanece em priorizacao estrutural, ranking probabilistico e
validacao cientifica.

### Regra 5 - Usos permitidos de ML

ML pode auxiliar, de forma subordinada e auditavel:

- ranking e rerank comparavel de candidatos;
- analise estrutural e estatistica complementar;
- clusterizacao e segmentacao diagnostica;
- deteccao de drift, anomalias e desvios;
- validacao temporal e benchmarking supervisionado;
- explicabilidade de contribuicoes por feature;
- diagnostico operacional e leitura institucional assistida.

Esses usos devem permanecer separados da geracao soberana e do comando normativo.

### Regra 6 - Explicabilidade, testabilidade, reversibilidade e auditabilidade

Toda contribuicao de ML deve ser:

- **explicavel:** attribution, coeficientes, pesos ou contrato de features visivel;
- **testavel:** coberta por testes automatizados e benchmarks reprodutiveis;
- **reversivel:** rollback de modelo, snapshot ou politica sem quebra estrutural;
- **auditavel:** persistencia ou artefato rastreavel em `experiments/`, registry ou memoria institucional.

Modelos opacos, AutoML nao governado e deep learning sem contrato explicito ficam fora do
perimetro institucional ate nova decisao arquivada.

### Regra 7 - Validacao temporal obrigatoria

Toda evolucao supervisionada deve respeitar governanca temporal:

```text
feature_cutoff_contest < scoring_contest
feature_cutoff_contest < label_contest, quando label existir
```

Walk-forward validation e obrigatorio antes de qualquer uso governado em avaliacao,
benchmark ou promocao experimental. Leakage temporal invalida o experimento.

### Regra 8 - Promocao institucional exige relatorio comparativo

Nenhum modelo, score, calibrador ou camada ML pode ser promovido a componente
institucional sem:

- relatorio comparativo contra baseline estatistico oficial;
- evidencia de validacao temporal;
- manifesto/versionamento de modelo e dataset;
- analise de reversibilidade;
- decisao arquivada em ADR ou registro institucional.

Promocao sem comparativo e bloqueada por politica.

## Matriz de conformidade

| Pergunta institucional | Resposta exigida |
|------------------------|------------------|
| ML substitui a Lei 15? | Nao |
| ML altera regra soberana sozinho? | Nao |
| ML gera sem rastreio? | Nao |
| ML e motor preditivo central? | Nao |
| ML auxilia ranking/analise com contrato? | Sim, se governado |
| Ha explicabilidade e rollback? | Sim |
| Ha validacao temporal? | Sim |
| Houve relatorio comparativo para promocao? | Obrigatorio |

## Perimetro tecnico de referencia

Modulos e contratos que devem respeitar esta politica:

- `src/lotoia/ml/` — camada oficial de ML governado (`score_ml`, rerank, explainability)
- `src/lotoia/experiments/` — datasets, manifests, temporal governance
- `experiments/registry/` — rastreabilidade experimental
- `src/lotoia/benchmark/` — referencia comparativa principal
- `src/lotoia/generator/` — anexacao auxiliar sem substituicao do ranking oficial
- `dashboard/institutional_app.py` — exibicao e diagnostico sem recalibracao soberana

## Relacao com decisoes arquivadas

Esta politica consolida e operacionaliza, sem contradizer:

- `ADRs/ADR_001_PARADIGMA_HIBRIDO.md`
- `ADRs/ADR_002_ML_GOVERNANCE.md`
- `ADRs/ADR_004_RERANK_CONSOLIDATION.md`
- `ADRs/ADR_005_TEMPORAL_GOVERNANCE.md`
- `ADRs/ADR_006_TEMPORAL_BENCHMARK.md`
- `ADRs/ADR_007_SUPERVISED_DATASET_GOVERNANCE.md`
- `ADRs/ADR_008_INCREMENTAL_SCORE_ML.md`
- `ADRs/ADR-023-SCIENTIFIC-ML-GOVERNANCE.md`
- `docs/adr/ADR-042-POLITICA-ML-ASSISTIVO.md`

## Criterio de bloqueio

Qualquer proposta de ML que viole uma ou mais regras obrigatorias deve ser classificada como:

`ML_ASSISTIVO_NAO_CONFORME`

e nao pode avancar para runtime institucional, painel soberano ou promocao operacional.

## Registro institucional

A LotoIA pode evoluir com ML assistivo.

A LotoIA nao pode abdicar de governanca, Lei 15, ranking auditavel ou validacao temporal
em favor de modelos preditivos.

**Status final:** `POLITICA_ML_ASSISTIVO_FORMALIZADA`
