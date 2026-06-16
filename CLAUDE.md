# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

LotoIA is a **statistical structural platform with incremental supervised assistance** for analyzing LOTOFACIL lottery results. It is **not** a prediction system — it provides structural prioritization, probabilistic ranking, and historical analysis. ML is auxiliary and never replaces the core statistical engine.

## Environment setup (cloud-only)

There is **no local development runtime**. Operational persistence is PostgreSQL on Railway (Lei No 001).

For Cursor Cloud agents and CI:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp -n .env.example .env
# DATABASE_URL must point to Railway PostgreSQL (injected via secrets)
python scripts/ops/apply_cloud_migrations.py
python scripts/checks/postgresql_cloud_health_check.py
```

## Common commands

```powershell
# Run all tests (no servers needed — FastAPI runs in-process)
python -m pytest

# Run a single test file
python -m pytest tests/path/to/test_file.py

# Lint
ruff check src backend dashboard tests scripts

# Install CLI after code changes
pip install -e .

# Start FastAPI (port 8000)
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# Start institutional dashboard (port 8501)
streamlit run dashboard/institutional_app.py --server.port 8501 --server.headless true

# Start public dashboard (port 8501)
streamlit run dashboard/public_app.py --server.port 8501 --server.headless true

# Run CLI
lotoia institutional-analytics
python -m lotoia --help
```

## Architecture

### Monorepo layout

```
src/lotoia/        # All business logic (264+ modules)
backend/           # FastAPI routes (main.py entry point)
dashboard/         # Streamlit UIs (institutional_app.py, public_app.py)
tests/             # pytest suite
scripts/           # Utility CLI tools (init_database.py, etc.)
data/              # Historical CSV (backup/export) — not operational truth
docs/              # Technical docs and governance policies
ADRs/              # Architecture Decision Records (40+)
experiments/       # ML governance and supervised validation artifacts
snapshots/         # Institutional evolution records
.cursor/rules/     # Domain-specific agent rules (.mdc)
```

### Key src/lotoia modules

| Module | Responsibility |
|--------|---------------|
| `generator/` | Core game generation (Lei 15 / Lei 15A sovereign rules) |
| `statistics/` | Frequency, delays, distributions, structural scoring |
| `ml/` | Interpretable ML scoring and reranking (auxiliary only) |
| `database/` | SQLAlchemy models, schema, repositories |
| `public/` | Public API workflows, rate limiting, lead capture |
| `governance/` | Institutional decisions and audit trail |
| `backtesting/` | Temporal validation (walk-forward mandatory) |
| `experiments/` | ML governance and comparative benchmarking |
| `config.py` | Pydantic settings loaded from `.env` |

### Data flow

1. **Generation**: Statistical ranking → candidate games → optional ML reranking
2. **Conference**: Validate contest results against user selections
3. **Analytics**: Historical + institutional analysis from CSV and DB
4. **ML**: Score calculation → supervised reranking with full traceability

### Persistence

- **Operational truth**: PostgreSQL on Railway.app (`DATABASE_URL` / `LOTOIA_DATABASE_URL`)
- Historical draws: `data/raw/historico_lotofacil.csv` (backup/export only — not operational source)
- Lei No 001: PostgreSQL is the **only** operational source of truth
- SQLite fallback in code exists for legacy/unit-test isolation only — not for development or production

### Cloud runtime

Railway is detected via `RAILWAY_*` env vars, `LOTOIA_CLOUD_ONLY=1`, or `APP_ENV=production`. Without a valid PostgreSQL `DATABASE_URL`, `enforce_cloud_runtime_policy()` fails closed.

## Architectural constraints (mandatory)

These rules are enforced by governance and must not be violated:

- **Lei 15 / Lei 15A are sovereign** — never modify generation rules automatically or via ML
- **No temporal leakage** — all feature engineering must be gated by contest dates; walk-forward validation is required for any supervised model
- **ML is auxiliary** — ML may assist ranking, clustering, and diagnostics but must not replace the statistical pipeline or act as the central predictive engine
- **Interpretability over complexity** — every ML contribution must be explainable, testable, reversible, and auditable
- **Statistical logic stays separated from persistence** — business logic in `src/lotoia/`, not in `database/` or `backend/`
- **ADRs required** — changes to `FINAL_SCORE_WEIGHTS`, new generators, ML model promotions, or `validation_threshold` require an ADR in `ADRs/`
- **Artifact naming convention**: `lotoia_<type>_<name>_<YYYYMMDDTHHMMSSZ>.<ext>`

## Cursor agent domains

The `.cursor/rules/` directory defines agent scopes:

| Agent | Domain |
|-------|--------|
| `agent_dados` | Data ingestion and CSV/DB pipeline |
| `agent_estatistico` | Statistical analysis and scoring |
| `agent_geracao` | Game generation (Lei 15 enforcement) |
| `agent_governanca` | ADRs, weight changes, ML promotion approval |
| `agent_ml` | ML models, walk-forward validation |
| `agent_plataforma` | FastAPI backend and infrastructure |
| `agent_qualidade` | Tests, ruff, CI |
| `agent_visual` | Streamlit dashboard and charts |
