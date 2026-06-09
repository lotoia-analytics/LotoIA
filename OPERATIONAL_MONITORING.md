# LotoIA Operational Monitoring

## Purpose

This document defines the first official operational monitoring layer for
LotoIA during controlled operation.

The layer is intentionally lightweight, auditable, local-first, and compatible
with Streamlit Cloud. It does not add external services and does not change the
scientific, ML, dashboard, SQLite, governance, or observability architecture.

## Health Panel

The operational health panel is exposed in the institutional Observability
page and tracks:

- average generation time;
- average check time;
- cache policy;
- snapshot volume;
- total operational events;
- SQLite status;
- runtime status;
- ML status.

Status definitions:

- `SQLite = ok`: integrity check returns `ok`.
- `Runtime = ok`: no failed operational event in the recent monitoring window.
- `Runtime = degraded`: at least one recent failed event exists.
- `ML = ok`: ML events exist without recent failure.
- `ML = idle`: no recent ML operational event exists.
- `ML = failed`: recent ML failure exists.

## Performance Tracking

Performance metrics are persisted through existing `operational_logs` entries
and derived from existing public/admin event tables.

Tracked families:

- generation time;
- check time;
- analytics rendering time;
- report generation time;
- ML inference/governance time;
- dashboard loading time.

No dedicated metrics table is introduced in this phase. This keeps the layer
compatible with the current SQLite structure.

## Cloud Monitoring

Cloud-oriented failure counters monitor:

- dashboard/runtime failures;
- historical load failures;
- export failures;
- SQLite failures;
- ML failures.

Failures are recorded as controlled operational events with `status = failed`.
The Streamlit runtime remains active whenever possible.

## Operational Metrics

The controlled-operation metrics include:

- daily average generation volume;
- total check volume;
- ML usage volume;
- snapshot volume;
- daily log growth;
- total log volume;
- SQLite file growth.

These metrics are computed through bounded queries and recent operational
tables to avoid heavy runtime overhead.

## Alert Contracts

Initial lightweight thresholds:

- excessive generation time: `5000 ms`;
- excessive check time: `3000 ms`;
- abnormal daily log growth: `1000 events`;
- SQLite growth: `256 MB`;
- repeated failures: `3 recent failures`;
- ML failures: any recent ML failure;
- runtime failures: degraded runtime status.

Alert statuses:

- `ok`: contract is inside threshold;
- `alert`: contract crossed the threshold and requires review.

The alert layer is advisory. It does not block generation, checking, analytics,
reports, snapshots, or ML governance.

## Cache Monitoring

Cache usage is represented as an institutional cache policy:

- TTL: `300 seconds`;
- max cached entries: `16`.

This provides bounded memory behavior in Streamlit Cloud without relying on
private Streamlit cache internals.

## SaaS Preparation

This layer prepares LotoIA for future SaaS evolution by establishing:

- stable operational metrics;
- clear health contracts;
- local auditability;
- bounded cloud-friendly overhead;
- separation from scientific and ML logic.

Future SaaS phases may externalize these metrics to a production observability
backend, but this mission intentionally keeps monitoring local and lightweight.
