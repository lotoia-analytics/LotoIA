# LotoIA - Architectural Governance

## Official Positioning

LotoIA is a Statistical Structural Platform with Incremental Supervised Assistance.

The system prioritizes:
- statistical engineering,
- structural analysis,
- temporal validation,
- interpretability,
- scientific benchmarking.

Machine Learning is auxiliary and incremental.

Official ML assistive policy: `docs/governance/POLITICA_ML_ASSISTIVO.md`
(ADR-042 / ADR 009). Status: `POLITICA_ML_ASSISTIVO_FORMALIZADA`.

---

## Mandatory Principles

- Never break src modular architecture.
- Never introduce temporal leakage.
- Benchmarking is mandatory.
- Walk-forward validation is required for supervised models.
- Statistical logic must remain separated from persistence.
- ML must not replace structural statistical analysis.
- Interpretability has priority over model complexity.
- All experiments must be reproducible.
- Models must be versioned.
- Datasets must be versioned.
- Backtesting must remain temporally valid.

---

## Architectural Organization

- src = business logic
- tests = validation
- data = persistence
- reports = outputs
- experiments = ML governance
- snapshots = institutional evolution
- ADRs = architectural decisions

---

## Official Philosophy

LotoIA is NOT a lottery prediction system.

LotoIA is a scientific statistical platform focused on:
- structural prioritization,
- probabilistic ranking,
- hybrid statistical analysis,
- incremental supervised assistance.

---

## ML Assistive Policy (mandatory)

1. ML must not replace Law 15 or sovereign generation rules.
2. ML must not mutate sovereign rules automatically.
3. ML must not produce games without traceability.
4. ML must not act as the central predictive engine.
5. ML may assist ranking, analysis, clustering, diagnostics, and validation only.
6. Every ML contribution must be explainable, testable, reversible, and auditable.
7. Every ML evolution must pass temporal validation.
8. No model may be promoted to an institutional component without a comparative report.

---

## Cursor Cloud specific instructions

LotoIA is a **Python monorepo** (no Node.js, no Docker required). There is **no local development runtime** — operational work uses Railway PostgreSQL (Lei No 001). See `CLOUD_RUNTIME.md` and `docs/governance/RAILWAY_CLOUD_ONLY_DEPLOYMENT_2026_06_15.md`.

### Runtime

- **Python**: repo pins `3.11.15` (`.python-version`, `runtime.txt`); **Python 3.12** works on Cloud VMs. One-time: `sudo apt-get install -y python3.12-venv`.
- **Virtualenv**: `.venv/` at repo root — `source .venv/bin/activate` or `.venv/bin/pytest` directly.
- **Package manager**: `pip install -r requirements.txt` and `pip install -e .` for the `lotoia` CLI.
- **Persistence**: PostgreSQL via `DATABASE_URL` / `LOTOIA_DATABASE_URL` (Railway secrets). Historical CSV at `data/raw/historico_lotofacil.csv` is backup/export only.

### Environment bootstrap (first session)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp -n .env.example .env
# DATABASE_URL must be set (Railway PostgreSQL — injected in Cloud Agent secrets)
python scripts/ops/apply_cloud_migrations.py
python scripts/checks/postgresql_cloud_health_check.py
```

### Services (Railway production; manual start only for debugging)

| Service | Command | Port |
|---------|---------|------|
| FastAPI | `uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000` | 8000 |
| Streamlit (institutional) | `streamlit run dashboard/institutional_app.py --server.port 8501 --server.headless true` | 8501 |
| Streamlit (public/cloud) | `streamlit run dashboard/public_app.py --server.port 8501 --server.headless true` | 8501 |

`pytest` exercises the FastAPI app in-process — **no servers need to be running** for the test suite.

### Lint / test

```bash
source .venv/bin/activate
ruff check src backend dashboard tests scripts
python -m pytest
```

Unit tests may use ephemeral SQLite in `tmp_path` for isolation — that is test infrastructure, not an operational development database.

### Gotchas

- Streamlit binds port **8501**; FastAPI uses **8000** (`API_HOST` / `API_PORT` in `.env`).
- Without `DATABASE_URL`, cloud policy fails closed — do not bootstrap with `scripts/init_database.py`.
- Operational data lives in PostgreSQL only; CSV is never an operational source on institutional panels.
