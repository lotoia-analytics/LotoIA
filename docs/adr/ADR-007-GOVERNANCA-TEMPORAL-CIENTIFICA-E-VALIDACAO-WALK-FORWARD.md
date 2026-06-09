# ADR-007 — Governança Temporal Científica e Validação Walk-Forward

Status: Accepted

## Context

LotoIA reached a validated temporal governance stage and must preserve this
scientific result as permanent institutional knowledge.

The platform now demonstrates:

- walk-forward validation with strict past-to-future separation;
- benchmark and backtest flows that use only prior history;
- anti-leakage guards on supervised rows and score_ml calibration;
- logical segregation of operational, benchmark, validation, and expansion
  histories through contracts and registries;
- runtime validation that remains reproducible and temporally consistent.

The physical persistence layer is still partially shared across historical
domains, so the segregation is not yet fully materialized as distinct history
tables.

## Decision

LotoIA formalizes the temporal scientific governance baseline with the
following rules:

1. **Temporal validation is mandatory**
   - walk-forward is the canonical validation mechanism;
   - training may only use contests strictly prior to the validation target;
   - future leakage is prohibited.

2. **Benchmarking is temporally governed**
   - benchmark and backtest flows must remain past-only;
   - contaminated benchmark usage is prohibited;
   - score_ml remains protected as an auxiliary capability.

3. **Historical segregation exists logically**
   - operational, benchmark, validation, expansion, and contest histories must
     remain independently classified;
   - logical segregation is enforced through registries and validation
     contracts;
   - physical segregation remains partial and must be treated as a residual
     risk under audit.

4. **No expansion during audit**
   - no new engines;
   - no strong supervised ML activation;
   - no new GT phases;
   - no UI growth;
   - no architectural expansion while the scientific core is under
     validation.

## Consequences

### Positive

- the scientific core becomes institutionally reproducible;
- validation behavior can be audited against a formal baseline;
- benchmark and score_ml remain protected from leakage;
- the project can preserve evidence without increasing roadmap entropy.

### Trade-offs

- physical persistence remains partially shared;
- some segregation is still logical rather than table-level;
- the runtime stays intentionally conservative while evidence is accumulated.

## Evidence

Validated code paths:

- `src/lotoia/experiments/temporal_governance.py`
- `src/lotoia/ml/walk_forward_validation.py`
- `src/lotoia/benchmark/benchmark_engine.py`
- `src/lotoia/backtesting/backtester.py`
- `src/lotoia/ml/score_ml.py`
- `src/lotoia/governance/scientific_governance.py`

Validated runtime results:

- walk-forward validation reports remained temporally valid for 300, 500, and
  1000 contests;
- benchmark and backtest execution remained past-only;
- anti-leakage guards remained active in the supervised governance layer;
- temporal validation and benchmark test suites passed.

## Baseline

This ADR establishes the scientific validation baseline as a permanent
institutional artifact.

The baseline remains valid when:

- no future contest is consumed by validation or benchmark logic;
- shared persistence remains known and controlled;
- `score_ml` stays in preparation mode;
- runtime stability and observability remain consistent.

