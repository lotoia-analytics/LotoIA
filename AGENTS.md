# LotoIA - Architectural Governance

## Official Positioning

LotoIA is a Statistical Structural Platform with Incremental Supervised Assistance.

The system prioritizes:
- statistical engineering,
- structural analysis,
- temporal validation,
- interpretability,
- scientific benchmarking.

Machine Learning is auxiliary and incremental.

Official ML assistive policy: `docs/governance/POLITICA_ML_ASSISTIVO.md`
(ADR-042 / ADR 009). Status: `POLITICA_ML_ASSISTIVO_FORMALIZADA`.

---

## Mandatory Principles

- Never break src modular architecture.
- Never introduce temporal leakage.
- Benchmarking is mandatory.
- Walk-forward validation is required for supervised models.
- Statistical logic must remain separated from persistence.
- ML must not replace structural statistical analysis.
- Interpretability has priority over model complexity.
- All experiments must be reproducible.
- Models must be versioned.
- Datasets must be versioned.
- Backtesting must remain temporally valid.

---

## Architectural Organization

- src = business logic
- tests = validation
- data = persistence
- reports = outputs
- experiments = ML governance
- snapshots = institutional evolution
- ADRs = architectural decisions

---

## Official Philosophy

LotoIA is NOT a lottery prediction system.

LotoIA is a scientific statistical platform focused on:
- structural prioritization,
- probabilistic ranking,
- hybrid statistical analysis,
- incremental supervised assistance.

---

## ML Assistive Policy (mandatory)

1. ML must not replace Law 15 or sovereign generation rules.
2. ML must not mutate sovereign rules automatically.
3. ML must not produce games without traceability.
4. ML must not act as the central predictive engine.
5. ML may assist ranking, analysis, clustering, diagnostics, and validation only.
6. Every ML contribution must be explainable, testable, reversible, and auditable.
7. Every ML evolution must pass temporal validation.
8. No model may be promoted to an institutional component without a comparative report.