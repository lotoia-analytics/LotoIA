# Scientific Validation Baseline

## Purpose

Record the institutional evidence that the temporal scientific core of LotoIA
is valid, reproducible, and leakage-protected.

## Baseline Evidence

- temporal validation reports passed for 300 contests
- temporal validation reports passed for 500 contests
- temporal validation reports passed for 1000 contests
- benchmark and backtest logic remained past-only
- `score_ml` calibration stayed protected by temporal boundary checks
- anti-leakage rules remained active

## Test Evidence

The following validation set passed locally:

- `tests/test_backtester.py`
- `tests/test_benchmark_engine.py`
- `tests/test_temporal_governance.py`
- `tests/test_temporal_history_registry.py`
- `tests/test_scientific_governance.py`
- `tests/test_supervised_walk_forward.py`

Result:

- `36 passed`

## Segregation Status

### Correct

- walk-forward separation is valid
- benchmark/backtest consume only prior history
- anti-leakage and score_ml guards are active

### Partially segregated

- physical persistence still uses shared tables for multiple historical domains
- the logical separation is stronger than the table-level separation

### Residual risk

- direct access to shared persistence outside governed contracts can reintroduce
  contamination

## Operational Conclusion

The scientific core is valid and audit-ready, but architecture expansion remains
paused until physical segregation is revisited under a separate governance
decision.

