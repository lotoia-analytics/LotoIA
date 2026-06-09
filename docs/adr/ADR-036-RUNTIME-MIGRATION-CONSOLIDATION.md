# ADR-036 - Runtime Migration Consolidation

## Status
Proposed

## Context

The LotoIA runtime currently exposes operational instability in local and published environments:

- inconsistent cache and reload behavior,
- old builds persisting unexpectedly,
- divergence between local and published runtime behavior,
- long-running or automatic jobs making the admin runtime heavier than necessary.

The product must keep the scientific core unchanged while consolidating the operational runtime around a predictable deployment model.

## Decision

We consolidate the operational surface to the main workflow and prepare a cleaner runtime migration path.

### Operational simplification

- Keep the main operational flow centered on:
  - `Gerar Jogos`
  - `Conferir Jogos`
  - `Simular Resultado`
  - `Memória Analítica`
- Remove HBIA from the primary operational UI.
- Remove the Expansivo flow from the main navigation and visible product surface.
- Preserve historical payloads, lineage, replay, benchmark artifacts, and existing database schema.

### Runtime consolidation checklist

#### Environment variables already in use

- `DATABASE_URL`
- `LOTOIA_AUTO_SYNC_RESULTS_ON_STARTUP`
- `LOTOIA_LIGHTWEIGHT_ADMIN_RUNTIME`
- `LOTOIA_DISABLE_INSTITUTIONAL_COCKPIT`
- `LOTOIA_RUNTIME_AUDIT`
- `LOTOIA_BOOTSTRAP_SCHEMA_ON_STARTUP`

#### Database/runtime paths

- `DB_PATH`
- `DEFAULT_DATABASE_PATH`
- institutional adapter resolution via `resolve_institutional_adapter(...)`

#### Operational jobs that must remain on-demand

- benchmark longitudinal
- replay histórico
- temporal replay
- sync contínuo
- workflow scheduler loops
- verbose telemetry loops

#### CLI entrypoints already available

- `python -m lotoia result-sync`
- `python -m lotoia official-caixa-validation`
- `python -m lotoia workflow-scheduler`
- `python -m lotoia operational-lifecycle`
- `python -m lotoia benchmark`
- `python -m lotoia reports`
- `python -m lotoia institutional-analytics`

#### Deployment targets to evaluate

- Render
- Fly.io

### Validation checklist for a clean migration

1. Confirm a single backend for admin runtime and sync runtime.
2. Confirm the deployment command starts only the intended Streamlit entrypoint.
3. Confirm automatic jobs are disabled by default in the local admin runtime.
4. Confirm logs clearly show:
   - build id
   - database backend
   - engine URL
   - sync state
   - cache boundaries
5. Confirm restart/redeploy is deterministic and does not resurrect old builds.
6. Confirm `imported_contests`, `generation_events`, and `generated_games` remain readable after restart.

## Consequences

- Lower operational friction in the local admin runtime.
- Clearer separation between UI and long-running workloads.
- Reduced risk of hidden background work during daily operation.
- Cleaner path for migration to a more predictable runtime platform.

## Notes

This ADR does not change:

- benchmark logic,
- `temporal_v1`,
- scoring core,
- Caixa validation,
- observability,
- historical persistence.

It only consolidates the operational runtime and documents the migration checklist.
