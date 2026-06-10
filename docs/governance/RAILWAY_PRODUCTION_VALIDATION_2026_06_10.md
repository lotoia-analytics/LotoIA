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

## 4. Resultado missão `MERGE_PR_30_AND_RUN_RAILWAY_VALIDATION`

| Escopo | Status | Notas |
|--------|--------|-------|
| PR #30 merge | **PASS** | `2026-06-10T06:29:59Z`, merge commit `9046305` |
| Deploy Railway | **PASS** | SHA `9046305`, state `success` (`2026-06-10T06:31:35Z`) |
| CI governance-gate | **PASS** | headSha `9046305` |
| `RAILWAY_FULL_VALIDATION` | **FAIL** | Agente sem shell Railway / `DATABASE_URL`; comando deve rodar no Railway |

**Nota SHA:** após merge #30 o deploy ativo é `9046305` (não `f263197`). Usar:
`python scripts/checks/railway_production_validation.py --expected-sha 9046305`

### Execução agente (2026-06-10T06:31Z)

```text
deploy-only --expected-sha 9046305 → PASS
full --expected-sha 9046305        → FAIL (DATABASE_URL ausente)
full --expected-sha f263197          → FAIL (SHA mismatch + DATABASE_URL ausente)
```

---

## 5. Próxima ação (`next_action`)

**Pré-requisito:** merge PR #30 (script de validação) e redeploy Railway antes do comando abaixo.

```yaml
next_action:
  id: RAILWAY_FULL_VALIDATION
  where: Railway shell
  command: "python scripts/checks/railway_production_validation.py --expected-sha f263197"
  expected:
    - backend_postgresql_ok
    - institutional_tables_ok
    - lotofacil_official_history_populated
    - get_latest_official_contest_ok
    - RAILWAY_VALIDATION_STATUS_PASS
```

## 6. Sequência pós-validação

```yaml
sequence:
  - encerrar_AUD_005_pos_deploy
  - revisar_mergear_PR_25_AUD_006
  - promover_baseline_de_approved_candidate_para_approved_production
```

| Etapa | Critério de conclusão |
|-------|----------------------|
| `encerrar_AUD_005_pos_deploy` | Checklist em `LOTOIA_INSTITUTIONAL_BASELINE_2026_06_10.md` + `AUD_005_STATUS=ENCERRADO_POS_DEPLOY` |
| `revisar_mergear_PR_25_AUD_006` | PR #25 mergeado; fechar PR #24 (duplicado) |
| `promover_baseline` | `status: approved_production` em `snapshots/baselines/LOTOIA_INSTITUTIONAL_BASELINE_2026_06_10.yaml` |
