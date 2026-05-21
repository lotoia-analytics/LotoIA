# ADR 023 - Scientific ML Governance Layer

Status: Accepted

## Context

LotoIA already has a statistical structural core, a governed `score_ml` layer, temporal validation primitives, and institutional observability/memory contracts.

The project now needs an explicit scientific governance boundary for supervised ML so that:

- walk-forward validation is mandatory,
- experiment execution is reproducible,
- model versions are traceable and reversible,
- feature provenance is auditable,
- calibration snapshots are governed,
- drift is monitored over time,
- explainability remains interpretable,
- ML runtime stays isolated from statistical runtime.

ML in LotoIA remains auxiliary and incremental. It must never replace structural statistical analysis or introduce temporal leakage.

## Decision

We are formalizing a Scientific ML Governance Layer under `src/lotoia/ml/` as the authoritative boundary for supervised ML governance.

The layer will include:

- governed `score_ml` activation,
- walk-forward validation contracts,
- experiment tracking,
- model registry and rollback,
- feature lineage tracking,
- calibration governance snapshots,
- ML drift detection,
- ML explainability,
- ML runtime isolation.

## Boundaries

The ML governance layer must not:

- alter generator logic,
- change baseline hard,
- replace benchmark ranking,
- break temporal validity,
- introduce temporal leakage,
- become an autonomous decision engine,
- silently recalibrate models,
- hide model lineage,
- couple ML runtime to UI concerns.

## Governance

- Every supervised ML run must remain reproducible.
- Every model version must be versioned and reversible.
- Every feature set must have lineage and temporal scope.
- Every calibration snapshot must be persistent and auditable.
- Walk-forward validation is required before supervised execution is considered governed.
- Drift, confidence, and explainability must remain interpretable and persisted.
- ML runtime must remain isolated from statistical runtime and from presentation layers.
- `score_ml` must remain auxiliary to the hybrid statistical ranking contract.

## Consequences

Positive:

- ML becomes governable instead of merely experimental,
- scientific validation is explicit,
- future supervised experimentation gains a stable institutional contract,
- observability, memory, and ML can interoperate without collapsing into a single opaque layer.

Trade-offs:

- more registry and snapshot artifacts,
- more tests and contracts to maintain,
- stricter boundaries between ML, statistics, and persistence.

## Future Work

- connect future supervised model versions to the registry and rollback contract,
- expand explainability with richer contribution views,
- surface governed ML health in the institutional observability dashboard,
- extend drift monitoring into longitudinal ML reports,
- keep all future ML work under walk-forward and anti-leakage governance.
