# Cloud Runtime

## Railway Cloud-Only (Lei No 001)

Production operation runs exclusively on Railway with PostgreSQL as the single source of truth.

| Component | Runtime |
|-----------|---------|
| Dashboard ADM | `dashboard/institutional_app.py` |
| Deploy | `Procfile` / `railway.toml` |
| Database | PostgreSQL Railway (`DATABASE_URL`) |
| Auth | `AuthenticationService` via `dashboard/institutional_auth.py` |
| Local CPU | Browser only |

## Prohibited in production

- SQLite as operational persistence
- CSV as operational data source
- `localhost` in `DATABASE_URL`
- `session_state` as source of truth
- Unauthenticated ADM panel access

## Environment signals

Cloud runtime is detected when any of these are set:

- `LOTOIA_CLOUD_ONLY=1`
- `APP_ENV=production`
- `RAILWAY_ENVIRONMENT`
- `RAILWAY_PROJECT_ID`

When cloud runtime is active:

- `enforce_cloud_runtime_policy()` fails closed without PostgreSQL
- `require_institutional_login()` blocks the panel until login

## Local development

Local development may still use SQLite when cloud signals are absent. Set `LOTOIA_AUTH_REQUIRED=0` to skip login locally.

## Validation scripts

```bash
python scripts/checks/postgresql_cloud_health_check.py
python scripts/checks/lei_001_zero_local_read_validation.py --strict
python scripts/checks/railway_production_validation.py
python scripts/ops/apply_cloud_migrations.py
python scripts/ops/postgresql_cloud_backup.py
```

## Snapshots

Snapshots are persisted as files under `reports/`.

This supports:

- institutional replay;
- auditability;
- artifact download;
- model governance traces.

## Observability

Cloud observability remains lightweight:

- PostgreSQL queries via institutional adapter;
- health checks via dedicated scripts;
- deployment stability preserved.

## Stability Rules

- no destructive runtime changes to Lei 15 / Lei 15A / generation core;
- no temporal leakage introduced by cloud monitoring;
- no dependency on ephemeral local disk for operational persistence.
