# Auditoria Constitucional Final — Painel ADM e public_app

| Campo | Valor |
|-------|-------|
| **Missão** | `M-GOV-042` |
| **Registro** | `AUDITORIA_CONSTITUCIONAL_FINAL_PAINEL_ADM_PUBLIC_APP_M_GOV_042` |
| **Data** | 2026-06-17 |
| **Modo** | **Read-only** — auditoria/documental; sem geração, purge, banco ou alteração funcional |
| **Base Git** | `main` @ `32797c9` |
| **Build ADM** | `institutional-adm-runtime-v17` |
| **Build público** | `public-surface-v1-m-plat-041` |
| **Agentes** | `agent_governanca` + `agent_plataforma` + `agent_qualidade` + `agent_visual` + `agent_dados` + `agent_geracao` + `agent_ml` + `agent_estatistico` |

---

## 1. Resumo executivo

A fase constitucional do Painel ADM institucional e do `public_app` foi **auditada e aprovada** após consolidação das missões `M-LEI15-003` a `M-PLAT-041`.

**Respostas às perguntas institucionais:**

| Pergunta | Resposta |
|----------|----------|
| O Painel ADM está constitucionalmente coerente? | **SIM** — rotas, bloqueios e governança read-only alinhados |
| Rotas críticas bloqueadas ou read-only? | **SIM** |
| Geração continua bloqueada? | **SIM** — `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0` (default) |
| Path soberano correto? | **SIM** — ADM → `generate_best_games` com label soberano |
| Purge continua bloqueado? | **SIM** |
| Lei 15A inoperante? | **SIM** — camada futura subordinada (M-GOV-038) |
| ML assistivo? | **SIM** — `generation_cmd=False`, `ml_operacional=False` |
| public_app separado do ADM? | **SIM** — default canal público (M-PLAT-041) |
| PostgreSQL fonte soberana? | **SIM** — Lei 001 enforced |
| Missões/documentos sincronizados? | **SIM** — registro, quadro e cartões coerentes |
| Testes cobrem regressão suficiente? | **SIM** — 130 testes targeted passando |
| Pendência crítica antes da próxima fase? | **NÃO** — riscos residuais documentados abaixo (baixo/médio) |

### Veredicto final

**M-GOV-042 CONCLUÍDA — AUDITORIA CONSTITUCIONAL FINAL APROVADA**

**FASE CONSTITUCIONAL DO PAINEL ADM E PUBLIC_APP ENCERRADA COM SUCESSO**

---

## 2. Tabela de validação — 30 itens obrigatórios

| # | Item | Status | Evidência |
|---|------|--------|-----------|
| 1 | LEI15_CORE_002 soberano | ✅ APROVADO | `src/lotoia/governance/lei15_core_002_sovereign.py`; testes M-VIS-033 |
| 2 | Label soberano `STRUCT_LEI15_CORE_CANDIDATE_002_15D_001` | ✅ APROVADO | `BATCH_LABEL` em `lei15_core_002_sovereign.py`; M-LEI15-003 |
| 3 | Geração bloqueada (`LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0`) | ✅ APROVADO | Default env=0; `_run_clean_law15_generation` retorna `blocked=True` |
| 4 | Path soberano `generate_best_games(..., batch_label=..., ml_enabled=False)` | ✅ APROVADO | M-LEI15-003 — `sovereign_generation_path=generate_best_games` |
| 5 | `_generate_direct_15_games` bloqueado | ✅ APROVADO | `BLK-LEGACY-GEN-001`; teste M-LEI15-003 |
| 6 | `batch_label=None` rejeitado no ADM | ✅ APROVADO | `_resolve_adm_sovereign_batch_label(None)` → RuntimeError |
| 7 | Gerador ADM CORE_002 BLOQUEADO | ✅ APROVADO | Menu + página `clean_law15_generation`; label explícito |
| 8 | Núcleo Lei 15 CORE_002 read-only | ✅ APROVADO | `institutional_core_002.py`; M-VIS-033 |
| 9 | Cobertura Estrutural + 6 Bases read-only | ✅ APROVADO | `institutional_structural_coverage.py`; M-VIS-034 |
| 10 | ML Assistivo sem efeito operacional | ✅ APROVADO | `generation_cmd=False`, `ml_operacional=False`; M-VIS-035 |
| 11 | Vazamento Lateral Constitucional read-only | ✅ APROVADO | Diagnóstico sem botões operacionais; M-VIS-035 |
| 12 | Simulação Institucional / Backtesting read-only | ✅ APROVADO | `execucao_backtest_automatica=False`; M-VIS-036 |
| 13 | Corte temporal X−1 registrado | ✅ APROVADO | `temporal_cut_rule` com X-1; M-VIS-036 |
| 14 | Conferir Resultados = auditoria lotes persistidos | ✅ APROVADO | Não gera, não simula; PostgreSQL; M-VIS-037 |
| 15 | Fonte soberana = PostgreSQL | ✅ APROVADO | Lei 001; `conference_audit`; M-DADOS-039 |
| 16 | session_state/cache/tela/CSV rejeitados como verdade | ✅ APROVADO | Alertas em conference_audit e controlled_cleanup |
| 17 | Área Restrita / Limpeza Controlada sem purge real | ✅ APROVADO | M-DADOS-039 — módulo sem `execute_purge` |
| 18 | Purge real bloqueado | ✅ APROVADO | `purge_real_status=BLOQUEADO`; `_purge_institutional_history_tables` gated |
| 19 | Lei 15A futura/subordinada/inoperante | ✅ APROVADO | M-GOV-038 — `INOPERANTE` formal |
| 20 | Mecânica 15+1/15+2 não reativada | ✅ APROVADO | Pontos constitucionais Lei 15A governance |
| 21 | public_app separado do ADM | ✅ APROVADO | M-PLAT-041 — default `render_public_app()` |
| 22 | public_app não expõe rotas ADM | ✅ APROVADO | `PUBLIC_NOT_OFFERED`; testes plat_041 |
| 23 | Railway usa `institutional_app` | ✅ APROVADO | Procfile + railway.toml |
| 24 | Rotas legadas/órfãs limpas ou bloqueadas | ✅ APROVADO | M-PLAT-040 — inventário + aliases |
| 25 | Status constitucional coerente | ✅ APROVADO | Página Status Constitucional + blocos read-only |
| 26 | Governança read-only coerente | ✅ APROVADO | M-VIS-032 + integrações M-GOV-038/039/040/041 |
| 27 | Registro/Quadro/Cartões coerentes | ✅ APROVADO | `REGISTRO_MISSOES_INSTITUCIONAL.md`, `QUADRO_PROJETOS_MISSOES.md` |
| 28 | Build marker coerente | ✅ APROVADO | v17 ADM + public-surface-v1-m-plat-041 |
| 29 | Produção HTTP 200 / health OK | ✅ APROVADO | `/_stcore/health` → 200 |
| 30 | Nenhuma geração/purge/banco/schema na auditoria | ✅ APROVADO | Missão read-only; zero alteração operacional |

