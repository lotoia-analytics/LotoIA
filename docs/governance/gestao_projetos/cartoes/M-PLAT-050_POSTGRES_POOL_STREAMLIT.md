# M-PLAT-050 — Corrigir saturação de conexões PostgreSQL / SQLAlchemy

| Campo | Valor |
|-------|-------|
| Missão | M-PLAT-050 |
| Tipo | Correção crítica runtime / pool PostgreSQL |
| Build ADM | `institutional-adm-runtime-v26` |

## Problema

`QueuePool limit of size 1 overflow 0 reached` ao carregar Home e boot do painel ADM.

## Correção

- Pool PostgreSQL: `pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`, `pool_recycle=120`, `pool_timeout=30`
- `get_session` como context manager com `session.close()` garantido
- `ensure_database_schema` — schema uma vez por processo (sem `create_all` a cada rerun)
- Fail-safe: `_load_imported_contests_summary`, `_load_official_history_diagnostics`, Home

## Veredicto alvo

**M-PLAT-050 CONCLUÍDA — POOL POSTGRESQL CORRIGIDO, HOME ESTÁVEL, SEM QUEUEPOOL TIMEOUT**
