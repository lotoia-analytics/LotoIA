# ADR 032 - Operational Scientific Audit Baseline

Status: Accepted

## Context

The LotoIA temporal governance layer has reached a stable validation stage.
The current priority is to audit the scientific core without expanding the
architecture or creating new engines.

The codebase now demonstrates:

- walk-forward validation with strict past-to-future separation;
- benchmark and backtest flows that consume only prior history;
- anti-leakage guards for supervised rows and score_ml calibration;
- logical segregation of operational, benchmark, validation, and expansion
  concerns through registries and validation contracts.

At the same time, the physical persistence layer still shares tables for several
historical domains, so the segregation is not yet fully materialized as separate
history tables.

## Decision

LotoIA adopts an operational scientific audit baseline with the following
governance rules:

1. **Temporal validation is mandatory**
   - walk-forward remains the canonical validation mode;
   - training may only use past-relative contests;
   - future leakage is prohibited.

2. **Benchmarking remains temporally governed**
   - benchmark and backtest flows must continue to use prior history only;
   - score_ml remains a protected auxiliary capability, not a primary runtime.

3. **Historical segregation is enforced logically**
   - operational, benchmark, validation, and expansion histories must remain
     classified independently;
   - shared persistence is allowed only while the physical separation is still
     being audited.

4. **No architectural expansion during audit**
   - no new GTs;
   - no new motors;
   - no strong supervised ML activation;
   - no UI growth until the scientific core proves stability.

## Consequences

### Positive

- the scientific core can be validated without adding roadmap noise;
- temporal integrity remains the default constraint;
- benchmark and score_ml remain protected from leakage;
- the audit can focus on evidence instead of expansion.

### Trade-offs

- physical persistence is still partially shared across historical domains;
- some segregation remains logical rather than table-level;
- the platform stays intentionally conservative while the audit is running.

## Evidence

Validated code paths include:

- `src/lotoia/experiments/temporal_governance.py`
- `src/lotoia/ml/walk_forward_validation.py`
- `src/lotoia/benchmark/benchmark_engine.py`
- `src/lotoia/backtesting/backtester.py`
- `src/lotoia/ml/score_ml.py`
- `src/lotoia/governance/scientific_governance.py`

Validated runtime results:

- walk-forward validation reports remained temporally valid for 300, 500, and
  1000 contests;
- benchmark and backtest tests passed with past-only behavior;
- leakage guards remained active in the supervised governance layer.

## Operational Baseline

The audit baseline is considered successful when:

- no future contest is consumed by validation or benchmark logic;
- shared persistence remains known and controlled;
- `score_ml` stays in preparation mode;
- runtime stability and observability remain consistent.

