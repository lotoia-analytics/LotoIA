# ADR 033 - Institutionalization of Scientific Validation

Status: Accepted

## Context

The LotoIA temporal governance layer has been validated in code and in runtime
through walk-forward validation, temporal benchmark execution, and anti-leakage
guards.

The project is now in an audit phase, not an expansion phase.
The scientific core must be preserved as institutional baseline material.

Current evidence shows:

- walk-forward validation is temporally valid;
- benchmark and backtest flows use past-only history;
- supervised score_ml remains protected by temporal contracts;
- historical segregation exists logically through registries and governance;
- physical persistence is still partially shared across historical domains.

## Decision

LotoIA adopts the scientific validation baseline as an institutional artifact.

This baseline records:

1. **Validated temporal behavior**
   - walk-forward remains the canonical validation mechanism;
   - 300, 500, and 1000 contest validation windows are temporally valid;
   - no future leakage is permitted in validation or benchmark flows.

2. **Benchmark governance**
   - benchmark and backtest flows remain past-only;
   - benchmark contamination is prohibited;
   - score_ml remains auxiliary and protected.

3. **Segregation status**
   - logical segregation is already in place through contracts, registries, and
     validation rules;
   - physical segregation is still partial because the database continues to
     share several persistence tables.

4. **Audit posture**
   - no new GTs;
   - no new motors;
   - no strong supervised ML activation;
   - no architecture expansion during the validation audit.

## Consequences

### Positive

- the scientific core now has a permanent institutional baseline;
- temporal integrity can be audited against a formal reference;
- the project can observe runtime and benchmark behavior without roadmap noise;
- the validation stage becomes reproducible and documentable.

### Trade-offs

- shared physical persistence remains a residual risk;
- physical history tables are not yet fully split by scientific domain;
- the system intentionally remains conservative while validation is ongoing.

## Evidence

Validated code paths:

- `src/lotoia/experiments/temporal_governance.py`
- `src/lotoia/ml/walk_forward_validation.py`
- `src/lotoia/benchmark/benchmark_engine.py`
- `src/lotoia/backtesting/backtester.py`
- `src/lotoia/ml/score_ml.py`
- `src/lotoia/governance/scientific_governance.py`

Validated runtime results:

- walk-forward validation reports were temporally valid for 300, 500, and
  1000 contests;
- benchmark and backtest behavior remained past-only;
- anti-leakage guards remained active in the supervised governance layer;
- temporal validation and benchmark test suites passed.

## Baseline Policy

This ADR establishes that:

- scientific validation is part of the institutional record;
- temporal validation must remain mandatory;
- leakage-free benchmark behavior must remain mandatory;
- score_ml remains in preparation mode until a future governance decision.

