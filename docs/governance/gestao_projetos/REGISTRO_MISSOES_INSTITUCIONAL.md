# Registro Institucional de Missões — LotoIA

Log cronológico de missões, evidências, bloqueios e veredictos.

**Modo:** Fase 0 — documental/Git (fonte: este arquivo versionado no repositório).

---

## Índice rápido

| ID | Título | Status | Veredicto |
|----|--------|--------|-----------|
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
