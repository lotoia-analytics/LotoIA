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

### Stack

Python monorepo (no Node.js, no Docker required). See `README.md` for the canonical setup commands.

- **Python**: 3.11+ (repo pins 3.11.15 in `.python-version`; Python 3.12 works on Cloud VMs).
- **Package manager**: `pip` + `requirements.txt`; install the package with `pip install -e .` so the `lotoia` CLI resolves.
- **Persistence**: SQLite at `data/lotoia.db` by default; historical CSV at `data/raw/historico_lotofacil.csv`.

On a fresh Ubuntu VM, `python3 -m venv` may require `sudo apt-get install -y python3.12-venv` once before the first venv creation.

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

| Service | Command | URL |
|---------|---------|-----|
| FastAPI | `uvicorn backend.main:app --reload` | http://127.0.0.1:8000 |
| Streamlit (institutional) | `streamlit run dashboard/app.py` | http://127.0.0.1:8501 |
| Streamlit (public/cloud) | `streamlit run dashboard/public_app.py` | http://127.0.0.1:8501 |

`pytest` exercises the FastAPI app in-process and imports dashboard modules directly — **no servers need to be running** for the test suite.

### Lint / test

```bash
source .venv/bin/activate
ruff check .
python -m pytest
```

`ruff check` may report pre-existing style issues; `pytest` currently has some failing tests on `main` (569+ pass). No Makefile or CI lint gate is defined in-repo.

### Gotchas

- Activate `.venv` (or call `.venv/bin/python` / `.venv/bin/pytest`) before running commands.
- Streamlit binds port **8501**; FastAPI uses **8000** (`API_HOST` / `API_PORT` in `.env`).
- The dashboard bootstraps SQLite schema on first run via `bootstrap_institutional_database`; run `python scripts/init_database.py` if you need tables before starting UI tests.
- Historical analysis reads the CSV directly (`load_draws_csv`); the SQLite DB tracks operational/generated games separately from the CSV history.