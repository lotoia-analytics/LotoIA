# Benchmark Temporal Reproduzivel

## Objetivo

Este documento define a camada minima de reproducibilidade para o benchmark temporal
cientifico do LotoIA.

## Artefatos Obrigatorios

- ADR de referencia;
- manifest de benchmark temporal;
- snapshot versionado de dataset;
- split temporal explicito;
- referencia ao benchmark estatistico;
- politica de seed;
- comando de reexecucao;
- proibicoes de ML real na baseline.

## Snapshot de Dataset

O snapshot inicial usa o historico oficial em:

```text
data/raw/historico_lotofacil.csv
```

O hash canonico e calculado sobre concursos carregados e validados pelo loader oficial,
ordenados por concurso.

## Temporal Baseline

O baseline inicial declara:

```text
train_start <= train_end < test_start <= test_end
```

Nenhuma estatistica futura pode ser usada para construir features historicas.

## Walk-Forward Futuro

Benchmarks supervisionados futuros devem usar janelas expansivas de treino e janelas de
teste futuras. A declaracao existe nesta etapa, mas nenhum modelo real e treinado.

## Comparabilidade

Um experimento futuro so e comparavel quando:

- referencia o mesmo snapshot ou justifica novo snapshot;
- declara split temporal compativel;
- registra manifest completo;
- nao declara `score_ml`;
- nao declara modelo treinado;
- nao altera ranking estatistico ou gerador principal.
