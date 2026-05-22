# Production SaaS Readiness Checklist

## Bootstrap

- [x] Entry points remain lightweight.
- [x] Heavy subsystems are loaded lazily.
- [x] Startup smoke tests exist for runtime boot.
- [x] Cold-start import cascades are guarded.

## Runtime

- [x] SQLite bootstrap is explicit and resilient.
- [x] Dashboard startup remains bounded.
- [x] Workflow and observability packages are lazy.
- [x] User and admin entrypoints are hardened.

## Recovery

- [x] Runtime fallback paths exist for report generation.
- [x] Recovery-aware SQLite access remains in place.
- [x] Cloud rebuild remains the only external variable.

## Governance

- [x] Entry point import policy is documented.
- [x] ADR-021, ADR-022, and ADR-023 remain in place.
- [x] Runtime validation stays separate from scientific logic.
- [x] Mission 28 maintenance policy is documented.
- [x] Institutional maintenance is governed as a recurring practice.
