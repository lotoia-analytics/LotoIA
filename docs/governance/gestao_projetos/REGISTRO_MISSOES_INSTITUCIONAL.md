# Registro Institucional de Missões — LotoIA

Log cronológico de missões, evidências, bloqueios e veredictos.

**Modo:** Fase 0 — documental/Git (fonte: este arquivo versionado no repositório).

---

## Índice rápido

| ID | Título | Status | Veredicto |
|----|--------|--------|-----------|
| [M-ML-VIS-053](#m-ml-vis-053--ativar-painel-central-ml-assistida--operacional-supervisionada) | Central ML Operacional Supervisionada | `CONCLUIDA` | `PAINEL ML ATIVO / POSTGRESQL SOBERANO` |
| [M-GER-DADOS-051](#m-ger-dados-051--persistência-16d23d--histórico-analítico--remoção-ges) | Persistência multidezena CORE_002 | `CONCLUIDA` | `16D–23D PERSISTIDOS / GE 114 REMOVIDO / 115 PRESERVADO` |
| [M-PLAT-050](#m-plat-050--corrigir-saturação-de-conexões-postgresql--sqlalchemy) | Pool PostgreSQL Streamlit | `CONCLUIDA` | `HOME ESTÁVEL / SEM QUEUEPOOL TIMEOUT` |
| [M-DADOS-049](#m-dados-049--reset-controlado-das-gerações-antigas) | Reset controlado gerações antigas | `CONCLUIDA` | `NOVA FASE 001 / POSTGRESQL VALIDADO` |
| [M-DADOS-048](#m-dados-048--card-último-concurso-monitorado--postgresql-imported_contests) | Último concurso monitorado | `CONCLUIDA` | `POSTGRESQL imported_contests / SEM RESÍDUO 5000` |
| [M-VIS-047](#m-vis-047--simplificação-operacional-da-página-de-geração-adm-core_002) | Geração ADM — simplificação operacional | `CONCLUIDA` | `PÁGINA LIMPA / JOGOS 1–100 / DEZENAS 15–23` |
| [M-VIS-046](#m-vis-046--corrigir-resíduo-visual-lei-15a-operacional-no-runtime-limpo-adm-15) | Runtime Limpo — resíduo Lei 15A | `CONCLUIDA` | `VISUAL CORRIGIDO / CORE_002 15D PRESERVADO` |
| [M-ML-045](#m-ml-045--ativação-definitiva-do-ml-operacional-supervisionado) | ML Operacional Supervisionado CORE_002 | `CONCLUIDA` | `ML SUPERVISIONADO ATIVO / POSTGRESQL + TRACE` |
| [M-GER-044](#m-ger-044--ativação-da-geração-soberana-controlada-core_002) | Geração Soberana CORE_002 | `CONCLUIDA` | `GERAÇÃO CONTROLADA ATIVA / POSTGRESQL` |
| [M-GOV-042](#m-gov-042--auditoria-constitucional-final-do-painel-adm-e-public_app) | Auditoria Constitucional Final | `CONCLUIDA` | `FASE CONSTITUCIONAL ENCERRADA / 30-30 APROVADOS` |
| [M-PLAT-041](#m-plat-041--separação-public_app-x-adm-institucional) | Separação public_app x ADM | `CONCLUIDA` | `PUBLIC_APP SEPARADO / RAILWAY ADM INTACTO` |
| [M-PLAT-040](#m-plat-040--limpeza-de-órfãs-e-rotas-legadas-do-painel-adm) | Limpeza órfãs/rotas legadas ADM | `CONCLUIDA` | `ROTAS LEGADAS BLOQUEADAS / ALIASES SEGUROS` |
| [M-DADOS-039](#m-dados-039--área-restrita--limpeza-controlada-protegida-pela-lei-001) | Área Restrita / Limpeza Controlada | `CONCLUIDA` | `PURGE BLOQUEADO / LEI 001 SOBERANA` |
| [M-GOV-038](#m-gov-038--lei-15a-redefinida-como-camada-futura-subordinada-ao-core_002) | Lei 15A redefinida / inoperante | `CONCLUIDA` | `LEI 15A FUTURA / SUBORDINADA / INOPERANTE` |
| [M-VIS-037](#m-vis-037--conferir-resultados--auditoria-de-lotes-reais-persistidos) | Conferir Resultados / Auditoria Lotes | `CONCLUIDA` | `VALIDADA EM PRODUÇÃO / SEM PENDÊNCIA DE DEPLOY` |
| [M-VIS-036](#m-vis-036--simulação-institucional--backtesting) | Simulação Institucional / Backtesting | `CONCLUIDA` | `VALIDADA EM PRODUÇÃO / SEM PENDÊNCIA DE DEPLOY` |
| [M-VIS-035](#m-vis-035--ml-assistivo--vazamento-lateral-constitucional) | ML Assistivo + Vazamento Lateral | `CONCLUIDA` | `VALIDADA EM PRODUÇÃO / SEM PENDÊNCIA DE DEPLOY` |
| [M-VIS-034](#m-vis-034--cobertura-estrutural--6-bases-refinadas-no-painel-adm) | Cobertura Estrutural + 6 Bases ADM | `CONCLUIDA` | `VALIDADA EM PRODUÇÃO / SEM PENDÊNCIA DE DEPLOY` |
| [M-VIS-033](#m-vis-033--pacote-núcleo-lei-15-no-painel-adm) | Pacote Núcleo Lei 15 ADM | `CONCLUIDA` | `VALIDADA EM PRODUÇÃO / SEM PENDÊNCIA DE DEPLOY` |
| [M-LEI15-003](#m-lei15-003--unificar-path-de-geração-adm) | Unificar path geração ADM | `CONCLUIDA` | `VALIDADA EM PRODUÇÃO / SEM PENDÊNCIA DE DEPLOY` |
| [M-RODADA-001](#m-rodada-001--rodada-multiagente-painel--core_002) | Rodada multiagente Painel / CORE_002 | `CONCLUIDA` | `INCORPORADA À MAIN` |
| [M-GOV-031](#m-gov-031--checkpoint-de-produção-simplificado) | Checkpoint produção simplificado | `CONCLUIDA` | `INCORPORADA À MAIN` |
| [M-VIS-032](#m-vis-032--governança-read-only-no-painel-adm) | Governança read-only Painel ADM | `CONCLUIDA` | `VALIDADA EM PRODUÇÃO / SEM PENDÊNCIA DE DEPLOY` |
| [M-VIS-031](#m-vis-031--painel-adm-fase-1) | Painel ADM Fase 1 bloqueios | `CONCLUIDA` | `VALIDADA EM PRODUÇÃO / SEM PENDÊNCIA DE DEPLOY` |
| [M-GOV-030](#m-gov-030--gestão-de-projetos-fase-0) | Gestão de Projetos Fase 0 | `CONCLUIDA` | `APROVADA / MERGED / INCORPORADA À MAIN` |
| [M-OPS-INC-001](#m-ops-inc-001--incidente-deploy-artefato-não-versionado) | Incidente deploy artefato não versionado | `CONCLUIDA` | `RESOLVIDO / ENCERRADO / COM PREVENÇÃO IMPLANTADA` |
| [M-GOV-027](#m-gov-027--auditoria-constitucional) | Auditoria constitucional | `AGUARDANDO_VEREDICTO` | `LOTOIA CONFLITANTE` |
| [M-LEI15-002](#m-lei15-002--implantação-lei15_core_002) | Implantação LEI15_CORE_002 | `CONCLUIDA` | `NÚCLEO SOBERANO IMPLANTADO` |
| [M-GOV-028](#m-gov-028--manutenção-institucional-contínua) | Mission 28 manutenção | `CONCLUIDA` | `APROVADO` |
| [M-OPS-015](#m-ops-015--cloud-only-railway) | Cloud-only Railway | `CONCLUIDA` | `APROVADO` |

---

## Entradas

### M-ML-VIS-053 — Ativar Painel Central ML Assistida / Operacional Supervisionada

| Campo | Valor |
|-------|-------|
| **Status** | `CONCLUIDA` |
| **Build ADM** | `institutional-adm-runtime-v32` |
| **Pré-requisito** | M-ML-045 — ML operacional supervisionado + trace PostgreSQL |

**Objetivo:** Ativar a Central ML para exibir eventos reais `ml_enabled=True` em PostgreSQL,
com decision trace, feature attribution e ML × 6 Bases — sem mock e sem session_state soberano.

**Entregáveis:** loader PostgreSQL em `institutional_supervised_ml.py`, painel em
`institutional_ml_assistive.py`, rota `central_ml_diagnostics`, testes M-ML-VIS-053.

**Veredicto:** **M-ML-VIS-053 CONCLUÍDA — CENTRAL ML OPERACIONAL SUPERVISIONADA ATIVA SOBRE POSTGRESQL**

**Cartão:** `cartoes/M-ML-VIS-053_CENTRAL_ML_OPERACIONAL_SUPERVISIONADA.md`

---

### M-GER-DADOS-051 — Persistência 16D–23D + Histórico Analítico + Remoção GEs remanescentes

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-18 |
| Agentes | `agent_geracao` + `agent_dados` + `agent_qualidade` + `agent_visual` + `agent_governanca` + `agent_estatistico` |
| Status | `CONCLUIDA` |
| Tipo | Persistência multidezena + remoção controlada |

**Correção:** Persistência CORE_002 liberada para 15D–23D; labels derivadas `STRUCT_LEI15_CORE_CANDIDATE_002_{N}D_001`; Histórico Analítico exibe batch_label/formato/ml_enabled; remoção controlada GE 114 executada; GE 1115 inexistente — GE 115 preservado aguardando confirmação.

**Build:** `institutional-adm-runtime-v27`

**Veredicto:** **M-GER-DADOS-051 CONCLUÍDA — PERSISTÊNCIA 16D–23D LIBERADA, HISTÓRICO ANALÍTICO E COBERTURA ESTRUTURAL RECEBENDO GERAÇÕES, GEs 114/1115 TRATADOS COM SEGURANÇA**

**Cartão:** `cartoes/M-GER-DADOS-051_MULTIDEZENA_PERSISTENCIA.md`

---

### M-PLAT-050 — Corrigir Saturação de Conexões PostgreSQL / SQLAlchemy no Runtime Streamlit

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-18 |
| Agentes | `agent_plataforma` + `agent_dados` + `agent_qualidade` + `agent_governanca` |
| Status | `CONCLUIDA` |
| Tipo | Correção crítica runtime |

**Correção:** Pool PostgreSQL ampliado (5/10), `get_session` com fechamento garantido, `ensure_database_schema` once-per-process, fail-safe Home/diagnósticos.

**Build:** `institutional-adm-runtime-v26`

**PR:** [#161](https://github.com/lotoia-analytics/LotoIA/pull/161)

**Veredicto:** **M-PLAT-050 CONCLUIDA — POOL POSTGRESQL CORRIGIDO, HOME ESTÁVEL, SEM QUEUEPOOL TIMEOUT**

**Cartão:** `cartoes/M-PLAT-050_POSTGRES_POOL_STREAMLIT.md`

---

### M-DADOS-049 — Reset Controlado das Gerações Antigas + Validação Histórico Analítico e Cobertura Estrutural

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Agentes | `agent_dados` + `agent_geracao` + `agent_qualidade` + `agent_governanca` + `agent_estatistico` + `agent_visual` |
| Status | `CONCLUIDA` |
| Tipo | Limpeza controlada operacional / validação recepção |

**Correção:** Dry-run + reset controlado de gerações/lotes operacionais antigos; preservação de `imported_contests`, memória científica/institucional e GE 114/115. Numeração operacional 001/002 via rótulo (sem reset de sequence). Validação Histórico Analítico e Cobertura Estrutural via PostgreSQL.

**Build:** `institutional-adm-runtime-v25`

**Veredicto:** **M-DADOS-049 CONCLUÍDA — RESET CONTROLADO EXECUTADO, NOVA FASE OPERACIONAL 001 PRONTA**

**Cartão:** `cartoes/M-DADOS-049_RESET_CONTROLADO_GERACOES.md`

---

### M-DADOS-048 — Card Último concurso monitorado — PostgreSQL imported_contests

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Agentes | `agent_dados` + `agent_visual` + `agent_governanca` + `agent_qualidade` |
| Status | `CONCLUIDA` |
| Tipo | Correção de dados / card operacional |

**Correção:** Home e Conferência usam `imported_contests` (PostgreSQL) como fonte soberana. Artefatos/outliers (ex. concurso 5000) filtrados. Divergência vs `lotofacil_official_history` reportada quando aplicável.

**Build:** `institutional-adm-runtime-v24`

**Veredicto:** **M-DADOS-048 CONCLUÍDA — CARD ÚLTIMO CONCURSO CORRIGIDO — POSTGRESQL EXIBE 3712 OU DIVERGÊNCIA DE SYNC REPORTADA**

**Cartão:** `cartoes/M-DADOS-048_ULTIMO_CONCURSO_MONITORADO.md`

---

### M-VIS-047 — Simplificação Operacional da Página de Geração ADM CORE_002

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Agentes | `agent_visual` + `agent_geracao` + `agent_governanca` + `agent_qualidade` |
| Status | `CONCLUIDA` |
| Tipo | Simplificação visual / operacional |

**Correção:** Página de geração ADM reduzida ao essencial operacional — quantidade de jogos 1–100, dezenas 15–23 (multidezena CORE_002), estratégia CORE_002 + ML supervisionado, botão Gerar lote, resultado compacto. Banners e textos longos movidos para expansores. Persistência 16D–23D bloqueada tecnicamente; 15D CORE_002 + ML preservados.

**Build:** `institutional-adm-runtime-v23`

**Veredicto:** **M-VIS-047 CONCLUÍDA — PÁGINA DE GERAÇÃO ADM CORE_002 SIMPLIFICADA, COM QUANTIDADE DE JOGOS 1–100 E SELEÇÃO DE DEZENAS 15–23**

**Cartão:** `cartoes/M-VIS-047_OPERACIONAL_GERACAO_ADM.md`

---

### M-VIS-046 — Corrigir resíduo visual Lei 15A operacional no Runtime Limpo ADM 15

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Agentes | `agent_visual` + `agent_governanca` + `agent_geracao` + `agent_qualidade` |
| Status | `CONCLUIDA` |
| Tipo | Correção visual / constitucional |

**Correção:** Removido selectbox 16D–23D e textos "Lei 15 + reserva auditada" / "Leitura operacional Lei 15A" da página Gerador ADM CORE_002. Formato fixo 15D CORE_002. Lei 15A exibida apenas como futura/inoperante.

**Build:** `institutional-adm-runtime-v21`

**Veredicto:** **M-VIS-046 CONCLUÍDA E ATIVA EM PRODUÇÃO — RESÍDUO VISUAL LEI 15A OPERACIONAL REMOVIDO / CORE_002 15D PRESERVADO**

**Cartão:** `cartoes/M-VIS-046_RUNTIME_LIMPO_LEI15A_VISUAL.md`

---

### M-ML-045 — Ativação Definitiva do ML Operacional Supervisionado

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Projeto | `P-GOV-001` / `P-ML-001` |
| Agentes | `agent_ml` + `agent_geracao` + `agent_estatistico` + `agent_dados` + `agent_governanca` + `agent_qualidade` + `agent_plataforma` |
| Status | `CONCLUIDA` |
| Tipo | ML / Geração supervisionada |

**Ativação:** `LOTOIA_ML_CORE_002_OPERATIONAL_ENABLED` default=`1`. Path único ADM via
`generate_best_games(batch_label=STRUCT_LEI15_CORE_CANDIDATE_002_15D_001, ml_enabled=True)`.

**Entregáveis:** `dashboard/institutional_supervised_ml.py`, build `institutional-adm-runtime-v20`,
smoke `scripts/ops/smoke_supervised_ml_m_ml_045.py`.

**Veredicto:** **M-ML-045 CONCLUÍDA E ATIVA EM PRODUÇÃO — ML OPERACIONAL SUPERVISIONADO ATIVO SOBRE CORE_002 COM PERSISTÊNCIA POSTGRESQL E RASTREABILIDADE**

**Smoke PostgreSQL real:** `generation_event_id=167`, `batch_label=STRUCT_LEI15_CORE_CANDIDATE_002_15D_001`, 1 jogo persistido, `ml_enabled=1`, decision trace + feature attribution + ML × 6 Bases persistidos.

**Cartão:** `cartoes/M-ML-045_ATIVACAO_ML_OPERACIONAL_SUPERVISIONADO.md`

---

### M-GER-044 — Ativação da Geração Soberana Controlada CORE_002

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Projeto | `P-GOV-001` / `P-OPS-001` |
| Agentes | `agent_geracao` + `agent_dados` + `agent_qualidade` + `agent_governanca` + `agent_plataforma` |
| Status | `CONCLUIDA` |
| Tipo | Geração / Crítica |

**Ativação:** `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED` default=`1`. Path único ADM via
`generate_best_games(batch_label=STRUCT_LEI15_CORE_CANDIDATE_002_15D_001, ml_enabled=False)`.

**Entregáveis:** `dashboard/institutional_sovereign_generation.py`, build `institutional-adm-runtime-v18`,
smoke `scripts/ops/smoke_sovereign_generation_m_ger_044.py`.

**Veredicto:** **M-GER-044 CONCLUÍDA E ATIVA EM PRODUÇÃO — GERAÇÃO SOBERANA CONTROLADA CORE_002 VALIDADA COM PERSISTÊNCIA POSTGRESQL**

**Smoke PostgreSQL real:** `generation_event_id=116`, `batch_label=STRUCT_LEI15_CORE_CANDIDATE_002_15D_001`, 1 jogo persistido, `ml_enabled=0`. Veredicto: **M-GER-044 VALIDADA COM SMOKE POSTGRESQL REAL — GERAÇÃO SOBERANA CORE_002 ATIVA E PERSISTIDA**

**Evidência Git:** merge `167d46e` — [PR #152](https://github.com/lotoia-analytics/LotoIA/pull/152) — commit `c05e135`

**Cartão:** `cartoes/M-GER-044_ATIVACAO_GERACAO_SOBERANA_CORE_002.md`

---

### M-GOV-042 — Auditoria Constitucional Final do Painel ADM e public_app

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Data encerramento | 2026-06-17 |
| Projeto | `P-GOV-001` |
| Agentes | `agent_governanca` + `agent_plataforma` + `agent_qualidade` + `agent_visual` + `agent_dados` + `agent_geracao` + `agent_ml` + `agent_estatistico` |
| Status | `CONCLUIDA` |
| Tipo | Governança / Auditoria / Consolidação |
| Risco | Médio (auditoria documental) |

**Objetivo:** Auditar consolidação da fase constitucional do Painel ADM e `public_app` após
missões M-LEI15-003 a M-PLAT-041.

**Entregáveis:**

- `docs/governance/AUDITORIA_CONSTITUCIONAL_FINAL_PAINEL_ADM_PUBLIC_APP_M_GOV_042.md`
- Tabela 30 itens obrigatórios — **30/30 APROVADOS**
- Veredicto por agente (8 agentes — todos APROVADOS)
- Testes: 130 regressão + 6 M-GOV-042 = **136 passed**

**Base auditada:** `main` @ `32797c9` — build `institutional-adm-runtime-v17`

**Bloqueios validados:** `BLK-GERACAO-001`, `BLK-PURGE-001`, `BLK-LEI001-001`, `BLK-CORE002-001`,
`BLK-LEI15A-001`, `BLK-ML-OPERACIONAL-001`, `BLK-PUBLIC-APP-001`, `BLK-LEGACY-ROUTES-001`

**Confirmações:** Sem geração, purge, banco/schema ou alteração funcional durante auditoria.
Produção health HTTP 200.

**Veredicto:** **M-GOV-042 CONCLUÍDA — AUDITORIA CONSTITUCIONAL FINAL APROVADA**

**Encerramento:** **FASE CONSTITUCIONAL DO PAINEL ADM E PUBLIC_APP ENCERRADA COM SUCESSO**

**Evidência Git:** merge `5346d0f` — [PR #150](https://github.com/lotoia-analytics/LotoIA/pull/150) — commit `9a0c927`

**Cartão:** `cartoes/M-GOV-042_AUDITORIA_CONSTITUCIONAL_FINAL.md`

**Nota M-GOV-027:** Auditoria histórica `AUDITORIA_CONSTITUCIONAL_LOTOIA_2026_06_17.md` permanece
como evidência pré-correções; veredicto operacional do painel passa a ser M-GOV-042.

---

### M-PLAT-041 — Separação public_app x ADM Institucional

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Data encerramento | 2026-06-17 |
| Projeto | `P-GOV-001` / `P-OPS-001` |
| Agentes | `agent_plataforma` + `agent_governanca` + `agent_visual` + `agent_qualidade` |
| Status | `CONCLUIDA` |
| Tipo | Plataforma / Segurança / Governança / Alto risco |
| Risco | Alto (separação de interface) |

**Objetivo:** Separar canal público `public_app` do Painel ADM institucional sem quebrar
produção Railway (`institutional_app.py`).

**Decisão aplicada (Opção A):** Railway permanece em `institutional_app.py`. `public_app.py`
default = canal público seguro; ADM via `LOTOIA_DASHBOARD_MODE=institutional` explícito.

**Entregáveis:**

- `dashboard/public_surface.py` — canal público seguro
- `dashboard/entrypoint_inventory.py` — inventário entrypoints
- `dashboard/public_app.py` — separação por modo
- `dashboard/institutional_public_separation.py` — bloco governança
- Build ADM `institutional-adm-runtime-v17`
- Build público `public-surface-v1-m-plat-041`

**Bloqueios relacionados:** `BLK-PUBLIC-APP-001`, `BLK-ADM-001`, `BLK-GERACAO-001`,
`BLK-PURGE-001`, `BLK-LEI001-001`, `BLK-CORE002-001`, `BLK-ML-OPERACIONAL-001`, `BLK-LEI15A-001`.

**Confirmações:**

- Railway entrypoint inalterado (`institutional_app.py`)
- public_app não espelha ADM por default
- Sem geração, purge, banco, Núcleo ou Lei 15A operacional

**Veredicto:** **M-PLAT-041 CONCLUÍDA E ATIVA EM PRODUÇÃO — PUBLIC_APP SEPARADO DO ADM INSTITUCIONAL COM SEGURANÇA**

**Evidência Git:** merge `1f8688a` — [PR #148](https://github.com/lotoia-analytics/LotoIA/pull/148) — commit `9d030c4`

**Cartão:** `cartoes/M-PLAT-041_SEPARACAO_PUBLIC_APP_ADM.md`

---

### M-PLAT-040 — Limpeza de Órfãs e Rotas Legadas do Painel ADM

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Data encerramento | 2026-06-17 |
| Projeto | `P-GOV-001` / `P-OPS-001` |
| Agentes | `agent_plataforma` + `agent_visual` + `agent_governanca` + `agent_qualidade` |
| Status | `CONCLUIDA` |
| Tipo | Plataforma / Visual / Governança / Defensiva |
| Risco | Médio (defensivo/read-only) |

**Objetivo:** Auditar, mapear, bloquear, redirecionar ou remover com segurança páginas órfãs,
aliases antigos e rotas legadas do Painel ADM.

**Entregáveis:**

- `dashboard/institutional_route_inventory.py`
- `docs/governance/INVENTARIO_ROTAS_PAINEL_ADM_M_PLAT_040.md`
- Aliases: `generation` → gerador bloqueado; `clear_histories`/`delete_history` → Área Restrita
- Build `institutional-adm-runtime-v16`

**Bloqueios relacionados:** `BLK-LEGACY-ROUTES-001`, `BLK-GERACAO-001`, `BLK-PURGE-001`,
`BLK-LEI001-001`, `BLK-CORE002-001`, `BLK-LEI15A-001`, `BLK-ML-OPERACIONAL-001`, `BLK-PUBLIC-APP-001`.

**Evidência Git:**

| Campo | Valor |
|-------|-------|
| Branch | `cursor/m-plat-040-rotas-legadas-cae6` |
| PR | [#146](https://github.com/lotoia-analytics/LotoIA/pull/146) |
| Merge commit | `8cc1568` |
| Commit entrega | `3cdb295` |
| Build marker | `institutional-adm-runtime-v16` |

**Evidência testes:** `tests/dashboard/test_institutional_app_plat_040_route_inventory.py` + regressões — 113/113 passed.

**Confirmações:**

- Rotas legadas não geram, não executam purge, não alteram banco
- `public_app` não alterado
- Labels constitucionais padronizados no menu

**Veredicto:** **M-PLAT-040 CONCLUÍDA E ATIVA EM PRODUÇÃO — ÓRFÃS E ROTAS LEGADAS DO ADM LIMPAS/BLOQUEADAS COM SEGURANÇA**

**Cartão:** `cartoes/M-PLAT-040_LIMPEZA_ORFAS_ROTAS_LEGADAS_ADM.md`

---

### M-DADOS-039 — Área Restrita / Limpeza Controlada protegida pela Lei 001

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Data encerramento | 2026-06-17 |
| Projeto | `P-GOV-001` / `P-OPS-001` |
| Agentes | `agent_dados` + `agent_governanca` + `agent_visual` + `agent_qualidade` + `agent_plataforma` |
| Status | `CONCLUIDA` |
| Tipo | Dados / Governança / Visual / Segurança / Read-only defensivo |
| Risco | Médio (read-only/defensivo) |

**Objetivo:** Reorganizar a área de limpeza no Painel ADM separando limpeza de sessão,
limpeza visual, dry-run e purge real bloqueado — histórico protegido pela Lei 001.

**Frase obrigatória:** Limpeza de sessão não é purge. Purge real é operação crítica,
protegida pela Lei 001, e não pode apagar evidência institucional sem missão específica,
dry-run, guarda por label e autorização.

**Entregáveis:**

- `dashboard/institutional_controlled_cleanup.py`
- Página `Área Restrita — Limpeza Controlada` com 4 abas
- Build `institutional-adm-runtime-v15`

**Bloqueios relacionados:** `BLK-PURGE-001`, `BLK-LEI001-001`, `BLK-HISTORICO-001`,
`BLK-GERACAO-001`, `BLK-CORE002-001`, `BLK-PUBLIC-APP-001`.

**Evidência Git:**

| Campo | Valor |
|-------|-------|
| Branch | `cursor/m-dados-039-limpeza-controlada-cae6` |
| PR | [#144](https://github.com/lotoia-analytics/LotoIA/pull/144) |
| Merge commit | `ae15edf` |
| Commit entrega | `7e502d1` |
| Build marker | `institutional-adm-runtime-v15` |

**Evidência testes:** `tests/dashboard/test_institutional_app_dados_039_controlled_cleanup.py` + regressões — 99/99 passed.

**Confirmações:**

- Purge real bloqueado — sem execução de DELETE pelo painel
- Limpeza de sessão ≠ purge
- PostgreSQL permanece fonte soberana
- Sem alteração de banco/schema, geração, Núcleo, Lei 15A operacional, ML ou public_app

**Veredicto:** **M-DADOS-039 CONCLUÍDA E ATIVA EM PRODUÇÃO — ÁREA RESTRITA / LIMPEZA CONTROLADA VALIDADA COM PURGE BLOQUEADO**

**Cartão:** `cartoes/M-DADOS-039_AREA_RESTRITA_LIMPEZA_CONTROLADA.md`

---

### M-GOV-038 — Lei 15A Redefinida como Camada Futura Subordinada ao CORE_002

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Data encerramento | 2026-06-17 |
| Projeto | `P-GOV-001` / `P-LEI15-001` |
| Agentes | `agent_governanca` + `agent_geracao` + `agent_estatistico` + `agent_qualidade` |
| Status | `CONCLUIDA` |
| Tipo | Governança / Constitucional / Read-only |
| Risco | Médio (documental/read-only) |

**Objetivo:** Redefinir constitucionalmente a Lei 15A como camada futura subordinada ao
`LEI15_CORE_002`, mantendo-a totalmente inoperante.

**Frase obrigatória:** A Lei 15A é uma camada futura subordinada ao LEI15_CORE_002. No estado
atual, está redefinida e inoperante: não gera, não expande, não altera Núcleo, não ativa
mecânica 15+1/15+2 e não possui efeito operacional.

**Entregáveis:**

- `docs/governance/LEI_15A_CAMADA_FUTURA_SUBORDINADA_CORE_002.md`
- `dashboard/institutional_lei15a_governance.py`
- Status Constitucional e Governança read-only atualizados
- Build `institutional-adm-runtime-v14`

**Bloqueios relacionados:** `BLK-GERACAO-001`, `BLK-CORE002-001`, `BLK-LEI15A-001`,
`BLK-ML-OPERACIONAL-001`, `BLK-PUBLIC-APP-001`.

**Evidência Git:**

| Campo | Valor |
|-------|-------|
| Branch | `cursor/m-gov-038-lei15a-redefinida-cae6` |
| PR | [#142](https://github.com/lotoia-analytics/LotoIA/pull/142) |
| Merge commit | `0c2dadb` |
| Commit entrega | `9134945` |
| Build marker | `institutional-adm-runtime-v14` |

**Evidência testes:** `tests/dashboard/test_institutional_app_gov_038_lei15a_governance.py` + regressões — 86/86 passed.

**Confirmações:**

- LEI15_CORE_002 permanece soberano
- Lei 15A não liberou geração
- Mecânica 15+1/15+2 não reativada
- Sem alteração de banco/schema, purge, ML operacional ou `public_app`

**Veredicto:** **M-GOV-038 CONCLUÍDA — LEI 15A REDEFINIDA COMO CAMADA FUTURA SUBORDINADA AO CORE_002 E INOPERANTE**

**Cartão:** `cartoes/M-GOV-038_LEI15A_REDEFINIDA_CAMADA_FUTURA.md`

---

### M-VIS-037 — Conferir Resultados / Auditoria de Lotes Reais Persistidos

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Projeto | `P-GOV-001` / `P-LEI15-001` |
| Agentes | `agent_visual` + `agent_dados` + `agent_governanca` + `agent_qualidade` + `agent_estatistico` |
| Status | `EM EXECUCAO / AGUARDANDO REVIEW` |
| Risco | Médio (read-only) |
| Branch | `cursor/m-vis-037-conferir-resultados-auditoria-cae6` |

**Objetivo:** Conferir Resultados como auditoria de lotes reais persistidos (Lei 001 / PostgreSQL),
separando conferência de simulação, session_state e geração.

**Bloqueios relacionados:** BLK-GERACAO-001, BLK-LEI001-001, BLK-PURGE-001, BLK-CORE002-001, BLK-PUBLIC-APP-001.

**Veredicto alvo:** **M-VIS-037 CONCLUÍDA — CONFERIR RESULTADOS READ-ONLY AGUARDANDO REVIEW**

**Cartão:** `cartoes/M-VIS-037_CONFERIR_RESULTADOS_AUDITORIA_LOTES.md`

---

### M-VIS-036 — Simulação Institucional / Backtesting

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Projeto | `P-GOV-001` / `P-LEI15-001` |
| Agentes | `agent_estatistico` + `agent_ml` + `agent_visual` + `agent_governanca` + `agent_qualidade` |
| Status | `EM EXECUCAO / AGUARDANDO REVIEW` |
| Risco | Médio (read-only) |
| Branch | `cursor/m-vis-036-simulacao-backtesting-cae6` |

**Objetivo:** Simulação Institucional / Backtesting read-only — walk-forward, corte temporal X-1,
separação de Conferir Resultados e geração operacional.

**Pré-requisito:** M-VIS-035 em `main` (PR #136 — merge `76031cb`).

**Veredicto alvo:** **M-VIS-036 CONCLUÍDA — SIMULAÇÃO INSTITUCIONAL / BACKTESTING READ-ONLY AGUARDANDO REVIEW**

**Cartão:** `cartoes/M-VIS-036_SIMULACAO_INSTITUCIONAL_BACKTESTING.md`

---

### M-VIS-035 — ML Assistivo + Vazamento Lateral Constitucional

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Data encerramento | 2026-06-17 |
| Projeto | `P-GOV-001` / `P-ML-001` |
| Agentes | `agent_ml` + `agent_visual` + `agent_governanca` + `agent_estatistico` + `agent_qualidade` |
| Status | `CONCLUIDA` |
| Risco | Médio (read-only) |
| Branch implantação | `cursor/m-vis-035-ml-assistivo-vazamento-lateral-cae6` |

**Objetivo:** Central ML Assistiva + Vazamento Lateral Constitucional read-only — ML como
Guardião Analítico Assistivo, sem efeito operacional automático.

**Pré-requisito:** M-VIS-034 em `main` (PR #134 — merge `a533e61`).

**Evidência Git:** PR [#136](https://github.com/lotoia-analytics/LotoIA/pull/136) — merge
`76031cb2b319b21b2f8e05a530d4ef2e64e57fde` — entrega `d7c283d74130d2d7a30823ac1282df0abd737a3c`

**Evidência produção:** `lotoia-production.up.railway.app` — build `institutional-adm-runtime-v11`
— checkpoint HTTP 200 + health `ok` — 54 testes passed.

**Veredicto:** **M-VIS-035 CONCLUÍDA E ATIVA EM PRODUÇÃO — ML ASSISTIVO + VAZAMENTO LATERAL READ-ONLY VALIDADO**

**Veredicto institucional:** **M-VIS-035 ATIVA EM PRODUÇÃO — ML ASSISTIVO + VAZAMENTO LATERAL READ-ONLY VALIDADO**

**Cartão:** `cartoes/M-VIS-035_ML_ASSISTIVO_VAZAMENTO_LATERAL.md`

---

### M-VIS-034 — Cobertura Estrutural + 6 Bases refinadas no Painel ADM

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Data encerramento | 2026-06-17 |
| Projeto | `P-GOV-001` / `P-LEI15-001` |
| Agentes | `agent_visual` + `agent_estatistico` + `agent_governanca` + `agent_qualidade` |
| Status | `CONCLUIDA` |
| Risco | Médio (read-only) |
| Branch implantação | `cursor/m-vis-034-cobertura-estrutural-6-bases-cae6` |

**Objetivo:** Refinar Cobertura Estrutural e leitura pelas 6 Bases no Painel ADM — modo
read-only, separação soberano/histórico, alertas institucionais.

**Pré-requisito:** M-VIS-033 fechada em `main` (PR #133 — merge `a2009cda`).

**Evidência Git:** PR [#134](https://github.com/lotoia-analytics/LotoIA/pull/134) — merge
`a533e61d2b55e43b0eebd61de5673417abff019c` — entrega `89fffae77474ab3662ff859d11a2dff6e81d4f18`

**Evidência produção:** `lotoia-production.up.railway.app` — build `institutional-adm-runtime-v10`
— checkpoint HTTP 200 + health `ok` — 43 testes passed.

**Veredicto:** **M-VIS-034 CONCLUÍDA E ATIVA EM PRODUÇÃO — COBERTURA ESTRUTURAL + 6 BASES READ-ONLY VALIDADA**

**Veredicto institucional:** **M-VIS-034 ATIVA EM PRODUÇÃO — COBERTURA ESTRUTURAL + 6 BASES READ-ONLY VALIDADA**

**Cartão:** `cartoes/M-VIS-034_COBERTURA_ESTRUTURAL_6_BASES_PAINEL_ADM.md`

---

### M-VIS-033 — Pacote Núcleo Lei 15 no Painel ADM

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Data encerramento | 2026-06-17 |
| Projeto | `P-GOV-001` / `P-LEI15-001` |
| Agentes | `agent_visual` + `agent_governanca` + `agent_estatistico` + `agent_qualidade` |
| Status | `CONCLUIDA` |
| Risco | Médio (read-only) |
| Branch implantação | `cursor/m-vis-033-pacote-nucleo-lei15-cae6` |

**Objetivo:** Pacote read-only **Núcleo Lei 15 — CORE_002** no Painel ADM — matriz soberana,
6 bases, cobertura orientada, evidências históricas reclassificadas.

**Pré-requisito:** M-LEI15-003 fechada em `main` (PR #131/#132).

**Evidência Git:** PR [#133](https://github.com/lotoia-analytics/LotoIA/pull/133) — merge
`a2009cda458b2044020c5d9256693e0b19950e3b` — entrega `c5ce9ad259ce414b17500e04f4556cac0a973859`

**Evidência produção:** `lotoia-production.up.railway.app` — build `institutional-adm-runtime-v9`
— deploy Railway 2026-06-17T19:55:04Z — health `ok` — tela `core_002_read_only` read-only.

**Veredicto:** **M-VIS-033 FECHADA FORMALMENTE — NÚCLEO LEI 15 READ-ONLY VALIDADO EM PRODUÇÃO**

**Veredicto institucional:** **M-VIS-033 ATIVA EM PRODUÇÃO POR EVIDÊNCIA PROPORCIONAL — NÚCLEO LEI 15 READ-ONLY VALIDADO**

**Cartão:** `cartoes/M-VIS-033_PACOTE_NUCLEO_LEI15_PAINEL_ADM.md`

---

### M-LEI15-003 — Unificar path de geração ADM para generate_best_games

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Data encerramento | 2026-06-17 |
| Projeto | `P-LEI15-001` |
| Agentes | `agent_geracao` + `agent_plataforma` + `agent_qualidade` + `agent_governanca` (fechamento) |
| Status | `CONCLUIDA` |
| Risco | Crítico |
| Branch implantação | `cursor/m-lei15-003-unificar-path-geracao-cae6` |
| Branch fechamento | `cursor/m-lei15-003-fechamento-producao-cae6` |

**Objetivo:** Unificar Painel ADM para path único `generate_best_games` com label soberano
`STRUCT_LEI15_CORE_CANDIDATE_002_15D_001`; bloquear `_generate_direct_15_games`; manter
geração bloqueada com flag `0`.

**Bloqueios tratados:** `BLK-GERACAO-001`, `BLK-ADM-001`, `BLK-CORE002-001`, `BLK-LEGACY-GEN-001`.

**Evidência Git:** PR [#131](https://github.com/lotoia-analytics/LotoIA/pull/131) — merge
`6dea9e7f50bba2565c6981b50e47b30ad0ec473f` — entrega `b63a1f677066495ab68b5cdd7531aeecc3765024`

**Evidência produção:** `lotoia-production.up.railway.app` — build `institutional-adm-runtime-v8`
— deploy Railway 2026-06-17T19:02:10Z — health `ok` — geração **BLOQUEADA**.

**Veredicto:** **M-LEI15-003 FECHADA FORMALMENTE — PATH ÚNICO ADM VALIDADO EM PRODUÇÃO COM GERAÇÃO BLOQUEADA**

**Veredicto institucional:** **M-LEI15-003 ATIVA EM PRODUÇÃO — PATH ÚNICO ADM VALIDADO COM GERAÇÃO BLOQUEADA**

**Ressalva:** futura liberação de geração exige missão/autorização própria — fora do escopo M-LEI15-003.

**Cartão:** `cartoes/M-LEI15-003_UNIFICAR_PATH_GERACAO_ADM.md`

---

### M-RODADA-001 — Rodada Multiagente Painel / CORE_002

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Projeto | `P-GOV-001` |
| Agentes | 8 agentes institucionais |
| Status | `CONCLUIDA` |
| Risco pacote | Baixo (documental/planejamento) |
| Branch | `cursor/rodada-multiagente-painel-core002-cae6` |
| Merge | PR [#130](https://github.com/lotoia-analytics/LotoIA/pull/130) — `295f1c0` |

**Objetivo:** Auditoria e organização multiagente; relatórios por domínio; política de pacotes;
fila de missões propostas — sem geração, purge ou alteração de Núcleo.

**Entregáveis:** `POLITICA_MISSOES_POR_PACOTE_LOTOIA.md`, `DIRETRIZ_EXECUCAO_MULTIAGENTE_LOTOIA.md`,
`rodada_multiagente/RELATORIO_*.md`, fechamento M-GOV-031 documental.

**Bloqueios identificados:** bypass `_generate_direct_15_games`; segregação public_app; órfãs page_keys.

**Veredicto:** **RODADA MULTIAGENTE INCORPORADA À MAIN** — M-LEI15-003 priorizada

**Cartão:** `cartoes/M-RODADA-001_RODADA_MULTIAGENTE_PAINEL_CORE002.md`

---

### M-GOV-031 — Checkpoint de produção simplificado

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Data encerramento | 2026-06-17 |
| Projeto | `P-GOV-001` |
| Agentes | `agent_governanca` (primário), `agent_plataforma` |
| Status | `CONCLUIDA` |
| Tipo | Governança / Política |

**Veredicto:** `CONCLUIDA / INCORPORADA À MAIN`

**Veredicto institucional:** **M-GOV-031 INCORPORADA À MAIN — CHECKPOINT SIMPLIFICADO OFICIALIZADO**

**Evidência Git:** PR [#129](https://github.com/lotoia-analytics/LotoIA/pull/129) — merge `1de7cfd`

**Cartão:** `cartoes/M-GOV-031_CHECKPOINT_PRODUCAO_SIMPLIFICADO.md`

---

### M-VIS-032 — Governança read-only no Painel ADM

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Data encerramento | 2026-06-17 |
| Projeto | `P-GOV-001` |
| Agentes | `agent_visual` (primário), `agent_governanca`, `agent_plataforma` |
| Status | `CONCLUIDA` |
| Tipo | Visual / Governança / Read-only |
| Pré-requisito | M-VIS-031 fechada — PR #126 merge `510cccb` |

**Objetivo:** Área read-only de Governança no Painel ADM — Gestão de Projetos, missões,
bloqueios, leis/ADRs, Git/Railway — sem ações operacionais.

**Entregáveis:** `dashboard/institutional_governance.py`, rota/menu Governança, testes, cartão M-VIS-032.

**Bloqueios exibidos (sem alterar):** `BLK-GERACAO-001`, `BLK-PURGE-001`, `BLK-ADM-001`, `BLK-DEPLOY-001`

**Evidência Git:**

| Campo | Valor |
|-------|-------|
| Branch implantação | `cursor/m-vis-032-governanca-read-only-cae6` |
| PR implantação | [#127](https://github.com/lotoia-analytics/LotoIA/pull/127) |
| Merge commit | `7df540ce3bcc3a0eae3916afdf8baaa6c97a447f` |
| Merge em `main` | 2026-06-17 |
| Branch fechamento | `cursor/m-vis-032-fechamento-cae6` |

**Evidência testes:** `tests/dashboard/test_institutional_app_governance_read_only.py` — 13/13 passed.

**Evidência deploy (Railway produção):**

| Campo | Valor |
|-------|-------|
| Ambiente | `lotoia-production.up.railway.app` |
| Build marker | `institutional-adm-runtime-v7` |
| Commit em produção | `7df540ce3bcc` |
| Deploy | via GitHub merge PR #127 — sem deploy manual |
| Pendência de deploy | **NENHUMA** |
| Tipo de evidência | Textual/operacional — screenshot/script HTTP **não exigidos** |

**Confirmação textual/operacional em produção:**

- Painel ADM carregando; build v7; commit `7df540ce3bcc`
- Governança Institucional — read-only disponível
- Gestão de Projetos Fase 0; missões M-GOV-030, M-OPS-INC-001, M-VIS-031, M-VIS-032
- Bloqueios e leis/ADRs exibidos; geração BLOQUEADA; purge PROTEGIDO; ML ASSISTIVO; Lei 15A SUSPENSA
- Sem botões operacionais na área read-only

**Veredicto:** `CONCLUIDA / VALIDADA EM PRODUÇÃO / SEM PENDÊNCIA DE DEPLOY`

**Veredicto institucional:** **M-VIS-032 ATIVA EM PRODUÇÃO — GOVERNANÇA READ-ONLY VALIDADA**

**Veredicto de fechamento:** **M-VIS-032 FECHADA FORMALMENTE — GOVERNANÇA READ-ONLY VALIDADA EM PRODUÇÃO**

**Emitido por:** `agent_governanca` + `agent_visual` + `agent_plataforma` — 2026-06-17

**Próxima missão autorizável:** a definir após fechamento da política de checkpoint simplificado (M-GOV-031).

**Cartão:** `cartoes/M-VIS-032_GOVERNANCA_READ_ONLY_PAINEL_ADM.md`

---

### M-VIS-031 — Painel ADM Fase 1: Bloqueios Constitucionais e Status mínimo

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Data encerramento | 2026-06-17 |
| Projeto | `P-GOV-001` |
| Agentes | `agent_visual` (primário), `agent_plataforma`, `agent_governanca` (fechamento) |
| Status | `CONCLUIDA` |
| Tipo | Correção constitucional defensiva |
| Base | Inventário PR #124 (`328d26f`) |

**Objetivo:** Bloqueios defensivos no Painel ADM — status constitucional, gerador bloqueado, purge
bloqueado, órfã `generation` removida, NameError corrigido.

**Entregáveis:** `dashboard/institutional_app.py`, testes Fase 1, cartão M-VIS-031.

**Bloqueios mitigados:** `BLK-GERACAO-001`, `BLK-PURGE-001`, `BLK-ADM-001` — `BLK-DEPLOY-001` removido.

**Evidência Git:**

| Campo | Valor |
|-------|-------|
| Branch implantação | `cursor/m-vis-031-painel-adm-fase1-cae6` |
| PR | [#125](https://github.com/lotoia-analytics/LotoIA/pull/125) |
| Merge commit | `a5a3f2f250b1b749d0cd0915f1a6828dadf8a731` |
| Merge em `main` | 2026-06-17 |
| Branch fechamento | `cursor/m-vis-031-fechamento-cae6` |

**Evidência testes:** `tests/dashboard/test_institutional_app_phase1_constitutional_blocks.py` — 7/7 passed.

**Evidência deploy (Railway produção):**

| Campo | Valor |
|-------|-------|
| Ambiente | `lotoia-production.up.railway.app` |
| Build marker | `institutional-adm-runtime-v6` |
| Commit em produção | `a5a3f2f250b1` |
| Deploy | via GitHub merge PR #125 — sem deploy manual |
| Pendência de deploy | **NENHUMA** |

**Confirmação visual em produção:**

- Status Constitucional visível
- Núcleo soberano: `LEI15_CORE_002`
- Label soberano: `STRUCT_LEI15_CORE_CANDIDATE_002_15D_001`
- Geração: **BLOQUEADA**
- Lei 15A: **SUSPENSA** / aguardando redefinição
- ML: **ASSISTIVO** / diagnóstico / sem efeito operacional automático
- Histórico/purge: **PROTEGIDO**
- Gestão de Projetos Fase 0 implantada
- Inventário Painel ADM aprovado pela PR #124
- Gerador ADM CORE_002 bloqueado
- Recalibração bloqueada
- Purge protegido

**Veredicto:** `CONCLUIDA / VALIDADA EM PRODUÇÃO / SEM PENDÊNCIA DE DEPLOY`

**Veredicto institucional:** **M-VIS-031 ATIVA EM PRODUÇÃO — PAINEL ADM FASE 1 VALIDADO**

**Veredicto de fechamento:** **M-VIS-031 FECHADA FORMALMENTE — PAINEL ADM FASE 1 VALIDADO EM PRODUÇÃO**

**Emitido por:** `agent_governanca` + `agent_visual` + `agent_plataforma` — 2026-06-17

**Próxima missão autorizável:** `M-VIS-032` — Governança read-only no Painel ADM

**Cartão:** `cartoes/M-VIS-031_PAINEL_ADM_FASE_1_BLOQUEIOS_CONSTITUCIONAIS.md`

---

### M-GOV-030 — Gestão de Projetos Fase 0

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Data encerramento | 2026-06-17 |
| Projeto | `P-GOV-001` |
| Agentes | `agent_governanca` (primário), `agent_plataforma` (suporte) |
| Status | `CONCLUIDA` |
| Origem | Missão institucional pós-incidente de deploy |

**Objetivo:** Implantar camada documental de Gestão de Projetos (Fase 0) sem alterar Painel ADM, geração, banco ou `LEI15_CORE_002`.

**Escopo autorizado:**

- `docs/governance/POLITICA_GESTAO_PROJETOS_LOTOIA.md`
- `docs/governance/gestao_projetos/*`
- referências em `.cursor/rules/agent_governanca.mdc`

**Escopo proibido:** Painel ADM, PostgreSQL, geração, Núcleo LEI15_CORE_002, automação destrutiva.

**Evidência Git:**

| Campo | Valor |
|-------|-------|
| Branch | `cursor/gestao-projetos-fase0-cae6` |
| PR | [#121](https://github.com/lotoia-analytics/LotoIA/pull/121) |
| Merge commit | `7a10363f39afb131bc7bd34ca8a50ec21cdfbd26` |
| Merge em `main` | 2026-06-17T16:27:21Z |
| Tipo | documental |

**Checklist:** A–G = OK; D e E = N/A (escopo documental).

**Veredicto:** `APROVADA / MERGED / INCORPORADA À MAIN`

**Veredicto institucional:** **M-GOV-030 FECHADA FORMALMENTE — GESTÃO DE PROJETOS FASE 0 APROVADA EM MAIN**

**Emitido por:** `agent_governanca` — 2026-06-17

**Nota de fechamento:** commit de registro formal em branch `cursor/m-gov-030-fechamento-cae6` após merge da PR #121.

---

### M-OPS-INC-001 — Incidente deploy artefato não versionado

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 (retroativa — registro Fase 0) |
| Data encerramento | 2026-06-17 |
| Projeto | `P-OPS-001` |
| Agentes | `agent_plataforma` (primário), `agent_governanca` (fechamento) |
| Status | `CONCLUIDA` |
| Tipo | Incidente operacional — Painel ADM |

**Descrição:** Após merge constitucional em `main`, Railway executou código novo, mas o Painel ADM
quebrou em produção por módulo ausente no Git.

**Causa raiz:** `dashboard/institutional_app.py` importava `dashboard.institutional_light_mode`,
porém `dashboard/institutional_light_mode.py` existia apenas localmente e ficou fora do
commit/deploy.

**Erro em produção:**

```text
ModuleNotFoundError: Nenhum módulo chamado 'dashboard.institutional_light_mode'
```

**Impacto:** Painel ADM inoperante em produção até aplicação de hotfix.

**Correção aplicada:**

| Campo | Valor |
|-------|-------|
| Commit hotfix | `f0c1261e927d2a33c50f7b9b04bc925aa43213d0` |
| Mensagem | `fix(dashboard): add missing institutional_light_mode module for ADM panel boot` |
| Arquivo | `dashboard/institutional_light_mode.py` (+121 linhas) |

**Confirmação de produção:**

| Campo | Valor |
|-------|-------|
| Build marker | `build=institutional-adm-runtime-v6` |
| Commit em produção | `f0c1261e927d` |
| Estado | Painel ADM operacional pós-hotfix |

**Ação preventiva:** M-GOV-030 — Gestão de Projetos Fase 0 (`CONCLUIDA`) — [PR #121](https://github.com/lotoia-analytics/LotoIA/pull/121), [PR #122](https://github.com/lotoia-analytics/LotoIA/pull/122).

**Bloqueios removidos:** `BLK-GIT-001`, `BLK-DEPLOY-001`

**Veredicto:** `RESOLVIDO / ENCERRADO / COM PREVENÇÃO IMPLANTADA`

**Veredicto institucional:** **M-OPS-INC-001 ENCERRADO FORMALMENTE — INCIDENTE RESOLVIDO COM PREVENÇÃO IMPLANTADA**

**Emitido por:** `agent_governanca` + `agent_plataforma` — 2026-06-17

**Lições institucionais:**

1. Todo import do Painel ADM deve ter arquivo correspondente versionado antes do merge em `main`.
2. Incidentes exigem registro com causa raiz, commit e validação de produção (Regra 8).
3. M-GOV-030 institui gates Git/teste/deploy/veredicto para evitar recorrência.
4. Build marker (`institutional-adm-runtime-v6`) serve como evidência de runtime correto.

**Cartão:** `cartoes/M-OPS-INC-001_INCIDENTE_DEPLOY_ARTEFATO_NAO_VERSIONADO.md`

---

### M-GOV-027 — Auditoria constitucional

| Campo | Valor |
|-------|-------|
| Data | 2026-06-17 |
| Agente | `agent_governanca` |
| Status | `AGUARDANDO_VEREDICTO` |
| Documento | `AUDITORIA_CONSTITUCIONAL_LOTOIA_2026_06_17.md` |

**Resumo:** Plataforma funcional para auditoria read-only, porém constitucionalmente fragmentada após implantação LEI15_CORE_002.

**Veredicto preliminar (relatório):** `LOTOIA CONFLITANTE — EXIGE CORREÇÃO ANTES DO PAINEL`

**Missões derivadas sugeridas:**

- M-LEI15-001 (alinhamento ADM/doc) — `BLOQUEADA`
- correção purge evidência Lei 001 — backlog

---

### M-LEI15-002 — Implantação LEI15_CORE_002

| Campo | Valor |
|-------|-------|
| Data | 2026-06-17 |
| Agente | `agent_geracao` |
| Status | `CONCLUIDA` |
| ADR | ADR-046 |
| Relatório | `RELATORIO_LEI15_CORE_002_IMPLANTACAO_2026_06_17.md` |

**Veredicto:** `NÚCLEO SOBERANO LEI 15 IMPLANTADO`

**Ressalva:** `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0` — geração bloqueada até missão autorizada.

---

### M-GOV-028 — Manutenção institucional contínua

| Campo | Valor |
|-------|-------|
| Data | política formalizada em Mission 28 |
| Agente | `agent_governanca` |
| Status | `CONCLUIDA` |
| Documento | `MISSION_28_CONTINUOUS_MAINTENANCE_POLICY.md` |

**Veredicto:** `APROVADO` — política de manutenção recorrente ativa.

---

### M-OPS-015 — Cloud-only Railway

| Campo | Valor |
|-------|-------|
| Data | 2026-06-15 |
| Agente | `agent_plataforma` |
| Status | `CONCLUIDA` |
| Documento | `RAILWAY_CLOUD_ONLY_DEPLOYMENT_2026_06_15.md` |

**Veredicto:** `APROVADO` — Lei 001 operacional em cloud; PostgreSQL como fonte única.

**Nota:** validações SHA subsequentes devem referenciar este registro e atualizar evidência de deploy quando o SHA ativo mudar.

---

## Modelo de nova entrada

Copiar e preencher ao abrir missão:

```markdown
### M-___-___ — Título

| Campo | Valor |
|-------|-------|
| Data abertura | YYYY-MM-DD |
| Projeto | P-___-___ |
| Agente | agent___ |
| Status | PROPOSTA |

**Objetivo:**

**Escopo autorizado:**

**Escopo proibido:**

**Evidência Git:** branch / commits / PR

**Evidência testes:** N/A ou comando + resultado

**Evidência deploy:** N/A ou SHA + checklist

**Bloqueios:**

**Veredicto:** pendente | APROVADO | ...
```

---

## Regras do registro

1. Entradas são **append-only** — não apagar histórico; corrigir com nova nota datada.
2. Veredicto formal é obrigatório antes de status `CONCLUIDA` no quadro.
3. Incidentes operacionais devem gerar entrada aqui em até um ciclo Git.
4. Export JSON futuro (Fase 1+) não substitui este arquivo na Fase 0.

---

## Referências

- [`QUADRO_PROJETOS_MISSOES.md`](QUADRO_PROJETOS_MISSOES.md)
- [`POLITICA_GESTAO_PROJETOS_LOTOIA.md`](../POLITICA_GESTAO_PROJETOS_LOTOIA.md)
- [`GOVERNANCA_OPERACIONAL_LOTOIA.md`](../GOVERNANCA_OPERACIONAL_LOTOIA.md) — Regra 8 (incidentes)
