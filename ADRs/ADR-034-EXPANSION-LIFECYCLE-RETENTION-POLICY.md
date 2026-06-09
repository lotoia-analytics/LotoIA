# ADR 034 - Expansion Lifecycle Retention Policy

Status: Accepted

## Context

The LotoIA expansion pipeline now has a validated scientific lifecycle:

- preview operational generation;
- post-contest validation;
- institutional promotion;
- cleanup of obsolete noise;
- institutional memory refresh;
- auditability through snapshots and lineage.

The project is in a controlled operational phase. Expansion artifacts must be
retained only when they remain scientifically useful, institutionally relevant,
and auditable over time.

The current codebase already distinguishes expansion lifecycle states:

- `PENDING`
- `VALIDATED`
- `ARCHIVED`
- `DISCARDED`
- `PREMIUM`

and already exposes cleanup and promotion hooks in the dashboard and in the
public persistence layer.

## Decision

LotoIA adopts a formal retention policy for expansion history.

### Retention tiers

1. **PENDING**
   - preview operational state;
   - keep as short-lived operational context;
   - do not treat as institutional memory;
   - may be removed by cleanup once superseded.

2. **VALIDATED**
   - expansion passed contest-based validation;
   - keep as institutional evidence;
   - eligible for institutional memory refresh;
   - eligible for long-term audit retention.

3. **PREMIUM**
   - expansion scored as high-performance and structurally strong;
   - keep as highest-value operational artifact;
   - always preserved ahead of lower-value records;
   - promoted into validated institutional memory when official context exists.

4. **ARCHIVED**
   - expansion remains relevant but is not top priority;
   - preserved as historical reference;
   - eligible for cold storage and long-term benchmark comparison;
   - retained ahead of discarded noise.

5. **DISCARDED**
   - redundant, low-value, or structurally noisy expansion;
   - eligible for cleanup;
   - not preserved as institutional memory unless later revalidated by an
     explicit promotion path.

### Cleanup policy

- cleanup must preserve the strongest institutional records first;
- cleanup must keep `PREMIUM`, `VALIDATED`, and `ARCHIVED` records ahead of
  `DISCARDED`;
- cleanup must operate with a limit-based retention window;
- cleanup must never alter benchmark, walk-forward, temporal governance, or
  score_ml contracts;
- cleanup must be auditable and deterministic.

### Cold storage policy

- long-term reference artifacts should be persisted as snapshots/reports, not
  as transient preview rows;
- institutional memory refresh must write:
  - snapshot
  - state
  - lineage

### Historical benchmark policy

- historical benchmark records are preserved for comparison;
- benchmark artifacts must remain temporally valid;
- cleanup must not remove benchmark evidence required for scientific audit.

## Consequences

### Positive

- expansion artifacts now have an explicit lifecycle;
- cleanup can remove operational noise without destroying institutional value;
- validated and premium records remain auditable over time;
- preview and institutional memory stay separated by policy, not only by UI;
- lineage and snapshot refresh can be used to reconstruct the operational story.

### Trade-offs

- the system becomes more selective about what it keeps permanently;
- retention decisions must remain conservative to avoid accidental loss of
  relevant scientific evidence;
- operational preview data may be pruned before it becomes institutional memory.

## Evidence

Validated code paths:

- `src/lotoia/public/expansion_lifecycle.py`
- `src/lotoia/public/persistence/repositories.py`
- `src/lotoia/database/public_repository.py`
- `dashboard/admin_app.py`

Validated behavior:

- lifecycle statuses are present and used in code;
- cleanup exists and is limit-based;
- promotion can refresh institutional memory;
- preview and validated memory are separated;
- validated promotions can write snapshot/state/lineage records.

Observed runtime posture:

- expansion lifecycle is structurally ready;
- retention is operationally enforceable;
- the retention policy is now formally declared as part of the institution.

