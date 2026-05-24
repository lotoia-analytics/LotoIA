# ADR 030 - Temporal Consolidation of Operational Nuclei, Benchmark Engine, Feature Governance, Matrix Geometry and Runtime Integrity

Status: Accepted

## Context

After the initial temporal segregation of historical sources and the formalization of
walk-forward validation, the LotoIA scientific stack needs a stricter runtime boundary.
The remaining challenge is no longer only about separating tables. It is now about
making the operational nuclei, benchmark execution, feature definitions, matrix-based
spatial reading, and runtime integrity behave as one governed temporal system.

The platform needs to ensure that:

- operational nuclei remain temporally scoped and scientifically named;
- benchmark comparisons are temporal and future-relative only;
- official features are governed with cutoff rules and leakage guards;
- matrix geometry is treated as a first-class temporal signal family;
- runtime integrity validates the full scientific contract continuously.

## Decision

LotoIA adopts a formal temporal scientific runtime registry for the GT-11 to GT-15
scope.

The registry governs five areas:

1. **Temporal consolidation of operational nuclei**
   - `Jogos Passados`
   - `Testar Estratégia`
   - `Comparativos Operacionais`
   - `Ranking ML`
   - `Expansivo`
   - `Analíticas Persistidas`

2. **Temporal benchmark engine**
   - compare official strategies only;
   - keep validation future-relative;
   - preserve traceability and historical metrics;
   - disallow leakage or contaminated benchmark reuse.

3. **Temporal feature governance**
   - govern official features such as frequency, delay, sequence, quadras, sum, rows,
     columns, and diagonals;
   - prohibit future information and label-derived access;
   - keep feature cutoff strictly before label assignment.

4. **Temporal matrix geometry**
   - treat rows, columns, diagonals, center, frame and distribution as governed spatial
     signals;
   - preserve the Lotofácil 5x5 matrix as the institutional geometry;
   - use matrix-based signals only under temporal rules.

5. **Scientific runtime integrity**
   - validate leakage, dataset correctness, benchmark cleanliness, historical
     segregation, feature validity and temporal window validity as a single runtime
     contract.

## Consequences

### Positive

- the scientific runtime becomes easier to validate as one coherent contract;
- benchmark and feature governance become traceable and auditable;
- matrix-based signals gain a formal temporal boundary;
- the platform can reject contaminated scientific state earlier;
- operational nuclei are now clearly named as scientific components.

### Trade-offs

- more registry objects and validation surfaces;
- stricter runtime checks for scientific workflows;
- more explicit versioning for benchmark and feature contracts;
- additional discipline required before expanding the ML pipeline.

## Implementation Notes

The temporal scientific runtime registry is implemented in:

- `src/lotoia/governance/temporal_scientific_governance.py`

The registry is validated by targeted tests to ensure:

- the operational nuclei are complete and segregated;
- the benchmark engine only exposes the official strategies;
- the feature governance registry rejects future information;
- the matrix geometry registry remains a 5x5 Lotofácil structure;
- the runtime integrity contract keeps every scientific guard enabled.

