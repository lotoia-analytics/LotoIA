# SNAPSHOT 05 - Scientific Validation Baseline

## Purpose

This snapshot records the institutional baseline of the temporal scientific
validation layer in LotoIA.

## Validated Results

### Walk-forward validation

- 300 contests: temporal_valid = true
- 500 contests: temporal_valid = true
- 1000 contests: temporal_valid = true

### Benchmark and backtest

- benchmark uses past-only relative history
- backtest uses previous history only
- no future contest is consumed by the core validation path

### Anti-leakage posture

- supervised rows reject future feature cutoffs
- score_ml calibration rejects temporal leakage
- baseline governance rejects score_ml in prohibited contexts

## Segregation Status

### Correct

- logical segregation exists through governance registries and validation
  contracts
- temporal validation is mandatory
- benchmark validation is mandatory

### Partially segregated

- the database still shares operational tables across historical domains
- `benchmark_history`, `validation_history`, `expansion_history`, and
  `contest_history` are not yet materialized as separate physical tables

### Residual risk

- direct access to shared tables outside the governed contracts can reintroduce
  contamination
- shared persistence remains the main residual risk

## Operational Notes

- runtime validation remains observability-driven
- score_ml is kept in preparation mode only
- no architectural expansion is allowed during this baseline phase

