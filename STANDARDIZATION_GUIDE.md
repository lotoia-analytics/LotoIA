# LotoIA Standardization Guide

## Purpose

This guide defines the institutional standards for logs, snapshots, reports,
ML governance artifacts, and operational events in LotoIA.

LotoIA remains a Statistical Structural Platform with Incremental Supervised
Assistance. These standards do not replace the scientific pipeline, runtime,
generation, checking, dashboard, SQLite layer, observability, or cloud deploy.

## Global Conventions

- All operational timestamps are UTC.
- Human-readable metadata uses ISO-8601 with `Z`, for example `2026-05-20T13:45:30Z`.
- Artifact filenames use compact UTC timestamps, for example `20260520T134530Z`.
- Canonical artifact names follow:
  `lotoia_<artifact_type>_<name>_<YYYYMMDDTHHMMSSZ>.<ext>`.
- Every generated JSON artifact should expose a top-level `metadata` object.
- Metadata must include `standard_version`, `institution`, `positioning`,
  `artifact_type`, `name`, `created_at`, `timezone`, and `context`.

## Logs

Operational logs are standardized through an event envelope stored in
`context_json`.

Required fields:

- `standard_version`
- `occurred_at`
- `severity`
- `category`
- `event`
- `status`
- `context`

Canonical severities:

- `debug`
- `info`
- `warning`
- `error`
- `critical`

Canonical categories:

- `generation`
- `check`
- `export`
- `report`
- `snapshot`
- `ml`
- `observability`
- `audit`
- `sqlite`
- `runtime`

The existing SQLite tables remain compatible. The standard is applied inside
the JSON context, avoiding destructive schema changes.

## Snapshots

Snapshot filenames follow:

`lotoia_snapshot_<name>_<YYYYMMDDTHHMMSSZ>.json`

ML snapshot filenames follow:

`lotoia_ml_snapshot_<name>_<YYYYMMDDTHHMMSSZ>.json`

Snapshot JSON structure:

```json
{
  "metadata": {
    "standard_version": "standardization-v0.1.0",
    "institution": "LotoIA",
    "artifact_type": "snapshot",
    "created_at": "2026-05-20T13:45:30Z",
    "timezone": "UTC",
    "context": {}
  },
  "payload": {}
}
```

Snapshots are operational evidence. They must not modify statistical logic or
introduce temporal leakage.

## Reports

PDF, CSV, and JSON report artifacts follow the same naming convention:

`lotoia_report_<name>_<YYYYMMDDTHHMMSSZ>.<pdf|csv|json>`

Report JSON payloads include:

- top-level institutional `metadata`;
- `timestamp` using compact UTC;
- `type` preserving the operational report family;
- domain payload such as `analytics`, `games`, `contest_id`, or `result`.

PDF reports include an institutional header:

`LotoIA | Statistical Structural Platform | UTC`

CSV reports preserve tabular data only; operational metadata is recorded via
logs and artifact names to keep CSVs easy to consume.

## ML Governance

ML remains auxiliary, interpretable, versioned, and temporally governed.

ML governance artifacts must preserve:

- `model_version`;
- `feature_schema_version`;
- `experiment_name`;
- `metrics`;
- `validation_metrics`;
- `walk_forward_splits`;
- `temporal_valid`;
- training summary and calibration payload when available.

ML report filenames follow:

`lotoia_ml_governance_<YYYYMMDDTHHMMSSZ>.<json|csv|pdf>`

ML snapshots follow:

`lotoia_ml_snapshot_<name>_<YYYYMMDDTHHMMSSZ>.json`

All supervised model work must continue to use walk-forward validation. No
standardization artifact may bypass temporal governance, benchmarking, dataset
versioning, or model versioning.

## Operational Events

Operational events are recorded for:

- generation;
- checking;
- exports;
- reports;
- snapshots;
- ML training/governance;
- observability boot and health;
- SQLite failures;
- audit trail actions.

Events should use stable category names and a slugified event name. Context may
contain operational details such as `path`, `format`, `model_version`,
`feature_schema_version`, `contest_id`, and error summaries.

## Directory Conventions

- `reports/`: reports and export artifacts.
- `reports/snapshots/`: operational report snapshots.
- `reports/ml/`: ML governance reports.
- `reports/ml/snapshots/`: ML snapshots.
- `snapshots/`: institutional architecture snapshots.
- `experiments/`: governed ML and benchmark manifests.
- `ADRs/`: architectural decisions.
- `audit/` and `audit_full/`: audit evidence.

## Non-Negotiable Boundaries

- Do not refactor runtime or generation for standardization alone.
- Do not alter the scientific scoring pipeline through artifact formatting.
- Do not couple statistical logic to persistence details.
- Do not introduce temporal leakage in metadata, reports, or ML artifacts.
- Do not remove benchmark or walk-forward governance requirements.
