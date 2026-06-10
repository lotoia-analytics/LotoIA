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

LotoIA is a **Python monorepo** (no Node.js). Standard setup is documented in `README.md`.

### Runtime

- **Python**: repo pins `3.11.15` (`.python-version`, `runtime.txt`); **Python 3.12** works on Cloud VMs when 3.11 is unavailable. One-time system package: `python3.12-venv`.
- **Virtualenv**: `.venv/` at repo root. Activate with `source .venv/bin/activate` before CLI commands, or call `.venv/bin/pytest`, `.venv/bin/ruff`, etc. directly.
- **Import layout**: `lotoia_runtime.ensure_src_layout()` bootstraps `src/lotoia` imports; the editable install (`pip install -e .`) registers the `lotoia` CLI.

### Services (manual start — not in the update script)

| Service | Command | Port |
|---------|---------|------|
| FastAPI | `uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000` | 8000 |
| Streamlit dashboard | `streamlit run dashboard/app.py --server.port 8501 --server.headless true` | 8501 |

Run both from `/workspace` with the venv active. SQLite DB defaults to `data/lotoia.db` (init: `python scripts/init_database.py`). Historical CSV is bundled at `data/raw/historico_lotofacil.csv`. Copy `.env.example` → `.env` for local config.

Production-parity Streamlit entry: `streamlit run dashboard/institutional_app.py --server.port 8501`.

### Lint, test, and quick smoke checks

- **Lint**: `ruff check src backend dashboard tests scripts` (no project `ruff.toml`; pre-existing findings are common).
- **Tests**: `pytest` from repo root (~600+ tests; some failures may exist on `main` — API/dashboard smoke tests do not require a running server).
- **API smoke**: `curl http://127.0.0.1:8000/health` and `curl http://127.0.0.1:8000/generate/game`.
- **CLI smoke**: `python scripts/run_basic_analysis.py` or `lotoia --help`.

Optional PostgreSQL (`DATABASE_URL` / `LOTOIA_DATABASE_URL`) is not required for local development.