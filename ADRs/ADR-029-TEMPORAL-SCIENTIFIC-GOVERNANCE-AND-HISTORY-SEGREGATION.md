# ADR 029 - Temporal Scientific Governance and History Segregation

Status: Accepted

## Context

LotoIA has already stabilized the operational runtime, the shared PostgreSQL backend,
the dashboard lifecycle, and the institutional observability layer. The next scientific
phase requires a strict temporal governance boundary so that operational history, benchmark
history, validation history, expansion history, and supervised ML datasets are no longer
mixed in the same lineage.

Today the platform still mixes, in different degrees:

- generated games used for operations and reports,
- expansion flows used for growth and operational assistance,
- benchmark-like comparisons embedded in historical views,
- reconciliation and check flows used for validation,
- contest history used as the scientific timeline reference,
- ML-related ranking and feature snapshots used for supervised assistance.

This mixture is acceptable for the current operational runtime, but it is not acceptable
for scientific validation. The platform now needs a governed temporal contract that
separates operational evidence from benchmark evidence and from ML training evidence.

## Decision

LotoIA adopts a formal temporal scientific governance boundary with explicit segregation of
historical sources by purpose.

The official history layers are:

- `generation_events`: operational generation evidence;
- `check_events`: operational conference evidence;
- `expansion_events`: operational expansion evidence;
- `reconciliation_events`: operational reconciliation evidence;
- `workflow_events`: operational workflow evidence;
- `operational_logs`: runtime and platform operational evidence;
- `audit_trail`: institutional traceability evidence;
- `snapshots`: immutable runtime and institutional snapshots;
- `generated_games`: operational game outputs;
- `imported_contests`: contest ingestion and real contest references;
- `backtest_runs`: temporal benchmark / validation runs;
- `adaptive_governance_reports`: institutional governance artifacts;
- future scientific datasets: governed, versioned ML datasets only.

The platform must treat these layers as distinct scientific purposes, even when they
share persistence infrastructure.

## Current Classification

### Operational layer

Used for runtime execution and product behavior:

- `generation_events`
- `check_events`
- `expansion_events`
- `reconciliation_events`
- `workflow_events`
- `operational_logs`
- `audit_trail`
- `generated_games`

### Benchmark and scientific validation layer

Used for reproducible temporal evaluation:

- `backtest_runs`
- `imported_contests`
- benchmark outputs under `reports/`
- walk-forward outputs under `reports/ml/`

### Supervised ML governance layer

Used only for governed supervised assistance:

- `score_ml` artifacts,
- feature-lineage manifests,
- calibration snapshots,
- supervised datasets,
- model registry artifacts,
- walk-forward validation manifests.

### Institutional snapshot layer

Used for replayable state and observability:

- `snapshots`
- `adaptive_governance_reports`
- observability tables and snapshots produced by the dashboard

## Required Separation

The system must preserve the following separation rules:

1. Operational history must not contaminate benchmark history.
2. Benchmark history must not contaminate supervised ML datasets.
3. ML datasets must be versioned and temporally bounded.
4. Validation must remain walk-forward based.
5. Contest history is the canonical temporal backbone for scientific validation.
6. Operational dashboards may read across layers, but scientific artifacts must remain
   lineage-safe and reproducible.
7. Persistence is allowed to be shared, but scientific meaning is not.

## Temporal Governance Rules

The official temporal validation contract is:

- train on the past only;
- validate on the next contest only;
- roll the window forward;
- never include future contests in features;
- never compute supervised labels from a future boundary;
- never reuse benchmark results as training truth without versioned provenance.

The canonical temporal predicates are:

```text
train_start <= train_end < test_start <= test_end
feature_cutoff_contest < label_contest
```

## GT-01 Scope

GT-01 is the segregation of historical sources.

### GT-01A

Map the current tables and classify each source by scientific purpose.

### GT-01B

Classify each history source into:

- operational,
- benchmark,
- validation,
- expansion,
- ML,
- conference,
- snapshot,
- audit.

### GT-01C

Separate the histories at the data-contract level and prevent cross-contamination.

### GT-01D

Remove implicit reuse of operational data in benchmark and ML contexts.

### GT-01E

Create a temporal governance contract that documents the allowed use of each history
layer and the temporal boundaries for each scientific workflow.

### GT-01F

Record this governance as a stable architectural decision and keep it versioned.

## GT-02 Scope

GT-02 is the formal walk-forward scientific validation layer.

It must:

- build temporal splits from the contest timeline,
- validate only with historical data available before the test contest,
- report reproducible validation manifests,
- prevent leakage across folds,
- keep benchmark and supervised runs comparable but not conflated.

## Consequences

### Positive

- operational evidence becomes distinct from scientific evidence;
- benchmark results become reproducible and auditable;
- supervised ML can grow without leakage;
- the platform gains a stable temporal research contract;
- institutional reporting becomes safer to trust.

### Trade-offs

- more versioned artifacts and manifests;
- stricter rules for data access and reuse;
- additional validation work before any supervised expansion;
- more discipline around dashboard shortcuts that touch scientific history.

## Implementation Notes

The current codebase already contains pieces of this contract in:

- `src/lotoia/experiments/temporal_governance.py`
- `src/lotoia/ml/walk_forward_validation.py`
- `src/lotoia/ml/score_ml.py`
- `src/lotoia/ml/feature_lineage.py`
- `src/lotoia/backtesting/backtester.py`
- `src/lotoia/benchmark/benchmark_engine.py`

The next work should align the dashboard, reports, and experiment artifacts with this
official segregation so that operational history and scientific history no longer drift
together.

