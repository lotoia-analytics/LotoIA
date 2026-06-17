# Auditoria Constitucional da LotoIA

| Campo | Valor |
|-------|-------|
| Registro | `AUDITORIA_CONSTITUCIONAL_LOTOIA_2026_06_17` |
| Data | 2026-06-17 |
| Agente principal | `agent_governanca` |
| Modo | **Read-only** — nenhuma alteração de código, banco, painel ou produção |
| Contexto | Pós-implantação do Núcleo Soberano `LEI15_CORE_002` |
| Export JSON | `reports/auditoria_constitucional_lotoia_2026_06_17.json` |

---

## 1. Resumo executivo

A LotoIA possui **base institucional sólida** (Lei 001 documentada e enforced em cloud, trilha ADR extensa, política ML assistivo formalizada, Núcleo Soberano LEI15_CORE_002 implantado com geração bloqueada). Porém, após a mudança de conceito da Lei 15 — de **cartão fixo de 15 dezenas** para **matriz soberana de papéis das dezenas 01–25** — o repositório permanece **constitucionalmente fragmentado**.

**Principais achados:**

- **SOBERANO operacional:** `LEI15_CORE_002` (código + ADR-046), com gate `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0`.
- **CONFLITANTE:** documento `LEI_15_NUCLEO_OPERACIONAL_15D.md`, constantes `NUCLEO_LEI15_15D_CONGELADO` e fluxo ADM `_generate_direct_15_games` ainda tratam o Núcleo como conjunto fixo `01…25`.
- **CONFLITANTE:** Lei 15A antiga (expansão 15+1/15+2, reservas mecânicas) permanece em código, painel e governança sem redefinição pós-auditoria.
- **RISCO CRÍTICO:** Painel ADM pode gerar e apagar histórico PostgreSQL sem usar o Núcleo Soberano; `public_app.py` expõe o painel institucional completo.
- **GAP Lei 001:** purge de histórico apaga `generation_events` incluindo evidências congeladas (GE 114/115, baseline EPOCH_001) — política de congelamento não protege linhas existentes.

### Respostas às 10 perguntas institucionais

| # | Pergunta | Resposta sintética |
|---|----------|-------------------|
| 1 | O que está saudável? | Lei 001 em cloud, ML assistivo subordinado, LEI15_CORE_002 implantado, 6 bases formalizadas, agentes Cursor delimitados, trilha ADR/ops read-only |
| 2 | Conflito com Lei 001? | CSV bootstrap em painel; SQLite residual no adapter; purge sem guarda de evidência institucional |
| 3 | Conflito com Lei 15? | Doc/código/painel ainda promovem núcleo fixo 15D; geração ADM bypassa LEI15_CORE_002; V1 `active` pode sequestrar GP globalmente |
| 4 | O que ficou legado? | `STRUCT_TEST_*`, motor round-robin, V2–V4, CAND-001, endpoints GET `/generate/*`, `admin_app.py`, `basic_generator.py.bak` |
| 5 | O que está duplicado? | Dois corpora ADR (`ADRs/` + `docs/adr/`); constantes núcleo 15D em 3+ locais; páginas de geração ADM (clean + generation oculta) |
| 6 | O que está obsoleto? | `LEI_15_NUCLEO_OPERACIONAL_15D` como doc-fonte soberano; `test_analysis_batch_labels.py`; `_render_generation_page` morta |
| 7 | O que mascara decisões? | `OPERATIONAL_EFFECT=False` nos labels (correto) mas painel exibe “Lei 15 soberana” enquanto chama gerador paralelo; V1 scoring paralelo no pool |
| 8 | O que atrapalha LEI15_CORE_002? | ADM não passa label soberano; doc antigo contradiz matriz; Lei 15A acopla expansão mecânica |
| 9 | O que impede Painel ADM? | `NameError` em `_run_clean_law15_generation`; rotas legadas; delete one-click; conceito UI desatualizado |
| 10 | Preservar / congelar / arquivar / remover depois? | Ver seção 18 |

### Veredicto final

**LOTOIA CONFLITANTE — EXIGE CORREÇÃO ANTES DO PAINEL**

A plataforma é **funcional** para evidência histórica e auditoria read-only, mas **não está constitucionalmente alinhada** para execução soberana via Painel ADM até correções de roteamento, documentação, Lei 15A e proteção de histórico institucional.

---

## 2. Escopo executado

**Executado (read-only):**

