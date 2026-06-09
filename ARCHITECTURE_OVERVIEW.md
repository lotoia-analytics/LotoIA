# Architecture Overview

## Summary

LotoIA follows a modular, institutionally governed architecture centered on statistical analysis, temporal validation, interpretability, and reproducible experimentation.

## `src/` Layout

The `src/lotoia` package contains the operational and scientific core:

- `generator/`: game generation logic.
- `statistics/`: structural and historical analytics.
- `benchmark/`: comparative scientific benchmarking.
- `calibration/`: calibration and comparison of weights.
- `backtesting/`: temporally valid historical evaluation.
- `ml/`: interpretable score ML and reranking.
- `experiments/`: temporal governance and supervised validation rules.
- `database/`: persistence models and repository functions.
- `reports/`: backtest report generation.
- `public/`: public lead and contest workflows.

## Modular Separation

The architecture keeps the following boundaries:

- business logic in `src/`;
- persistence in database/repository layers;
- dashboard presentation in `dashboard/`;
- outputs in `reports/`;
- validation and governance in `experiments/`, `ml/`, and `observability`.

## Operational Flow

1. Historical data is loaded and validated.
2. Structural statistics and ranking logic generate candidate games.
3. ML may rerank candidates without replacing the base logic.
4. Backtesting and benchmarking validate performance temporally.
5. Reports, snapshots, and logs are emitted for institutional traceability.

## Persistence

The platform preserves SQLite as the operational persistence layer for:

- generation events;
- check events;
- leads;
- operational logs;
- audit trail;
- model governance artifacts when persisted through report/snapshot outputs.

## Runtime

The Streamlit runtime is intentionally stable and lightweight:

- no radical runtime rewrites;
- no coupled heavy infrastructure;
- no dependency on external cloud services for core execution;
- compatibility with Streamlit Cloud deployment.

## ML Pipeline

The ML stack is incremental and interpretable:

- feature extraction from existing game metadata;
- linear supervised calibration;
- attach score ML to games;
- supervised reranking;
- walk-forward validation;
- snapshots and experiment tracking.

## Governance Principles

- temporal integrity first;
- interpretability over complexity;
- ML as an auxiliary layer;
- reproducibility and versioning required;
- backtesting remains a scientific gate.

