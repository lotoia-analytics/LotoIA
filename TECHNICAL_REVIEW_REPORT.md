# LotoIA Technical Review & Performance Report

## Scope

Mission 6.6 reviewed LotoIA for technical debt, performance, memory safety,
runtime stability, SQLite behavior, Streamlit execution, and SaaS readiness.

The review preserved:

- modular `src` architecture;
- ML pipeline, `score_ml`, and walk-forward validation;
- cloud runtime contracts;
- Streamlit deployment surface;
- structural dashboard behavior;
- SQLite table contracts;
- observability and institutional standardization contracts.

## Improvements Implemented

### SQLite Optimization

Added conservative SQLite runtime configuration in the administrative dashboard:

- `busy_timeout` centralized through `SQLITE_BUSY_TIMEOUT_MS`;
- `journal_mode = WAL` when supported;
- `synchronous = NORMAL` when supported;
- bootstrap execution guarded against cloud/runtime restrictions.

Added indexes for frequent read paths:

- generation event ordering;
- generation event lead lookup;
- check event ordering;
- check event lead lookup;
- check contest lookup;
- lead ordering;
- lead identity lookup;
- operational log ordering;
- operational log event/status lookup;
- audit ordering;
- audit action lookup.

These indexes preserve the existing schema and only improve lookup/order paths.

### Streamlit Runtime Optimization

Standardized heavy dashboard caches with:

- bounded TTL;
- bounded cache entries;
- explicit constants for operational tuning.

Affected cache families:

- historical dataset loading;
- analytics base tables;
- ML governance training result cache;
- draw loading;
- generation helpers;
- backtest and benchmark helpers;
- calibration helpers;
- statistics loading;
- run history;
- observability tables;
- admin event tables;
- lead history.

This reduces long-lived memory growth in cloud sessions while preserving
existing rerender semantics.

### Analytics Performance

Optimized lead analytics aggregation.

Before:

- each lead filtered generation/check DataFrames independently;
- repeated boolean filtering caused unnecessary runtime overhead as the event
  tables grew.

After:

- generation and check events are grouped once;
- summaries are merged into the lead table;
- history is capped by `LEAD_HISTORY_LIMIT`.

This prepares the dashboard for higher event volume without changing displayed
metrics or operational semantics.

### Memory & Runtime Safety

Added operational limits:

- `ADMIN_EVENT_LIMIT`;
- `LEAD_HISTORY_LIMIT`;
- `STREAMLIT_CACHE_TTL_SECONDS`;
- `STREAMLIT_CACHE_MAX_ENTRIES`;
- table whitelist for admin event loading.

The admin event loader now rejects unknown table names by returning an empty
DataFrame, avoiding accidental dynamic SQL expansion.

### Cleanup

Reduced import overhead by removing unused imports introduced around the
dashboard review path.

Centralized repeated magic numbers as institutional constants for future SaaS
configuration.

## Risks Found

- `dashboard/admin_app.py` remains a large orchestration module. It is stable,
  but still concentrates UI, persistence reads, reports, analytics, and ML
  governance orchestration.
- Some older generated files and backups remain in the repository, such as
  dashboard backups and historical report artifacts. They were not removed to
  avoid destructive cleanup.
- SQLite remains adequate for the current institutional runtime, but future
  SaaS multi-tenant evolution will require a formal persistence boundary,
  tenant isolation, and externalized connection lifecycle.
- Streamlit cache invalidation is now bounded by TTL, but write-heavy future
  usage may need explicit cache clearing after selected mutations.

## Debt Residual

- Split dashboard orchestration only in a future controlled mission, with tests
  per page/service boundary.
- Introduce a dedicated query module if SaaS volume grows beyond current admin
  analytics requirements.
- Add migration governance if SQLite indexes continue expanding.
- Move operational constants to environment-aware config when deployment needs
  different cloud profiles.

## SaaS Readiness Assessment

Current state after review:

- safer SQLite contention behavior;
- faster frequent admin queries;
- bounded Streamlit cache memory;
- lower analytics aggregation overhead;
- improved runtime guardrails;
- preserved institutional governance and scientific boundaries.

The platform is better prepared for SaaS evolution, but true SaaS readiness
still depends on future tenant-aware persistence, authz/authn governance,
rate-limit policy, and production observability backends.

## Verification

Executed:

```powershell
python -m pytest tests\test_standardization_contracts.py tests\observability\test_observability_contracts.py tests\ml\test_institutional_ml.py tests\integration\test_institutional_flow.py tests\dashboard\test_institutional_dashboard.py tests\runtime\test_cloud_hardening.py
```

Result:

- 15 passed;
- 1 non-functional pytest cache warning caused by local `.pytest_cache`
  permission restrictions.