- Varredura de `docs/governance/`, `docs/adr/`, `ADRs/`, `src/lotoia/governance/`, `generator/`, `generation/`, `ml/`, `database/`, `dashboard/`, `backend/`, `tests/`, `scripts/ops/`, `scripts/checks/`.
- Consulta cruzada por agentes: dados, geração, estatístico, ML, qualidade, visual, plataforma.

**Não executado (conforme ordem):**

- Implementação, geração de jogos, testes de resultado, alteração de painel/API/schema/ML, limpeza de banco, promoção active, Lei 15A operacional.

---

## 3. Leis verificadas

| Lei / Política | Aderência | Achado principal |
|----------------|-----------|------------------|
| **Lei 001** (PostgreSQL soberano) | **Parcial** | Enforced em cloud; risco CSV bootstrap + purge de evidência |
| **Lei 15** (LEI15_CORE_002 matriz) | **Parcial** | Código soberano implantado; docs/painel/15A ainda no paradigma fixo |
| **Lei Missões/Agentes** | **Compatível** | 8 agentes `.cursor/rules/`; mistura ocorre no monólito, não nas regras |
| **6 bases** | **Compatível** | `POLITICA_AVALIACAO_NUCLEO_LEI15_6_BASES.md` + `lei15_core_six_bases_evaluation.py` |
| **ML assistivo** | **Compatível** | `operational_effect=false` nos artefatos oficiais; rerank não reordena por padrão |
| **Lei 15A** | **Conflitante / Suspensa** | Expansão mecânica 16D–23D + reservas 15+1 persistem; gate soberano bloqueia abertura |

---

## 4. Mapa constitucional atual

### 4.1 Leis e políticas vigentes (seleção)

| Documento | Classificação |
|-----------|---------------|
| `LEI_001_FONTE_UNICA_DA_VERDADE.md` | **SOBERANO** |
| `POLITICA_AVALIACAO_NUCLEO_LEI15_6_BASES.md` | **SOBERANO** |
| `POLITICA_ML_ASSISTIVO.md` | **SOBERANO** |
| `LEI_15_NUCLEO_OPERACIONAL_15D.md` | **CONFLITANTE** (paradigma fixo 15D vs matriz CORE_002) |
| `ADR_LEI15A_CARTAO_REGISTRO_APOSTA.md` | **SUSPEITO** (requer redefinição pós-matriz) |
| `RELATORIO_NUCLEO_ANTIGO_LEI15_BASELINE_CONGELADO_2026_06_17.md` | **EVIDÊNCIA HISTÓRICA** |
| `RELATORIO_LEI15_CORE_002_IMPLANTACAO_2026_06_17.md` | **PRESERVAR** |

### 4.2 ADRs — arco do Núcleo Lei 15

| ADR | Status | Classificação |
|-----|--------|---------------|
| ADR-043 V1 | shadow_test autorizado | **EVIDÊNCIA HISTÓRICA** |
| ADR-044 V2 | shadow_test; active bloqueado | **EVIDÊNCIA HISTÓRICA** |
| ADR-045 V3 | shadow_test | **EVIDÊNCIA HISTÓRICA** |
| ADR-NUCLEO-LEI15-CANDIDATE-001 | shadow_test CDX | **EVIDÊNCIA HISTÓRICA** |
| ADR-046 LEI15_CORE_002 | **Núcleo Soberano implantado** | **SOBERANO** |

Corpus dual: `ADRs/` (001–035) + `docs/adr/` (036–046) — classificação **SUSPEITO** (risco de referência cruzada).

### 4.3 Núcleos, flags e labels

| Componente | Env var | Default | Classificação |
|------------|---------|---------|---------------|
| **LEI15_CORE_002** | `LOTOIA_LEI15_CORE_002` | `sovereign` | **SOBERANO** |
| Geração CORE_002 | `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED` | `0` | **COMPATÍVEL** (bloqueio correto) |
| V1 | `LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1` | `off` | **EVIDÊNCIA** — **SUSPEITO** se `active` |
| V2/V3 | `LOTOIA_LEI15_15A_CORE_REALIGNMENT_V2/V3` | `off` | **EVIDÊNCIA HISTÓRICA** |
| V3.1/V4 | `LOTOIA_LEI15_CORE_REALIGNMENT_V3_1/V4` | `off` | **EVIDÊNCIA HISTÓRICA** |
| CAND-001 | `LOTOIA_LEI15_CORE_CANDIDATE_001` | `off` | **EVIDÊNCIA HISTÓRICA** |
| Legacy baseline | — | sempre disponível se `batch_label=None` | **LEGADO CONGELADO** — **CONFLITANTE** como default |

