# M-OPS-079 — CORE_002 Soberano Direto

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-OPS-079` |
| **Título** | CORE_002 Soberano Direto — ML como ferramenta analítica |
| **Tipo** | Refatoração Arquitetural Operacional |
| **Prioridade** | ALTA |
| **Data de abertura** | 2026-06-20 |
| **Agentes** | `agent_plataforma` (primário) + `agent_governanca` + `agent_qualidade` |
| **Depende de** | M-ML-079 (mergeada — PR #256) ✅ |
| **ADR** | `docs/adr/ADR-050-CORE002-SOBERANO-DIRETO.md` |
| **Status atual** | `CONCLUÍDA` |

## Objetivo

Reposicionar ML e Agente Operador ML de portões de aprovação para ferramentas analíticas opt-in, tornando o CORE_002 o gerador soberano direto sem variáveis de ambiente adicionais no Railway.

## Alterações

| Arquivo | Função | Default anterior | Default novo |
|---------|--------|------------------|--------------|
| `dashboard/institutional_supervised_ml.py` | `is_ml_operational_enabled()` | `"1"` | `"0"` |
| `src/lotoia/ml/ml_operational_hierarchy.py` | `is_ml_operational_hierarchy_enabled()` | `"1"` | `"0"` |
| `src/lotoia/ml/pre_final_pool_ml_calibration.py` | `is_pre_final_pool_ml_enabled()` | `"1"` | `"0"` |
| `src/lotoia/ml/agent_operador_ml_executor.py` | `is_agent_operador_ml_enabled()` | `"1"` | `"0"` |
| `src/lotoia/ml/pre_gp_deterministic_recovery.py` | `is_pre_gp_recovery_enabled()` | `"1"` | `"0"` |

## Fluxo pós-missão

```
Solicitação N jogos XD
    → CORE_002 (build_sovereign_pool + compose_sovereign_gp)
    → Política Estrutural 15D (diagnóstico, sem bloqueio)
    → Persistência PostgreSQL
    → Histórico / Cobertura / Conferência operam sobre dados persistidos
```

## Opt-in ML (Railway)

```bash
LOTOIA_ML_CORE_002_OPERATIONAL_ENABLED=1
```

## Testes

```bash
python -m pytest tests/operations/test_m_ops_079_core002_soberano_direto.py -q
python scripts/checks/governance_contract_check.py
```

## Critério de aceite

- [x] Defaults `"0"` nas 5 funções `is_*_enabled()`
- [x] `generate_best_games(count=5, ml_enabled=None)` entrega sem hierarquia ML
- [x] 15D, 17D, 20D sem env vars adicionais
- [x] ML reativável via `LOTOIA_ML_CORE_002_OPERATIONAL_ENABLED=1`
- [x] ADR-050 criado
- [x] Testes passando

## Integridade confirmada

- CORE_002, Lei 15, Lei 15A intactos
- `public_app` intacto
- Sem purge, sem alteração de schema
- Módulos ML presentes (reposicionados)
