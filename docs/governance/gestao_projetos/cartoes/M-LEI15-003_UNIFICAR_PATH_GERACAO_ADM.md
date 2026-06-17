# M-LEI15-003 — Unificar path de geração ADM para generate_best_games

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-LEI15-003` |
| **Título** | Unificar path de geração ADM para generate_best_games |
| **Projeto** | `P-LEI15-001` |
| **Tipo** | Geração / Plataforma / Constitucional crítico |
| **Data de abertura** | 2026-06-17 |
| **Agentes** | `agent_geracao` + `agent_plataforma` + `agent_qualidade` |
| **Status atual** | `EM EXECUCAO / AGUARDANDO REVIEW` |
| **Prioridade / Risco** | `CRÍTICO` |

## Objetivo

Unificar o caminho de geração do Painel ADM para que, mesmo quando a geração for
liberada no futuro, só exista path preparado via `generate_best_games` com label
soberano `STRUCT_LEI15_CORE_CANDIDATE_002_15D_001` e guardas ADR-047.

## Path canônico obrigatório

```python
generate_best_games(
    count=...,
    pool_size=...,
    batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
    ml_enabled=False,
)
```

## Pontos de geração auditados (Painel ADM)

| Ponto | Arquivo | Tratamento M-LEI15-003 |
|-------|---------|------------------------|
| `_run_clean_law15_generation` | `institutional_app.py` | Redirecionado para `_invoke_sovereign_adm_generate_best_games` |
| `_run_institutional_generation` (15D) | `institutional_app.py` | Redirecionado para path soberano |
| `_generate_direct_15_games` | `institutional_app.py` | **Bloqueado** — não é caminho operacional |
| `_render_generation_page` / `generation` | `institutional_app.py` | Órfã — fallback / bloqueio M-VIS-031 |
| `_render_generator_page` | `institutional_app.py` | Fora de `allowed_pages` — inalcançável |

## Caminhos bloqueados

- `_generate_direct_15_games` → `RuntimeError` (`BLK-LEGACY-GEN-001`)
- `batch_label=None` no contexto ADM → `RuntimeError`
- Label não soberano no ADM → `RuntimeError`
- Geração com `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0` → payload bloqueado
- Página órfã `generation` → fallback sem geração

## Bloqueios relacionados

| Código | Estado pós-M-LEI15-003 |
|--------|------------------------|
| `BLK-GERACAO-001` | `MITIGADO` — path único preparado |
| `BLK-ADM-001` | `MITIGADO` — órfãs bloqueadas |
| `BLK-CORE002-001` | `MITIGADO` — routing ADR-047 no ADM |
| `BLK-LEGACY-GEN-001` | `MITIGADO` — motor direto bloqueado |

## Escopo proibido (respeitado)

- Liberar geração (`GENERATION_ENABLED` permanece `0`)
- Alterar Núcleo LEI15_CORE_002, banco, purge, public_app, deploy manual

## Evidência Git

| Campo | Valor |
|-------|-------|
| Branch | `cursor/m-lei15-003-unificar-path-geracao-cae6` |
| Build marker | `institutional-adm-runtime-v8` |

## Evidência de testes

| Arquivo | Escopo |
|---------|--------|
| `tests/dashboard/test_institutional_app_lei15_003_sovereign_path.py` | Path soberano, bloqueios, regressão M-VIS-031 |
| `tests/dashboard/test_institutional_app_phase1_constitutional_blocks.py` | Bloqueios Fase 1 |

## Veredicto alvo

**M-LEI15-003 CONCLUÍDA — PATH ÚNICO ADM → generate_best_games AGUARDANDO REVIEW**