**Label soberano:** `STRUCT_LEI15_CORE_CANDIDATE_002_15D_001` → batch type `LEI15_CORE_002_SOVEREIGN`.

### 4.4 Scripts ops críticos

| Tier | Scripts | Classificação |
|------|---------|---------------|
| **Perigosos** | `run_*_test_15d.py`, `purge_core_realign_v2_ge.py`, `apply_cloud_migrations.py` | **SUSPEITO** — exigem trava ADM |
| **Auditoria** | `report_lei15_core_*`, `compare_core_realign_*way*`, `ml_decide_lei15_core_candidate.py` | **PRESERVAR** |
| **Checks** | `scripts/checks/*` (11 arquivos) | **COMPATÍVEL** |

### 4.5 Tabelas PostgreSQL críticas (Lei 001)

| Tier | Tabelas | Classificação |
|------|---------|---------------|
| Verdade oficial | `imported_contests`, `lotofacil_official_history` | **SOBERANO** |
| Cadeia operacional | `generation_events`, `generated_games`, `reconciliation_*` | **COMPATÍVEL** / evidência mista |
| Memória institucional | `scientific_institutional_memory`, `institutional_memory_*` | **PRESERVAR** |
| Purge ADM | mesmas tabelas operacionais | **CONFLITANTE** — apaga evidência congelada |

### 4.6 Pontos de execução

| Ponto | Rota / arquivo | Classificação |
|-------|----------------|---------------|
| Orquestrador canônico | `basic_generator.generate_best_games(batch_label=...)` | **SOBERANO** (se label + flags corretos) |
| Painel clean Lei 15 | `_run_clean_law15_generation` → `_generate_direct_15_games` | **CONFLITANTE** |
| API legada | `GET /generate/game`, `/games`, `/best-games` | **LEGADO CONGELADO** — **CONFLITANTE** |
| API pública | `POST /api/public/generate` | **SUSPEITO** (ML opcional no body) |
| Ops headless | `scripts/ops/run_*_test_15d.py` | **EVIDÊNCIA** — risco se env persistir |

---

## 5. Estado real da Lei 15

### 5.1 LEI15_CORE_002 como soberano

**Confirmado em código:**

- `src/lotoia/governance/lei15_core_002_sovereign.py` — status `NUCLEO_SOBERANO_LEI15`
- `src/lotoia/generation/lei15_core_002.py` — 5 camadas (CAND-D → V1 compose → shield → anti-clone → critical digits)
- `basic_generator.py` — prioridade máxima no pool e compose; `enforce_generation_policy()` fail-closed

**Conceito correto (matriz de papéis):**

| Papel | Dezenas |
|-------|---------|
| Reforço | 07, 12, 16, 23 |
| Blind spot (CAND-D) | 06, 16, 17 |
| Penalização contextual | 02, 04, 11, 15, 24, 25 |
| Sufixo controlado/preservável | 22, 23, 24, 25 |
| Prefixo controlado/preservável | 01, 02, 03 |
| Universo elegível | 01–25 |

### 5.2 Concorrentes diretos

| Concorrente | Risco de acionamento indevido | Classificação |
|-------------|------------------------------|---------------|
| Legacy `batch_label=None` | **Alto** — default em API/admin | **CONFLITANTE** |
| `_generate_direct_15_games` (ADM) | **Alto** — bypass total | **CONFLITANTE** |
| V1 `active` global | **Alto** — qualquer label | **CONFLITANTE** |
| V2–V4, CAND-001 | **Médio** — exige env+label | **EVIDÊNCIA HISTÓRICA** |
| `generate_filtered_game()` | **Médio** — API GET | **LEGADO** |

### 5.3 Evidências históricas (não soberanas isoladas)

| Lane | Label exemplo | Classificação |
|------|---------------|---------------|
| V1 | `STRUCT_REALIGN_V1_15D_001` | **EVIDÊNCIA HISTÓRICA** |
| CAND-D | `STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001` | **EVIDÊNCIA HISTÓRICA** |
| V2/V3/V4 | labels `STRUCT_CORE_*` / `STRUCT_LEI15_CORE_*` | **EVIDÊNCIA HISTÓRICA** |
| Baseline legado | `STRUCT_TEST_15D_001` | **LEGADO CONGELADO** |

