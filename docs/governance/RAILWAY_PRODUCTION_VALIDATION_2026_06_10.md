# Validação Railway — Produção

## Identificação

| Campo | Valor |
|-------|-------|
| Baseline | `LOTOIA_INSTITUTIONAL_BASELINE_2026_06_10` |
| Data | 2026-06-10 |
| Commit baseline (PR #28) | `f263197` |
| Script | `scripts/checks/railway_production_validation.py` |

---

## 1. Merge baseline (#28)

| Verificação | Resultado |
|-------------|-----------|
| PR #28 estado | **MERGED** (`2026-06-10T06:11:50Z`) |
| Commit | `f2631974103f309542fbfe7211902801f783b518` |
| Artefatos | `docs/governance/LOTOIA_INSTITUTIONAL_BASELINE_2026_06_10.md`, `snapshots/baselines/LOTOIA_INSTITUTIONAL_BASELINE_2026_06_10.yaml` |

---

## 2. Deploy Railway (evidência GitHub)

| Verificação | Resultado |
|-------------|-----------|
| Deploy production mais recente | `2026-06-10T06:11:55Z` |
| SHA deployado | `f263197` (alinhado ao merge #28) |
| Estado deploy | **success** |
| Ambientes | `considerate-curiosity / production`, `meticulous-creativity / production` |
| CI `governance-gate` (main) | **success** (`2026-06-10T06:11:52Z`) |

---

## 3. Critérios operacionais PostgreSQL

Executar no shell Railway (ou ambiente com `DATABASE_URL` de produção):

```bash
python scripts/checks/railway_production_validation.py --expected-sha f263197
```

### Critérios mínimos (baseline `validar_producao_railway_estavel`)

| Critério | Como validar |
|----------|--------------|
| `DATABASE_URL` → PostgreSQL | Script: `InstitutionalDatabaseAdapter.backend == postgresql` |
| Auditoria Runtime | Script: `_database_snapshot()["backend"] == postgresql` |
| Histórico oficial | `lotofacil_official_history` com `COUNT > 0` |
| Concurso mais recente | `get_latest_official_contest()` retorna `contest_number` |
| Tabelas institucionais | `generation_events`, `reconciliation_runs`, etc. consultáveis |
| Sync Caixa `commit_state=ok` | Painel institucional → sync manual; não exibir sucesso sem commit |
| Pool / sessão aninhada | Hotfix #19 em produção; sem timeout em Auditoria Runtime |

### Modo deploy-only (sem DATABASE_URL)

Para validar apenas deploy + CI a partir de qualquer ambiente com `gh` autenticado:

```bash
python scripts/checks/railway_production_validation.py --deploy-only --expected-sha f263197
```

---

## 4. Resultado desta execução (agente CI)

| Escopo | Status | Notas |
|--------|--------|-------|
| Merge #28 | **PASS** | Confirmado via `gh pr view 28` |
| Deploy Railway | **PASS** | SHA `f263197`, state `success` |
| CI governance-gate | **PASS** | main verde pós-merge |
| PostgreSQL operacional | **PENDENTE** | `DATABASE_URL` indisponível no ambiente do agente; executar script no Railway |

---

## 5. Próximo passo (`next` baseline)

1. Rodar script completo no Railway shell → registrar `RAILWAY_VALIDATION_STATUS=PASS`
2. `encerrar_AUD_005_pos_deploy` — checklist em `LOTOIA_INSTITUTIONAL_BASELINE_2026_06_10.md`
3. `executar_AUD_006_DB_FIRST_HAI` — merge PR #25
