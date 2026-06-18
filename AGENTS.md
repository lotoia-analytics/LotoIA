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
- **DATABASE_URL soberano (M-PLAT-063)**: no Railway, use `${{Postgres.DATABASE_URL}}` — nunca o texto literal `DATABASE_URL`. `DATABASE_PUBLIC_URL` é workaround temporário (proxy TCP público) só quando `DATABASE_URL` estiver inválido; o código promove a URL resolvida para `DATABASE_URL` em runtime. Guia: `docs/governance/M_PLAT_063_DATABASE_URL_RAILWAY.md`.

### Environment bootstrap (first session)

Dependencies (`.venv` + `requirements.txt` + `pip install -e .`) are refreshed automatically by the Cloud Agent update script on startup. To run the operational DB scripts manually:

```bash
source .venv/bin/activate
python scripts/ops/apply_cloud_migrations.py
python scripts/checks/postgresql_cloud_health_check.py
```

Do **not** run `cp .env.example .env`: the `Settings` model (`src/lotoia/config.py`) forbids extra keys, and `.env.example` ships many integration keys (Evolution/Messenger/Asaas) — a copied `.env` makes the whole `pytest` collection fail with `extra_forbidden`. Leave `.env` absent and rely on OS env vars (all `Settings` fields have safe defaults).

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
ruff check src backend dashboard tests scripts   # whole-tree; currently reports pre-existing lint debt
python -m pytest                                  # whole suite; NOT green (see below)
```

Unit tests may use ephemeral SQLite in `tmp_path` for isolation — that is test infrastructure, not an operational development database. Do **not** export `DATABASE_URL` when running `pytest`: it forces SQLite-based tests onto the real PostgreSQL and breaks them.

**What CI actually gates** (`.github/workflows/governance-gate.yml`) is the source of truth, not the whole tree:

```bash
ruff check scripts/checks tests/governance/test_branch_protection_artifacts.py
python -m compileall -q dashboard/institutional_app.py scripts/checks
python -m pytest tests/test_clean_app_formats.py tests/dashboard/test_cloud_entrypoint.py tests/governance/test_branch_protection_artifacts.py -q
python scripts/checks/governance_contract_check.py
```

The full `ruff check ...` tree and full `python -m pytest` both have many **pre-existing** failures (hundreds of lint findings; ~220 test failures that assume specific DB/data state). Treat the CI subset above as the real gate; don't assume a clean full-tree run.

### Gotchas

- Streamlit binds port **8501**; FastAPI uses **8000** (`API_HOST` / `API_PORT`).
- Without `DATABASE_URL`, cloud policy fails closed — do not bootstrap with `scripts/init_database.py`.
- Operational data lives in PostgreSQL only; CSV is never an operational source on institutional panels.
- **Auth on the Cloud VM**: `is_auth_required()` is False unless a `RAILWAY_*` env var, `APP_ENV=production`, or `LOTOIA_CLOUD_ONLY=1` is set — so the institutional dashboard opens without a login on the Cloud VM. To force the login gate, set `LOTOIA_AUTH_REQUIRED=1` (plus `LOTOIA_ADMIN_EMAIL` / `LOTOIA_ADMIN_PASSWORD` to bootstrap an admin).
- **Generation is gated by ADR-047 (`LEI15_GENERATION_ROUTING_ADR_047`)**: the legacy/default generation path is blocked. The HTTP endpoints `/generate/game`, `/generate/games`, `/generate/best-games`, and `POST /api/public/generate` all currently error (`batch_label=None` blocked) — this is by design, not a setup bug. The only sanctioned path passes `batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001"`, e.g. `generate_best_games(count=2, pool_size=20, batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001")`. The institutional dashboard's "Gerador ADM CORE_002 — Geração Soberana Controlada" panel uses this sanctioned path and generates successfully.
