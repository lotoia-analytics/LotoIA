# ADR 035 - Institutional Backup Policy

Status: Accepted

## Context

LotoIA has entered a phase of institutional operational maturation. At this
stage, the platform no longer preserves only runtime state; it preserves
scientific, operational, and longitudinal evidence that must remain auditable
and recoverable over time.

The current institutional asset set includes:

- longitudinal benchmarks;
- `generation_events` and `generated_games`;
- `reconciliation_runs`, `reconciliation_games`, and `reconciliation_events`;
- validated memory structures and lineage;
- analytics outputs;
- operational logs;
- institutional snapshots;
- architectural decisions and governance artifacts.

Because these assets now form part of the scientific patrimony of the project,
backup policy must be treated as institutional preservation rather than a
purely technical maintenance task.

## Problem

Without an explicit backup policy, the platform is exposed to the following
risks:

- loss of benchmark history;
- loss of scientific memory and lineage;
- operational corruption or partial recovery after incidents;
- loss of reconciliation history;
- loss of institutional snapshots and analytical outputs;
- inconsistent restore behavior across different runtime layers.

These risks are amplified by the fact that the platform maintains both
operational and institutional evidence that must remain temporally valid and
traceable.

## Decision

LotoIA adopts a formal institutional backup policy with three preservation
tiers.

### Daily backup

Daily backups must include:

- PostgreSQL dump of institutional data;
- SQLite fallback snapshot when present as a local operational artifact;
- operational logs;
- critical reports produced during the day.

### Weekly backup

Weekly backups must include:

- complete institutional snapshot;
- benchmark reports;
- ADRs and governance documents;
- configuration artifacts relevant to operational reproducibility.

### Monthly backup

Monthly backups must include:

- cold backup package;
- external storage copy;
- long-retention archive suitable for long-term preservation.

## Restore Strategy

Restore must follow a deterministic recovery checklist:

1. restore PostgreSQL institutional data;
2. validate that the runtime can read the restored database;
3. validate `generation_events` and `generated_games`;
4. validate `reconciliation_runs`, `reconciliation_games`, and
   `reconciliation_events`;
5. validate benchmark artifacts and longitudinal reports;
6. validate memory lineage and institutional snapshots;
7. validate that the restored environment preserves operational continuity.

Restore is considered complete only when the recovered runtime can be used for
auditable operational reading, not merely when the database file exists.

## Recommended Structure

Backup artifacts should follow a simple institutional layout:

```text
/backups
  /daily
  /weekly
  /monthly
```

This structure keeps the policy observable, easy to audit, and compatible with
future automation.

## Critical Scope

The backup policy explicitly covers:

- `generation_events`;
- `generated_games`;
- `reconciliation_runs`;
- `reconciliation_games`;
- `reconciliation_events`;
- `institutional_validated_expansions`;
- `institutional_memory_snapshots`;
- `institutional_memory_states`;
- `institutional_memory_lineage`;
- `operational_logs`;
- benchmark reports;
- ADRs;
- institutional analytics outputs.

## Architectural Impact

This ADR formalizes backup as preservation of scientific institutional
heritage. The objective is not only operational continuity, but longitudinal
continuity of the evidence that supports the platform's scientific and
structural claims.

This decision does not modify:

- benchmark methodology;
- walk-forward validation;
- `score_ml`;
- the scientific generation pipeline;
- rerank logic;
- lifecycle logic;
- reconciliation logic;
- taxonomy;
- validated memory semantics.

## Consequences

### Positive

- the platform now has an explicit institutional preservation baseline;
- restore and retention can be audited consistently;
- scientific evidence is preserved alongside operational logs;
- backup policy becomes part of the formal architecture record.

### Trade-offs

- the policy requires operational discipline to remain effective;
- additional storage and periodic verification are necessary;
- backup automation must be implemented carefully to avoid leakage or schema
  drift.

## Validation

This ADR is consistent with the current institutional direction of the
platform:

- preservation of longitudinal scientific evidence;
- protection of operational history;
- separation between scientific logic and persistence concerns;
- conservative evolution of the platform while production validation
  continues.

## Status

Accepted as the institutional backup baseline for LotoIA.
