# ADR 028 - Institutional Maintenance Layer

Status: Accepted

## Context

LotoIA has reached a mature SaaS/institutional state after the structural and
governance work completed through Mission 27. At this point, the main risk is
not feature absence, but regression through drift:

- bootstrap regressions,
- UX inconsistency,
- workflow instability,
- observability degradation,
- technical debt accumulation,
- accidental coupling to the scientific core.

The platform needs an explicit maintenance contract that preserves the maturity
already achieved without introducing new architectural layers.

## Decision

We formalize Mission 28 as an Institutional Maintenance Layer composed of:

- runtime monitoring continuo,
- preventive maintenance governance,
- technical debt tracking,
- UX drift prevention,
- workflow stability monitoring,
- observability maturity,
- bootstrap regression protection,
- SaaS lifecycle governance,
- continuous audit cycles,
- institutional maintenance certification.

This layer is documentary and operational. It does not introduce new product
capabilities or new scientific engines.

## Boundaries

The maintenance layer must not:

- create new intelligence systems,
- alter the scientific baseline,
- modify benchmark or longitudinal logic,
- weaken ML governance boundaries,
- hide regressions behind operational wrappers,
- turn maintenance into an architecture-expansion channel.

## Governance Rules

- Entry points must remain lightweight and bootstrap-safe.
- Heavy subsystems must stay behind lazy imports or runtime composition.
- Visual and workflow consistency must be validated continuously.
- Scientific modules remain isolated from maintenance concerns.
- Audit cycles must be bounded, repeatable, and reproducible.
- SaaS readiness must be checked as a platform property, not a one-off task.

## Consequences

Positive:

- maintenance becomes an institutional contract,
- runtime drift is easier to detect,
- SaaS readiness remains active instead of implied,
- the platform can stay mature without degrading silently.

Trade-offs:

- more discipline in change management,
- more recurring validation work,
- stricter boundaries between maintenance and feature work.

## Implementation Notes

Mission 28 should be expressed through:

- formal policy documentation,
- operational checklists by phase,
- recurring audit cadence,
- maintenance-focused runtime validation.

It should be used to protect the platform, not to re-open architectural
expansion.