**Gap:** `assert_no_new_legacy_extensive_lot()` existe mas **não está wired** em `basic_generator.py`.

---

## 6. Estado real da Lei 15A

### 6.1 Mapeamento

| Artefato | Função | Classificação |
|----------|--------|---------------|
| `lei15a_operational.py` | Núcleo fixo 15D + reservas 15/05/07/14/19; sync cartão | **CONFLITANTE** |
| `lei15_15a_core_realignment_v2/v3.py` | Realinhamentos sob missão 15+15A | **OBSOLETO** para novo paradigma |
| `clients/game_expansion.py` | Expansão 16D–23D + tag 15A | **SUSPEITO** |
| `dashboard/institutional_app.py` | `NUCLEO_LEI15A_15D_CONGELADO`, matriz formatos | **CONFLITANTE** |
| `lei15_core_002_sovereign.lei15a_operational_gate()` | `open_15a: False` | **COMPATÍVEL** |

### 6.2 Avaliação constitucional

A Lei 15A no formato **expansão mecânica 15+1/15+2** com núcleo fixo `(1,2,3,4,9,10,11,12,13,18,20,22,23,24,25)` **não faz mais sentido** como camada soberana após LEI15_CORE_002.

**Recomendação institucional (missão posterior):**

- **Suspender** operacionalmente (já gateado pelo soberano).
- **Redefinir** 15A futura como camada adaptativa complementar sobre cartões Lei 15 gerados pelo CORE_002 — nunca expansão mecânica do núcleo 15D fixo.
- **Arquivar** docs `LEI_15_NUCLEO_OPERACIONAL_15D` e `ADR_LEI15A_*` após ADR de transição.

---

## 7. Estado dos núcleos e variantes (tabela consolidada)

| ID | Classificação | Pode gerar hoje? | Notas |
|----|---------------|------------------|-------|
| LEI15_CORE_002 | **SOBERANO** | Só com `_GENERATION_ENABLED=1` + label | Matriz de papéis |
| Legacy baseline | **LEGADO CONGELADO** | Sim (default) | Deveria estar bloqueado |
| V1 | **EVIDÊNCIA HISTÓRICA** | shadow_test + label; `active` perigoso | Líder hits EPOCH_001 |
| V2/V3 | **EVIDÊNCIA HISTÓRICA** | shadow_test + label | Platô ~11 hits |
| V3.1/V4 | **EVIDÊNCIA HISTÓRICA** | shadow_test + label | Não resolveram núcleo |
| CAND-001 A–D | **EVIDÊNCIA HISTÓRICA** | shadow_test + label | CDX; GE 114/115 |
| ADM direct generator | **CONFLITANTE** | Sim via painel | Bypass soberano |
| ML decision CAND-002 | **COMPATÍVEL** | Não (diagnose only) | `ml_operational_effect=false` |

---

## 8. Estado dos históricos

### 8.1 Evidência institucional (preservar)

| Evidência | Onde | Classificação |
|-----------|------|---------------|
| Baseline EPOCH_001 GEs | PostgreSQL `generation_events` | **PRESERVAR** |
| CDX piloto GE 114 (CAND-A), 115 (CAND-D) | PostgreSQL | **PRESERVAR** |
| V1 runs `STRUCT_REALIGN_V1_15D_001` | PostgreSQL | **PRESERVAR** |
| Relatórios `reports/lei15_*_2026_06_17.*` | filesystem | **PRESERVAR** |
| ADRs 043–046 + relatórios governança | docs | **PRESERVAR** |
| Concursos oficiais | `imported_contests`, `lotofacil_official_history` | **SOBERANO** |

### 8.2 Histórico operacional / descartável (após backup)

| Tipo | Classificação pós-backup |
|------|--------------------------|
| GEs de teste não rotulados institucionalmente | **REMOVER EM ETAPA POSTERIOR** |
| `operational_logs`, `reset_events` antigos | **ARQUIVAR** |
| Session state Streamlit | **Descartável** (já é) |

### 8.3 Congelado

| Item | Classificação |
|------|---------------|
| Núcleo antigo `STRUCT_TEST_15D_001` (política) | **LEGADO CONGELADO** |
| Labels `FROZEN_LEGACY_LABELS` | **LEGADO CONGELADO** |

### 8.4 Gap crítico

**Purge ADM** (`delete_history`) executa `DELETE` em `generation_events` **sem filtro por label** — destrói evidência institucional congelada. Classificação: **CONFLITANTE** com Lei 001 + política de baseline congelado.

