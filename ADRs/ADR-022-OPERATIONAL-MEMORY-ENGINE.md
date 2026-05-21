# ADR 022 - Operational Memory Engine

Status: Accepted

## Context

LotoIA needed an institutional memory layer capable of persisting runtime state, reconstructing chronology, comparing snapshots, and replaying execution history without coupling the memory layer to UI or analytical execution logic.

## Decision

We are introducing an `InstitutionalMemoryRegistry` under `src/lotoia/memory/` as the declarative authority for operational memory.

The registry will:

- register institutional snapshots,
- persist runtime state transitions,
- expose snapshot comparison and replay hooks,
- provide execution memory lookup for institutional dashboards and future governance.

## Boundaries

The memory engine must not:

- render user interfaces,
- execute analytics,
- execute ML,
- embed SQL inline in presentation code,
- depend on Streamlit,
- mutate generator, benchmark, baseline, or longitudinal scientific logic.

## Governance

- Every stored state must be traceable to an execution context.
- Memory snapshots must be reproducible and timestamped.
- Replay must remain chronological and auditable.
- Memory persistence must stay separate from statistical computation.
- Future ML governance may consume memory lineage, but memory must remain model-agnostic.

## Consequences

Positive:

- institutional memory becomes explicit and queryable,
- state diffs and replay can be audited,
- timeline reconstruction is possible from persisted evidence.

Trade-offs:

- new persistence tables and registry code,
- more governance tests required,
- stricter boundaries between memory, observability, and analytics.

## Future Work

- add richer replay views and executive timeline widgets,
- connect adaptive intelligence to memory snapshots in governed ways,
- use memory lineage as a foundation for future supervised ML observability.
