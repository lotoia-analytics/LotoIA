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

LotoIA is a **Python monorepo** (no Node.js, no Docker required). See `README.md` for the canonical setup.

### Runtime

- **Python**: repo pins `3.11.15` (`.python-version`, `runtime.txt`); **Python 3.12** works on Cloud VMs. One-time: `sudo apt-get install -y python3.12-venv`.
- **Virtualenv**: `.venv/` at repo root — `source .venv/bin/activate` or `.venv/bin/pytest` directly.
- **Package manager**: `pip install -r requirements.txt` and `pip install -e .` for the `lotoia` CLI.
- **Persistence**: SQLite at `data/lotoia.db` by default; historical CSV at `data/raw/historico_lotofacil.csv`.

### Environment bootstrap (first session)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp -n .env.example .env
python scripts/init_database.py
```

### Services (manual start; only one Streamlit app per port)

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

Optional PostgreSQL (`DATABASE_URL` / `LOTOIA_DATABASE_URL`) is not required for local development.

### Gotchas

- Streamlit binds port **8501**; FastAPI uses **8000** (`API_HOST` / `API_PORT` in `.env`).
- Run `python scripts/init_database.py` if you need tables before UI tests.
- Historical analysis may read CSV (`load_draws_csv`); operational data lives in SQLite/PostgreSQL.
