# Cloud Runtime

## Streamlit Cloud

The dashboard is designed to remain compatible with Streamlit Cloud deployment.

Operational expectations:

- single-process Streamlit runtime;
- lightweight startup;
- no external orchestration dependency for the dashboard;
- predictable local SQLite access;
- stable page routing.

## SQLite in Cloud Context

SQLite remains the operational persistence layer.

The cloud runtime preserves:

- generation events;
- check events;
- leads;
- operational logs;
- audit trail;
- report references.

## Snapshots

Snapshots are persisted as files under `reports/`.

This supports:

- institutional replay;
- auditability;
- artifact download;
- model governance traces.

## Logs

Runtime logs capture:

- generation;
- conference;
- ML;
- reporting;
- snapshots;
- operational failures.

## Observability

Cloud observability should remain lightweight and safe:

- use local DB queries;
- avoid expensive cross-service dependencies;
- keep health metrics derived from existing operational events;
- preserve deployment stability.

## Stability Rules

- no destructive runtime changes;
- no refactor of operational modules;
- no dependency on ephemeral cloud state for core scientific logic;
- no temporal leakage introduced by cloud monitoring.