**Backup obrigatório antes de qualquer limpeza:** `scripts/ops/postgresql_cloud_backup.py` + export JSON dos relatórios 6 bases.

---

## 9. Estado do Painel ADM

**Arquivo:** `dashboard/institutional_app.py` (~13k linhas)  
**Entrada pública:** `dashboard/public_app.py` → carrega painel completo (**CONFLITANTE**)

| Fluxo | Problema | Classificação |
|-------|----------|---------------|
| `clean_law15_generation` | Usa `_generate_direct_15_games`, não LEI15_CORE_002 | **CONFLITANTE** |
| `_run_clean_law15_generation` | Referencia `analysis_batch_label` **indefinido** (provável `NameError`) | **CONFLITANTE** |
| Página `generation` | Removida do sidebar, ainda roteável | **SUSPEITO** |
| `delete_history` | Wipe PostgreSQL one-click | **CONFLITANTE** |
| Conceito UI | `LEI15_PANEL_CONCEPT_15D = "15D = núcleo Lei 15 (geração soberana)"` | **OBSOLETO** vs matriz |
| Batch label selector | Metadado only; não aciona CORE_002 | **COMPATÍVEL** (metadado) / **CONFLITANTE** (expectativa) |

**Ajustes necessários (missão posterior, agent_visual + agent_plataforma):**

1. Roteamento único via `generate_best_games(batch_label=STRUCT_LEI15_CORE_CANDIDATE_002_15D_001)`.
2. Remover/ocultar gerador paralelo `_generate_direct_15_games` para Lei 15.
3. Atualizar copy para “matriz de papéis 01–25”, não cartão fixo.
4. Gate de confirmação em delete + proteção por label institucional.
5. Separar `public_app` do painel ADM destrutivo.

---

## 10. Estado dos scripts ops

Ver seção 4.3. **Scripts perigosos** devem exigir token ADM + checklist governança antes de execução em Railway.

**Recomendação:** criar registro `TIER_OPS_SCRIPTS` em governança (missão posterior) classificando run/purge/migrate.

---

## 11. Estado do ML

| Aspecto | Achado | Classificação |
|---------|--------|---------------|
| `ml_operational_effect` | `False` em decisão CAND-002 e painéis diagnóstico | **COMPATÍVEL** |
| `rerank_games` | Anexa `score_ml`; **não reordena** por padrão | **COMPATÍVEL** |
| ADM / WhatsApp / messenger | `ml_enabled=False` | **COMPATÍVEL** |
| API pública | Cliente pode enviar `ml_enabled: true` | **SUSPEITO** |
| Seleção GP | Realinhamentos (não ML) alteram compose quando env+label | **EVIDÊNCIA** — fora do escopo ML |

**Risco ML baixo** para o Núcleo Soberano; risco **médio** na API pública e na confusão entre camadas estatísticas vs ML nos relatórios.

---

## 12. Estado dos testes

| Teste | Classificação |
|-------|---------------|
| `test_lei15_core_002_sovereign.py` | **PRESERVAR** |
| `test_lei15_core_candidate_001_governance.py` | **PRESERVAR** |
| `test_lei15_legacy_core_baseline_governance.py` | **PRESERVAR** |
| `test_core_realignment_v3/v3_1/v4_governance.py` | **PRESERVAR** (evidência) |
| `test_ml_lei15_core_candidate_decision.py` | **PRESERVAR** |
| `test_lei15a_operational.py` | **SUSPEITO** — aponta paradigma 15A antigo |
| `test_analysis_batch_labels.py` | **OBSOLETO** — registry EPOCH_000 desatualizado |
| Gap: testes V1/V2 governance dedicados | **INCONCLUSIVO** — cobertura indireta |

---

## 13. Riscos críticos

| # | Risco | Severidade |
|---|-------|------------|
| R1 | Painel gera Lei 15 sem LEI15_CORE_002 | **Crítico** |
| R2 | Purge apaga evidência congelada EPOCH_001 | **Crítico** |
| R3 | Doc `LEI_15_NUCLEO_OPERACIONAL_15D` contradiz matriz soberana | **Alto** |
| R4 | `public_app` = painel ADM completo | **Alto** |
| R5 | V1 `active` sequestra compose global | **Alto** |
| R6 | API GET `/generate/*` bypass institucional | **Alto** |
| R7 | Lei 15A mecânica acoplada ao painel | **Médio** |
| R8 | `NameError` em clean generation | **Médio** |
| R9 | Ops scripts com env shadow_test persistente | **Médio** |

