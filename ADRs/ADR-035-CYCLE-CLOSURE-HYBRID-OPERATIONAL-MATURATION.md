# ADR 035 - Cycle Closure: Hybrid Operational Maturation

Status: Accepted

## Context

LotoIA reached a mature hybrid phase where the scientific core, the premium
expansive engine, the validated memory lifecycle, and the operational
persistence path are all structurally present.

During the current operational cycle, the project focused on stability,
durability, longitudinal validation, retention governance, and scientific
benchmarking. Expansion of roadmap, new ML, and temporal governance changes
were explicitly out of scope.

Validated evidence from the cycle shows:

- the admin dashboard now bootstraps the local SQLite schema at startup;
- generation and reconciliation can persist and replay successfully in a
  bootstrapped SQLite smoke test;
- the scientific expansive engine is no longer lexicographic brute force;
- the validated expansion lifecycle now refreshes institutional memory
  snapshots, states, and lineage;
- a formal retention policy is now documented as institutional baseline.

The remaining gaps are runtime-confirmation gaps rather than missing
capabilities:

- final Cloud/runtime durability proof for the operational SQLite path;
- formal production benchmark closure between the mathematical expansive
  engine and the scientific expansive engine;
- long-running proof of memory accumulation across real contest cycles;
- SaaS multi-tenant consolidation, which is intentionally deferred.

## Decision

LotoIA enters a formally documented **hybrid operational maturation** phase.

The project accepts the following state as institutional baseline:

1. **Scientific core**
   - temporal governance remains intact;
   - walk-forward validation remains mandatory;
   - benchmark and backtest remain temporally valid;
   - score_ml remains auxiliary and protected.

2. **Persistence and runtime**
   - the admin dashboard bootstraps the local SQLite schema at startup;
   - the operational SQLite path is explicitly auditable;
   - generation, persistence, reboot/re-read, simulation, and reconciliation
     are validated in local smoke execution.

3. **Scientific expansive engine**
   - the engine operates as a curated premium selection pipeline;
   - structural diversity, overlap control, rerank entropy, and concentration
     metrics are available for audit;
   - the engine is no longer a lexicographic enumerator.

4. **Validated memory and lifecycle**
   - validated expansions are promoted into institutional memory refresh;
   - snapshot, state, and lineage are now written together;
   - lifecycle statuses and retention policy are formalized.

5. **Roadmap boundaries**
   - no new motors;
   - no new ML;
   - no benchmark or walk-forward changes;
   - no SaaS expansion until persistence is fully proven in production.

## Consequences

### Positive

- the project has an explicit institutional end-of-cycle reference;
- the remaining gaps are now clearly classified as validation gaps, not
  architecture gaps;
- operators can focus on proving the published runtime instead of guessing
  about code paths;
- the scientific expansive engine and the retention policy now have formal
  institutional placement.

### Trade-offs

- the system intentionally remains conservative while production proof is
  completed;
- some components are ready in code but still need runtime confirmation in the
  deployed environment;
- SaaS consolidation is deferred by design.

## Evidence

Validated code paths:

- `dashboard/admin_app.py`
- `src/lotoia/database/database.py`
- `src/lotoia/database/public_repository.py`
- `src/lotoia/public/reconciliation.py`
- `src/lotoia/public/expansion_lifecycle.py`
- `src/lotoia/combinatorics/scientific_expansion_engine.py`

Validated local outcomes:

- SQLite schema bootstrap now runs at dashboard startup;
- generation/persistence/reconciliation work in a bootstrapped SQLite smoke
  test;
- scientific expansive engine returns diverse premium pools;
- validated expansion promotion refreshes institutional memory records.

Institutional artifacts produced during the cycle:

- `ADRs/ADR-034-EXPANSION-LIFECYCLE-RETENTION-POLICY.md`
- `reports/governance/expansive_scientific_benchmark_report.json`

