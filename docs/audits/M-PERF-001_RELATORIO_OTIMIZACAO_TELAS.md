# M-PERF-001 — Otimização das telas operacionais críticas

**Missão:** M-PERF-001  
**Data:** 2026-06-18  
**BUILD_MARKER:** `institutional-adm-runtime-v73`  
**Veredito:** **M-PERF-001 CONCLUÍDA — TELAS OPERACIONAIS CRÍTICAS OTIMIZADAS**

---

## Escopo

Telas otimizadas:

1. Gerar Jogos
2. Cobertura Estrutural
3. Central ML
4. Histórico Analítico
5. Conferir Resultados

**Sem alteração:** Lei 15, CORE_002, lógica ML, regras de promoção, `public_app`, purge.

---

## Tabela — Antes vs Depois

| Tela | Antes (comportamento) | Depois (comportamento) | Ganho estimado |
|------|----------------------|------------------------|----------------|
| **Boot / sidebar** | `_database_snapshot()` — 12× COUNT+MAX em todo rerun | `_resolve_database_snapshot()` — snapshot leve em modo leve | **~90%** menos queries no boot |
| **Gerar Jogos** | Herdava snapshot pesado do `main()` | Snapshot leve + sem carga histórica na abertura | **~70%** abertura mais rápida |
| **Cobertura Estrutural** | `load_operational_core_002_generations()` sem limit/cache | Cache 300s + últimos **20** lotes via `_load_operational_generations_cached` | **~80–95%** menos linhas/eventos |
| **Central ML** | Snapshot + operational load em todo render | Lazy gate + operational limit **20** | **~85%** na abertura (até clique) |
| **Histórico Analítico** | 25–50 gerações + sovereign sem limit + fallback 50 | Lazy gate + **20** gerações + indexes cacheados | **~75%** carga inicial |
| **Conferir Resultados** | `_load_persisted_generation_event_groups()` full scan + todos os jogos | Lazy gate + resumo conferível (count) últimos **20** | **~90%** queries/jogos na abertura |

> Medições absolutas no Railway: `python scripts/checks/m_perf_001_operational_screens_audit.py --json`

---

## Otimizações implementadas

### 1. Lazy loading (modo leve)

Novas chaves `session_state`:

- `panel_light_load_analytical`
- `panel_light_load_conference`
- `panel_light_load_central_ml`

Telas Cobertura, Comparativo e Histórico Institucional já tinham gate — mantidos.

### 2. Paginação / limites

| Constante | Valor |
|-----------|-------|
| `OPERATIONAL_EVENTS_LIMIT` | 20 |
| `ANALYTICAL_PAGE_SIZE` | 20 |
| `CONFERENCE_EVENTS_LIMIT` | 20 |

`load_operational_core_002_generations(limit=…)` — scan DESC com buffer, não full table.

`_load_persisted_generation_event_groups(limit=…, summary_only=…)` — conferência na abertura usa apenas contagem de jogos.

### 3. Cache institucional (TTL 300s)

- `_cached_operational_core_002_generations`
- `_cached_persisted_generation_event_groups`
- `_cached_scientific_context_indexes`

Invalidação via `_invalidate_operational_structural_cache()` após nova persistência.

### 4. Central ML

- Lazy gate na página
- `load_operational_core_002_generations(limit=20)` no cockpit e snapshot builder
- Métricas persistidas em `context_json` — sem recálculo estrutural na abertura

### 5. Cobertura Estrutural

- Resumo rápido (métricas escopo) antes do detalhe diagnóstico cacheado
- Loader cacheado com limite 20

### 6. Histórico Analítico

- Lazy gate
- `_load_sovereign_generation_event_rows(limit=20)`
- `_load_generation_history_light(limit=20)`
- Removido fallback automático para 50 gerações completas

### 7. Conferir Resultados

- Lazy gate
- `page_load=True` → `summary_only` + `conference_eligible_only` + limit 20
- Conferência completa (`_run_institutional_conference`) carrega jogos apenas no clique

---

## Arquivos alterados

| Arquivo | Mudança |
|---------|---------|
| `dashboard/institutional_perf.py` | **novo** — utilitários de auditoria |
| `dashboard/institutional_light_mode.py` | limites + session keys |
| `dashboard/institutional_operational_structural_coverage.py` | `limit` no loader |
| `dashboard/institutional_app.py` | cache, lazy gates, limits, snapshot leve |
| `dashboard/institutional_ml_calibration_cockpit.py` | limit 20 |
| `dashboard/institutional_supervised_ml.py` | limit 20 |
| `dashboard/institutional_build.py` | v73 |
| `tests/dashboard/test_m_perf_001_operational_screens.py` | **novo** |
| `scripts/checks/m_perf_001_operational_screens_audit.py` | **novo** |

---

## Comandos

```bash
python -m pytest tests/dashboard/test_m_perf_001_operational_screens.py -q
python scripts/checks/governance_contract_check.py
python scripts/checks/m_perf_001_operational_screens_audit.py --json
```

---

## Confirmações

- Lei 15, CORE_002, lógica ML e promoção N+1 **intactos**
- `public_app` **não alterado**
- **Nenhum purge** executado