---

## 14. Conflitos encontrados

1. **Dois conceitos de Núcleo Lei 15:** cartão fixo 15D (doc + ADM + lei15a) vs matriz CORE_002.
2. **Dois motores de geração Lei 15:** `basic_generator` vs `_generate_direct_15_games`.
3. **Lei 15A expansão mecânica** vs gate soberano `open_15a: False`.
4. **Política congelamento criação** vs **purge destruição** sem guarda.
5. **Label metadata-only** vs expectativa operacional no painel.

---

## 15. Componentes legados

`STRUCT_TEST_*`, motor round-robin, `admin_app.py`, endpoints GET legacy, `basic_generator.py.bak`, `_render_generation_page`, corpus ADR duplicado, constantes `NUCLEO_*_15D` espalhadas.

**Classificação predominante:** **LEGADO CONGELADO** / **ARQUIVAR**.

---

## 16. Componentes obsoletos

- `LEI_15_NUCLEO_OPERACIONAL_15D.md` como doc-fonte soberano atual
- Lei 15A 15+1/15+2 como expansão do núcleo fixo
- `test_analysis_batch_labels.py` (registry antigo)
- V2/V3/V4 como caminhos de evolução (já descartados institucionalmente)

---

## 17. Componentes limpáveis depois (com backup)

GEs não institucionais, logs operacionais antigos, session artifacts, `integrate_panel_9f4e376.py` (ferramenta de patch), dead code pages — **somente após backup + ADR de limpeza**.

---

## 18. Componentes a preservar

Lei 001 docs + checks; LEI15_CORE_002 código/governança; ADR-046; relatórios 6 bases; evidências PostgreSQL EPOCH_001; `scientific_institutional_memory`; políticas ML/6 bases; scripts `report_*` e `compare_*` read-only.

---

## 19. Recomendações por agente

| Agente | Recomendação (missão posterior) |
|--------|----------------------------------|
| **agent_governanca** | ADR de transição constitucional: matriz CORE_002 substitui doc fixo 15D; suspender 15A mecânica; tier ops scripts |
| **agent_dados** | Guarda DELETE por label; backup antes purge; eliminar CSV bootstrap operacional |
| **agent_geracao** | Wire `assert_no_new_legacy_extensive_lot`; deprecar default legacy; único path soberano |
| **agent_estatistico** | Recalibrar métricas legadas vs 6 bases; aposentar métricas GP50 fixo-núcleo |
| **agent_ml** | Bloquear `ml_enabled` na API pública ou exigir gate institucional |
| **agent_qualidade** | Reescrever `test_analysis_batch_labels`; testes V1/V2; regressão CORE_002 no painel |
| **agent_visual** | Unificar geração ADM → CORE_002; fix NameError; copy matriz; gate delete |
| **agent_plataforma** | Deprecar GET `/generate/*`; separar public vs ADM; auth em rotas destrutivas |

---

## 20. Saúde mental da LotoIA (classificação multi-eixo)

| Eixo | Classificação |
|------|---------------|
| Saudável | Parcial (Lei 001 cloud, CORE_002, ML subordinado) |
| Confuso | **Sim** — múltiplos núcleos nomeados “soberanos” |
| Fragmentado | **Sim** — ADR dual, variantes V1–V4 + CDX + legacy |
| Conflitante | **Sim** — doc vs código vs painel |
| Inchado | **Sim** — institutional_app ~13k linhas, dead pages |
| Instável | Moderado — bugs ADM, purge, API aberta |
| Pronto para limpeza controlada | **Sim**, após backup + ADR |
| Pronto para painel | **Não** — exige correção constitucional |
| Bloqueado por governança | Parcial — geração CORE_002 corretamente bloqueada |

---

## Veredicto final

# **LOTOIA CONFLITANTE — EXIGE CORREÇÃO ANTES DO PAINEL**

A implantação do Núcleo Soberano LEI15_CORE_002 é **real e verificável**, mas a LotoIA ainda opera com **camadas constitucionais concorrentes** (documento Lei 15 fixo, gerador ADM paralelo, Lei 15A mecânica, purge sem guarda). A correção, limpeza, redefinição 15A e atualização do Painel ADM devem seguir **missões roteadas separadas**, conforme esta auditoria.

---

*Auditoria read-only. Nenhum arquivo de runtime, banco ou painel foi alterado.*