**Resultado: 30/30 APROVADOS**

---

## 3. Veredicto por agente

| Agente | Veredicto | Achados |
|--------|-----------|---------|
| **agent_governanca** | ✅ APROVADO | Leis 001/15/15A, ML assistivo, registro e cartões coerentes; fase encerrável |
| **agent_plataforma** | ✅ APROVADO | Entrypoints corretos; Railway → ADM; build markers alinhados |
| **agent_qualidade** | ✅ APROVADO | 130 testes regressão passando; imports OK; suíte legada parcial obsoleta (risco residual) |
| **agent_visual** | ✅ APROVADO | Menus/labels read-only claros; public_app com disclaimers obrigatórios |
| **agent_dados** | ✅ APROVADO | Lei 001; tabelas protegidas; purge UI bloqueado |
| **agent_geracao** | ✅ APROVADO | Path soberano preparado; geração bloqueada; legacy bloqueado |
| **agent_ml** | ✅ APROVADO | Assistivo only; sem comandos operacionais |
| **agent_estatistico** | ✅ APROVADO | 6 Bases; X−1; Conferir ≠ Simulação |

---

## 4. Inventário final

### 4.1 Builds e main

| Campo | Valor |
|-------|-------|
| **main** | `32797c9` |
| **Build ADM** | `institutional-adm-runtime-v17` |
| **Build público** | `public-surface-v1-m-plat-041` |
| **Produção health** | HTTP 200 (`/_stcore/health`) |

### 4.2 Entrypoints

| Entrypoint | Papel | Railway |
|------------|-------|---------|
| `dashboard/institutional_app.py` | ADM institucional | **SIM** |
| `dashboard/public_app.py` | Canal público (default) | NÃO |
| `dashboard/app.py` | Streamlit Cloud → ADM | NÃO |
| `Procfile` / `railway.toml` | Deploy config | **SIM** → institutional |

### 4.3 Rotas ADM principais (read-only / bloqueadas)

| Rota | Estado |
|------|--------|
| Governança Institucional — read-only | Read-only |
| Núcleo Lei 15 — CORE_002 | Read-only |
| Cobertura Estrutural + 6 Bases | Read-only |
| Central ML Assistiva | Read-only / assistivo |
| Vazamento Lateral Constitucional | Read-only / diagnóstico |
| Simulação Institucional / Backtesting | Read-only |
| Conferir Resultados — Auditoria Lotes | Read-only / auditoria |
| Área Restrita — Limpeza Controlada | Read-only / purge bloqueado |
| Gerador ADM CORE_002 — BLOQUEADO | Bloqueado |
| Lei 15A (via Governança) | Inoperante / futura |

### 4.4 Bloqueios ativos

`BLK-GERACAO-001`, `BLK-PURGE-001`, `BLK-LEI001-001`, `BLK-CORE002-001`, `BLK-LEI15A-001`, `BLK-ML-OPERACIONAL-001`, `BLK-PUBLIC-APP-001`, `BLK-LEGACY-ROUTES-001`, `BLK-ADM-001`, `BLK-HISTORICO-001`

