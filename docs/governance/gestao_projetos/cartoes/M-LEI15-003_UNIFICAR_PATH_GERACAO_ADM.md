# M-LEI15-003 — Unificar path de geração ADM para generate_best_games

Cartão encerrado — missão concluída, validada em produção e incorporada à `main`.

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-LEI15-003` |
| **Título** | Unificar path de geração ADM para generate_best_games |
| **Projeto** | `P-LEI15-001` |
| **Tipo** | Geração / Plataforma / Constitucional crítico |
| **Data de abertura** | 2026-06-17 |
| **Data de encerramento** | 2026-06-17 |
| **Agentes** | `agent_geracao` + `agent_plataforma` + `agent_qualidade` + `agent_governanca` (fechamento) |
| **Status atual** | `CONCLUIDA` |
| **Prioridade / Risco** | `CRÍTICO` |

## Objetivo

Unificar o caminho de geração do Painel ADM para que, mesmo quando a geração for
liberada no futuro, só exista path preparado via `generate_best_games` com label
soberano `STRUCT_LEI15_CORE_CANDIDATE_002_15D_001` e guardas ADR-047.

## Path canônico obrigatório (preparado — geração ainda bloqueada)

```python
generate_best_games(
    count=...,
    pool_size=...,
    batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
    ml_enabled=False,
)
```

**Ressalva institucional:** futura liberação de geração exige missão/autorização própria,
`LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=1` e veredicto de governança — **fora do escopo
desta missão**.

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

| Código | Estado pós-validação produção |
|--------|-------------------------------|
| `BLK-GERACAO-001` | `MITIGADO` — path único preparado; geração permanece bloqueada |
| `BLK-ADM-001` | `MITIGADO` — órfãs bloqueadas |
| `BLK-CORE002-001` | `MITIGADO` — routing ADR-047 no ADM |
| `BLK-LEGACY-GEN-001` | `MITIGADO` — motor direto bloqueado |

## Escopo proibido (respeitado)

- Liberar geração (`GENERATION_ENABLED` permanece `0`)
- Alterar Núcleo LEI15_CORE_002, banco, purge, public_app, deploy manual

## Evidência Git

| Campo | Valor |
|-------|-------|
| Branch implantação | `cursor/m-lei15-003-unificar-path-geracao-cae6` |
| PR implantação | [#131](https://github.com/lotoia-analytics/LotoIA/pull/131) |
| Merge commit | `6dea9e7f50bba2565c6981b50e47b30ad0ec473f` |
| Commit entrega | `b63a1f677066495ab68b5cdd7531aeecc3765024` |
| Merge em `main` | 2026-06-17 |
| Branch fechamento | `cursor/m-lei15-003-fechamento-producao-cae6` |

## Evidência de testes

| Campo | Valor |
|-------|-------|
| Arquivo principal | `tests/dashboard/test_institutional_app_lei15_003_sovereign_path.py` |
| Resultado pós-merge | 12/12 passed (suite M-LEI15-003 em `main`) |
| Regressão M-VIS-031 | 7/7 passed (`test_institutional_app_phase1_constitutional_blocks.py`) |
| Escopo | path soberano, bloqueio legado, batch_label=None, flag=0, órfã generation |

## Evidência de deploy (Railway produção)

| Campo | Valor |
|-------|-------|
| Ambiente | `lotoia-production.up.railway.app` |
| Build marker | `institutional-adm-runtime-v8` |
| Commit em produção | `6dea9e7f50bba2565c6981b50e47b30ad0ec473f` |
| Deploy Railway | 2026-06-17T19:02:10Z (GitHub Deployments API) |
| Pendência de deploy | **NENHUMA** |
| Tipo de evidência | Textual/operacional (P1–P5) — screenshot/script HTTP **não exigidos** (M-GOV-031) |

## Confirmação textual/operacional em produção

Validação registrada no checkpoint de produção:

- Painel ADM carrega — HTTP 200 em `/`
- Streamlit `/_stcore/health` → `ok`
- Deploy Railway recebido com SHA `6dea9e7` (merge PR #131)
- Build `institutional-adm-runtime-v8` (único marker no commit mergeado)
- Geração **BLOQUEADA** — `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0`
- `_generate_direct_15_games` bloqueado — `RuntimeError` BLK-LEGACY-GEN-001
- `batch_label=None` rejeitado no contexto ADM
- Path soberano preparado exclusivamente via `generate_best_games` + label `STRUCT_LEI15_CORE_CANDIDATE_002_15D_001` + `ml_enabled=False`
- Nenhuma geração executada; nenhum purge executado
- Banco/schema inalterados; LEI15_CORE_002 inalterado; Lei 15A não reativada
- ML sem efeito operacional; `public_app` não alterado funcionalmente

## Checklist de conformidade

```text
A Autorização:     [x] OK
B Documentação:    [x] OK
C Git:             [x] OK — PR #131 mergeada
D Qualidade:       [x] OK — 12 testes M-LEI15-003 + regressão M-VIS-031
E Deploy:          [x] OK — evidência leve produção (Railway 19:02:10Z)
F Bloqueios:       [x] OK — geração bloqueada; path legado bloqueado
G Veredicto:       [x] OK
```

## Veredicto

| Campo | Valor |
|-------|-------|
| **Veredicto** | `CONCLUIDA / VALIDADA EM PRODUÇÃO / SEM PENDÊNCIA DE DEPLOY` |
| **Data** | 2026-06-17 |
| **Emitido por** | `agent_governanca` + `agent_geracao` + `agent_plataforma` + `agent_qualidade` |
| **Resumo** | PR #131 mergeada em `main`; Railway em `6dea9e7` com build `institutional-adm-runtime-v8`; path único ADM preparado; geração permanece bloqueada. |
| **Veredicto institucional** | **M-LEI15-003 ATIVA EM PRODUÇÃO — PATH ÚNICO ADM VALIDADO COM GERAÇÃO BLOQUEADA** |
| **Veredicto de fechamento** | **M-LEI15-003 FECHADA FORMALMENTE — PATH ÚNICO ADM VALIDADO EM PRODUÇÃO COM GERAÇÃO BLOQUEADA** |
| **Registro** | `REGISTRO_MISSOES_INSTITUCIONAL.md` — entrada M-LEI15-003 |

## Próxima missão autorizável

Liberação futura de geração Lei 15 — **missão separada**, com autorização explícita de
governança, validação ADR-047 e `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=1`. Esta missão
**não autoriza** geração operacional.

## Histórico de transições

| Data | De | Para | Motivo | Responsável |
|------|----|------|--------|-------------|
| 2026-06-17 | — | `EM EXECUCAO` | Priorizada pós rodada multiagente | `agent_geracao` |
| 2026-06-17 | `EM EXECUCAO` | `AGUARDANDO REVIEW` | PR #131 aberta | `agent_geracao` + `agent_plataforma` |
| 2026-06-17 | `AGUARDANDO REVIEW` | `INCORPORADA À MAIN` | Merge PR #131 | operador institucional |
| 2026-06-17 | `INCORPORADA À MAIN` | `CONCLUIDA` | Deploy Railway + checkpoint produção validado | `agent_governanca` |
