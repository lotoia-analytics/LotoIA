# ML Governance

## Official Purpose

The ML layer in LotoIA is auxiliary, interpretable, and temporally governed.
It exists to improve ranking support, not to replace structural statistical analysis.

## `score_ml`

`score_ml` is the operational machine-learning score assigned to a candidate game.

Properties:

- deterministic and interpretable;
- built from explicit features;
- bounded to a 0-100 scale;
- attached to existing candidate games;
- compatible with reranking.

## Feature Governance

The feature pipeline is explicitly controlled and leakage-safe.
Typical feature families:

- frequency;
- delay;
- incidence;
- patterns;
- odd/even balance;
- sum behavior;
- historical context.

Feature governance requires:

- documented feature versions;
- contribution tracking;
- model version tracking;
- training context capture.

## Reranking

Reranking is applied after structural generation.
The rerank step:

- scores candidates;
- orders by ML score;
- preserves the underlying statistical candidate set;
- never replaces the base scientific logic.

## Walk-Forward Validation

All supervised validation must remain temporally safe.

Requirements:

- train windows precede test windows;
- no future leakage;
- time-ordered splits;
- historical evaluation remains reproducible.

## Snapshots

ML snapshots should preserve:

- model version;
- feature schema version;
- calibration payload;
- training summary;
- attribution;
- timestamps.

## Experiment Tracking

Experiments should store:

- calibration history;
- metrics;
- temporal validation results;
- model comparisons;
- artifact locations;
- audit references.

## Temporal Safety

The ML layer must never:

- use future contests as features;
- leak labels into features;
- train on post-label information;
- bypass walk-forward governance.

## Governance Position

ML is a governed assistant layer.
It remains subordinate to statistical structure, benchmark discipline, and temporal validation.

