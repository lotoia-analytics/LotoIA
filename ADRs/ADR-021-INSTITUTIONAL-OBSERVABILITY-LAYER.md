# ADR 021 - Institutional Observability Layer

Status: Accepted

## Context

LotoIA needed an institutional observability layer that could audit runtime execution, persist tracing evidence, preserve lineage, and support replayable operational history without coupling observability to statistical or ML logic.

## Decision

We introduced a dedicated observability persistence layer backed by SQLite tables for runtime executions, spans, metrics, lineage, and snapshots.

The observability layer:

- captures `execution_id` for every operational flow,
- records spans and execution timing,
- persists operational metrics and lineage events,
- stores immutable snapshots for institutional replay,
- exposes a dashboard-oriented summary built from persisted evidence.

## Boundaries

The observability layer must not:

- alter generator logic,
- alter baseline hard logic,
- alter benchmark logic,
- alter longitudinal core logic,
- alter adaptive intelligence logic,
- alter orchestration logic,
- alter ML pipeline logic,
- alter scientific heuristics.

Observability is read-heavy and audit-oriented. Statistical and scientific logic remain separate from persistence.

## Governance

- All persisted observability events must be reproducible and timestamped.
- Runtime execution tracing must be auditable by `execution_id`.
- The observability dashboard must consume persisted evidence only.
- Future ML observability must be additive and governed, not autonomous.

## Consequences

Positive:

- full runtime auditability,
- replayable operational lineage,
- executive visibility into health, drift, and confidence stability,
- a persistent foundation for governed ML observability.

Trade-offs:

- additional persistence tables and reporting code,
- more operational evidence to maintain and test,
- stronger coupling between runtime flows and observability writes.

## Future Work

- enrich dashboard widgets for runtime graph, lineage replay, and drift evolution,
- add richer ML observability contracts as ML runtime grows,
- keep observability exports versioned and test-covered.
