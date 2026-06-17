# M-ML-045 — Ativação Definitiva do ML Operacional Supervisionado

| Campo | Valor |
|-------|-------|
| Missão | M-ML-045 |
| Status | CONCLUIDA |
| Build ADM | `institutional-adm-runtime-v19` |
| Pré-requisito | M-GER-044 — geração soberana CORE_002 validada |

## Objetivo

Ativar ML operacional supervisionado exclusivamente sobre geração soberana CORE_002, com
pontuação, reranking, decision trace, feature attribution e persistência PostgreSQL.

## Path autorizado

```python
generate_best_games(
    count=...,
    pool_size=...,
    batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
    ml_enabled=True,
)
```

## Flag institucional

| Variável | Default | Efeito |
|----------|---------|--------|
| `LOTOIA_ML_CORE_002_OPERATIONAL_ENABLED` | `1` | ML supervisionado ativo no ADM |
| `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED` | `1` | Pré-requisito geração soberana |

## Status operacional

`ML OPERACIONAL SUPERVISIONADO — ATIVO SOBRE CORE_002`

## Entregáveis

- `dashboard/institutional_supervised_ml.py`
- Integração ADM: `_invoke_sovereign_adm_generate_best_games`, persistência trace ML
- Central ML Assistiva: status operacional + decision trace + ML × 6 Bases
- Smoke: `scripts/ops/smoke_supervised_ml_m_ml_045.py`
- Testes: `tests/dashboard/test_institutional_app_ml_045_supervised_ml.py`

## Proibições mantidas

- Alterar LEI15_CORE_002 / Lei 15A / public_app / batch_label=None
- `_generate_direct_15_games`, purge, schema, hit isolado como veredicto
- ML sem trace ou sem persistência PostgreSQL

## Veredicto alvo

**M-ML-045 CONCLUÍDA E ATIVA EM PRODUÇÃO — ML OPERACIONAL SUPERVISIONADO ATIVO SOBRE CORE_002 COM PERSISTÊNCIA POSTGRESQL E RASTREABILIDADE**