### 4.5 Missões concluídas (fase constitucional)

| ID | Título | Build evidência |
|----|--------|-----------------|
| M-LEI15-003 | Path único ADM → generate_best_games | v8+ |
| M-VIS-033 | Núcleo CORE_002 read-only | v9 |
| M-VIS-034 | Cobertura Estrutural + 6 Bases | v10 |
| M-VIS-035 | ML Assistivo + Vazamento Lateral | v11 |
| M-VIS-036 | Simulação Institucional / Backtesting | v12 |
| M-VIS-037 | Conferir Resultados / Auditoria | v13 |
| M-GOV-038 | Lei 15A inoperante | v14 |
| M-DADOS-039 | Área Restrita / Limpeza Controlada | v15 |
| M-PLAT-040 | Rotas legadas / órfãs | v16 |
| M-PLAT-041 | Separação public_app x ADM | v17 |

---

## 5. Testes executados

```bash
# Imports
python -c "import dashboard.institutional_app; import dashboard.public_app"
# + 12 módulos institucionais (core_002, structural_coverage, ml_assistive, ...)

# Regressão fase constitucional
pytest tests/dashboard/test_institutional_app_lei15_003_sovereign_path.py
pytest tests/dashboard/test_institutional_app_core_002_read_only.py
pytest tests/dashboard/test_institutional_app_vis_034_structural_coverage.py
pytest tests/dashboard/test_institutional_app_vis_035_ml_assistive.py
pytest tests/dashboard/test_institutional_app_vis_036_simulation_backtesting.py
pytest tests/dashboard/test_institutional_app_vis_037_conference_audit.py
pytest tests/dashboard/test_institutional_app_gov_038_lei15a_governance.py
pytest tests/dashboard/test_institutional_app_dados_039_controlled_cleanup.py
pytest tests/dashboard/test_institutional_app_plat_040_route_inventory.py
pytest tests/dashboard/test_institutional_app_plat_041_public_separation.py
pytest tests/dashboard/test_institutional_app_governance_read_only.py
pytest tests/dashboard/test_institutional_app_phase1_constitutional_blocks.py
pytest tests/dashboard/test_cloud_entrypoint.py
pytest tests/dashboard/test_institutional_app_gov_042_constitutional_audit.py
```

**Resultado: 136 passed** (130 regressão + 6 M-GOV-042)

---

## 6. Riscos residuais (não bloqueantes)

| Risco | Severidade | Nota |
|-------|------------|------|
| Suíte `test_institutional_dashboard.py` legada | Médio | Testes de sidebar antigo falham; não cobrem painel institucional atual |
| `test_clean_app_formats.py` — ImportError | Médio | Referência obsoleta `NUCLEO_LEI15_15D_CONGELADO`; impede pytest full suite |
| `admin_app.py` / `user_app.py` legados no repo | Baixo | Fora do entrypoint Railway; não expostos em produção |
| M-GOV-027 histórico (`LOTOIA CONFLITANTE`) | Baixo | Supersedido por correções M-LEI15-003…M-PLAT-041; manter como evidência histórica |
| public_app modo ADM via env | Baixo | Opt-in explícito; não usado em Railway produção |

---

## 7. Próximas opções de fase (não executadas)

1. **Fase operacional controlada** — liberar geração soberana com ADR + flag explícita (missão futura dedicada).
2. **Produto comercial public_app** — evoluir canal público sem expor ADM (missão comercial separada).
3. **Limpeza de testes legados** — atualizar/arquivar `test_institutional_dashboard.py` e `test_clean_app_formats.py`.
4. **Consolidação documental Lei 15** — alinhar `LEI_15_NUCLEO_OPERACIONAL_15D.md` ao paradigma matriz CORE_002 (governança).
5. **Lei 15A futura** — quando autorizada, missão dedicada subordinada ao CORE_002.

---

## 8. Confirmações de escopo da auditoria

- [x] Sem geração real
- [x] Sem purge real
- [x] Sem alteração banco/schema
- [x] Sem exclusão de histórico
- [x] LEI15_CORE_002 não alterado
- [x] Lei 15A sem efeito operacional
- [x] ML sem efeito operacional
- [x] public_app não expõe ADM completo
- [x] ADM institucional íntegro
- [x] Sem deploy manual

---

## 9. Relação com M-GOV-027

A auditoria `AUDITORIA_CONSTITUCIONAL_LOTOIA_2026_06_17.md` (M-GOV-027) identificou conflitos **antes** da rodada de correções constitucionais. Esta auditoria final (M-GOV-042) valida que as missões subsequentes **mitigaram os achados críticos do painel ADM e public_app**. M-GOV-027 permanece como registro histórico; o veredicto operacional do painel passa a ser o deste documento.

---

**Veredicto institucional:**

**M-GOV-042 CONCLUÍDA — AUDITORIA CONSTITUCIONAL FINAL APROVADA**

**FASE CONSTITUCIONAL DO PAINEL ADM E PUBLIC_APP ENCERRADA COM SUCESSO**
