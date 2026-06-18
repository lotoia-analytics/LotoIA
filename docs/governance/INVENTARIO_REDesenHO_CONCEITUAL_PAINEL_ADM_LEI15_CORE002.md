# Inventário e Redesenho Conceitual do Painel ADM — LEI15_CORE_002

| Campo | Valor |
|-------|-------|
| Registro | `INVENTARIO_REDesenHO_CONCEITUAL_PAINEL_ADM_LEI15_CORE002` |
| Data | 2026-06-17 |
| Agentes | `agent_visual` (primário), `agent_plataforma`, `agent_governanca` |
| Modo | **Read-only** — diagnóstico e proposta documental |
| Runtime produção | `dashboard/institutional_app.py` via `public_app.py` |
| Build referência | `institutional-adm-runtime-v6` (hotfix `f0c1261`) |
| Veredicto | **INVENTÁRIO DO PAINEL ADM CONCLUÍDO — AGUARDANDO REVIEW** |

**Local do relatório:** `docs/governance/INVENTARIO_REDesenHO_CONCEITUAL_PAINEL_ADM_LEI15_CORE002.md`

> **Justificativa de path:** o caminho solicitado `docs/governance/reports/` está bloqueado
> pelo `.gitignore` (`reports/`). Seguindo o padrão institucional existente
> (`RELATORIO_*`, `AUDITORIA_*`), o relatório foi versionado diretamente em
> `docs/governance/`.

---

## 1. Sumário executivo

O Painel ADM em produção (`institutional_app.py`, ~13.400 linhas) foi restaurado após o hotfix
`f0c1261`, mas permanece **conceitualmente desalinhado** com a constituição vigente:

- **LEI15_CORE_002** soberano (ADR-046), geração bloqueada (`GENERATION_ENABLED=0`);
- **ADR-047** registrando transição constitucional — painel **não atualizado**;
- **Lei 15A operacional suspensa** (expansão mecânica 15+1/15+2 ainda visível no gerador);
- **Núcleo fixo 15D** (`NUCLEO_LEI15A_15D_CONGELADO`) ainda tratado como referência operacional;
- **Gestão de Projetos Fase 0** implantada em Git, **ausente** no painel;
- **ML assistivo** parcialmente correto na Central, mas risco de leitura operacional em outras telas;
- **public_app.py** expõe o painel institucional completo sem segregação pública/ADM.

### Achados críticos (prioridade máxima)

| # | Achado | Risco |
|---|--------|-------|
| C1 | `_run_clean_law15_generation` referencia `analysis_batch_label` **não definido** (L11909) | `NameError` em runtime — geração ADM quebrada |
| C2 | Geração ADM usa `_generate_direct_15_games` — **bypass** de `LEI15_CORE_002` e ADR-047 | Geração paralela ao núcleo soberano |
| C3 | `batch_label=None` possível no caminho legado | Motor baseline legado como default |
| C4 | `delete_history` pode apagar evidência institucional sem guarda por label | Conflito Lei 001 + ADR-047 |
| C5 | `public_app.py` importa `institutional_app.main()` integralmente | Superfície ADM exposta em entrypoint público |
| C6 | Páginas órfãs (`generation`, `_render_generation_page`) ainda no código e em `allowed_pages` | Risco de reativação acidental |
| C7 | Textos promovem Lei 15A mecânica e núcleo fixo 15D | Conflito ADR-047 / auditoria constitucional |
| C8 | V3 batch como default em Cobertura Estrutural (`institutional_light_mode`) | V3 apresentado como referência, não CORE_002 |

### Recomendação institucional

**Não implementar redesign de uma só vez.** Aprovar este inventário, depois executar em fases:
(1) bloqueios e correções de risco, (2) governança read-only no painel, (3) núcleo CORE_002,
(4) operação ADM, (5) área restrita e purge protegido.

---

## 2. Estado atual do Painel ADM

### 2.1 Superfícies de runtime

| Superfície | Arquivo | Status | Observação |
|------------|---------|--------|------------|
| **Produção Railway** | `dashboard/institutional_app.py` | **Ativo** | Entry via `public_app.py` |
| **Public wrapper** | `dashboard/public_app.py` | **Ativo** | Delega 100% ao institutional |
| **Legacy ADM** | `dashboard/admin_app.py` | **Legado** | Mission 29; não é entry Railway |
| **Light mode** | `dashboard/institutional_light_mode.py` | **Ativo** | Lazy-load; default batch V3 |

### 2.2 Constituição de referência

| Documento | Relação com o painel |
|-----------|---------------------|
| `LEI15_CORE_002` / ADR-046 | Soberano em código; **não refletido** no menu/gerador ADM |
| ADR-047 | Autoriza atualização do painel **após** este registro |
| Lei 001 | Painel deve ler PostgreSQL; purge sem guarda de evidência = gap |
| Política ML assistivo | Central ML aderente; outras telas precisam reforço |
| Gestão de Projetos Fase 0 | Documental/Git; **ausente** no painel |
| Auditoria constitucional 2026-06-17 | Veredicto: `LOTOIA CONFLITANTE — EXIGE CORREÇÃO ANTES DO PAINEL` |

### 2.3 Modelo de navegação atual

Sidebar **plana** em 6 grupos (sem toggle Operacional/Analítico). Session key:
`institutional_page_id`. Build/commit exibidos na sidebar.

---

## 3. Mapa completo dos menus atuais

### 3.1 Sidebar de produção (22 entradas navegáveis)

```
Núcleo Operacional
├── Painel Inicial Institucional          [home]
├── Gerador ADM - Lei 15 Limpo             [clean_law15_generation]
├── Conferir Resultados                    [conference]
└── Simular Resultados                     [simulation]

Históricos e Rastreabilidade
├── Histórico Analítico                    [history_analytical]
├── Histórico Institucional                [history_institutional]
└── Comparativos histórico                 [comparative_history]

Auditoria Observacional
├── Auditoria Runtime                      [audit]
├── Conferência por concurso               [audit_monitoring_conference]
├── Dezenas faltantes                      [audit_monitoring_missing_numbers]
└── Dezenas sobrando                       [audit_monitoring_extra_numbers]
    Analítico observacional
    ├── Benchmark resumido                 [summary_benchmark]
    ├── Métricas HB                        [hb_metrics]
    └── Cobertura estrutural               [structural_coverage]

Diagnósticos ML
├── Central de Diagnósticos ML             [central_ml_diagnostics]
├── Vazamento lateral                      [audit_monitoring_side_leak]
├── Evolução 13 -> 14                      [audit_monitoring_13_to_14]
└── Evolução 14 -> 15                      [audit_monitoring_14_to_15]

Área bloqueada / restrita
├── Limpar Históricos                      [clear_histories]
└── Apagar Histórico                       [delete_history]
```

### 3.2 Home — acesso rápido (6 atalhos)

`clean_law15_generation`, `conference`, `history_analytical`, `history_institutional`,
`audit`, `structural_coverage`.

### 3.3 Páginas órfãs (código presente, não no sidebar)

| page_key | Função | Em `allowed_pages`? |
|----------|--------|---------------------|
| `generation` | `_render_generator_page` | Sim |
| — | `_render_generation_page` | Não despachada (código morto) |
| — | `_render_operational_page` | Não despachada |
| — | `_render_history_page` | Não despachada |
| `audit_monitoring` | overview | Não no sidebar |
| `audit_monitoring_group_performance` | grupo | Não no sidebar |
| `audit_monitoring_offline_hypotheses` | hipóteses | Não no sidebar |
| `strategies_*` | estratégias | Não em `allowed_pages` → fallback |
| `institutional_replay` | replay | Não |
| `operational_statistics` | estatísticas | Não |
| `hb_geometry` | geometria HB | Fallback via `main()` else |

### 3.4 Legacy `admin_app.py` (referência Mission 29 — não produção)

16+ page keys com modo Operacional/Analítico. Diverge totalmente do painel Railway atual.

---

## 4. Tabela tela por tela — diagnóstico e decisão proposta

Legenda de **status futuro:** manter | renomear | reestruturar | fundir | bloquear | ocultar |
mover para legado | mover para public_app | read-only | remover após autorização

| # | Nome atual | Função atual | Arquivo / função | Risco constitucional | Conflito encontrado | Decisão proposta | Novo nome proposto | Novo conceito | Status futuro |
|---|------------|--------------|------------------|----------------------|---------------------|------------------|-------------------|---------------|---------------|
| 1 | Painel Inicial Institucional | Home, atalhos, status V3 | `_render_home_page` | Médio | Exibe `CORE_REALIGN_V3_BATCH_LABEL` como referência; sem Status Constitucional CORE_002 | Reestruturar | **Status Constitucional LotoIA** | Dashboard de governança: CORE_002, gates, ADR-047, M-GOV-030 | reestruturar + read-only |
| 2 | Gerador ADM - Lei 15 Limpo | Geração 15–23D via `_generate_direct_15_games` | `_render_clean_law15_generation_page` / `_run_clean_law15_generation` | **CRÍTICO** | Bypass CORE_002; Lei 15A mecânica; `NameError` em `analysis_batch_label`; expansão 16–23D sem suspensão explícita | Bloquear até Fase 2 | **Gerador ADM CORE_002 — Bloqueado** | Geração só via label soberano quando `GENERATION_ENABLED=1` | **bloquear** → reestruturar |
| 3 | Conferir Resultados | Conferência oficial PostgreSQL | `_render_conference_page` / `_run_institutional_conference` | Baixo | Aderente Lei 001 se usa banco institucional | Manter | **Conferência de Resultados** | Conferência oficial persistida | manter |
| 4 | Simular Resultados | Simulação session-only | `_render_simulation_page` | Médio | Não persiste; pode confundir com reconciliação operacional | Renomear | **Simulação Institucional (session)** | Comparação efêmera; sem efeito em banco | renomear + read-only |
| 5 | Histórico Analítico | Leitura analítica PostgreSQL | `_render_analytical_page` | Baixo | — | Manter | **Histórico Analítico** | Leitura analítica Lei 001 | read-only |
| 6 | Histórico Institucional | Memória HB, políticas, calibração | `_render_history_institutional_page` | Médio | Blocos científicos podem sugerir recalibração | Manter com guardas | **Histórico Institucional Protegido** | Evidência congelada; sem mutação | read-only + reestruturar |
| 7 | Comparativos histórico | Geração vs concurso oficial | `_render_comparative_history_page` | Baixo | Linguagem de "frequência" pode parecer recomendação | Manter | **Comparativos Históricos** | Observacional; sem promessa | read-only |
| 8 | Auditoria Runtime | COUNT(*) live + cloud policy | `_render_runtime_audit_page` | Baixo | — | Fundir parcialmente | **Auditoria Runtime / Railway** | Snapshot operacional + Git/deploy | manter + fundir com governança |
| 9 | Conferência por concurso | Monitoramento pós-draw | `_render_audit_monitoring_page("conference")` | Baixo | — | Manter | **Conferência por Concurso** | Observacional pós-conferência | read-only |
| 10 | Dezenas faltantes | Drilldown faltantes | `_render_audit_monitoring_page("missing_numbers")` | Baixo | — | Manter | **Dezenas Faltantes** | Observacional | read-only |
| 11 | Dezenas sobrando | Drilldown sobras | `_render_audit_monitoring_page("extra_numbers")` | Baixo | — | Manter | **Dezenas Sobrando** | Observacional | read-only |
| 12 | Benchmark resumido | Resumo benchmark DB | `_render_benchmark_resumido_page` | Baixo | — | Manter | **Benchmark Histórico Resumido** | Evidência histórica | read-only |
| 13 | Métricas HB | Métricas geometria HB | `_render_metrics_hb_page` (**duplicada L7556/L7937**) | Médio | Função duplicada — segunda sombra a primeira | Reestruturar | **Métricas HB** | Corrigir duplicata; read-only | reestruturar + read-only |
| 14 | Cobertura estrutural | Diagnóstico estrutural cartão | `_render_cobertura_estrutural_page` | Médio | Default batch V3; sem leitura 6 bases; sem CORE_002 | Reestruturar | **Cobertura Estrutural** | Alinhar 6 bases + label soberano opcional | reestruturar + read-only |
| 15 | Central de Diagnósticos ML | Vereditos ML sem efeito operacional | `_render_central_ml_diagnostics_page` | Médio | Campos `generation_cmd`/`recalibration_cmd` podem parecer acionáveis | Renomear | **Central ML Assistiva** | ML propõe; ADM veredita; sem efeito operacional | renomear + read-only |
| 16 | Vazamento lateral | Drilldown leakage | `_render_audit_monitoring_page("side_leak")` + expander na Central | Alto | Bypass conceitual se interpretado como ação | Renomear | **Vazamento Lateral Constitucional** | Auditoria de bypass/sobra_real | renomear + read-only |
| 17 | Evolução 13 → 14 | Métrica evolutiva | `_render_audit_monitoring_page("13_to_14")` | Médio | Pode parecer promessa de evolução | Manter como evidência | **Evolução 13→14 (evidência histórica)** | Sem linguagem de garantia | read-only + renomear |
| 18 | Evolução 14 → 15 | Métrica evolutiva | `_render_audit_monitoring_page("14_to_15")` | Médio | Idem | Manter como evidência | **Evolução 14→15 (evidência histórica)** | Sem linguagem de garantia | read-only + renomear |
| 19 | Limpar Históricos | Limpa session_state | `_render_clear_histories_page` | Baixo | Não destrutivo | Manter na área restrita | **Limpeza de Sessão** | Só chaves `institutional_*` | manter |
| 20 | Apagar Histórico | Purge PostgreSQL | `_render_delete_history_page` / `_purge_institutional_history_tables` | **CRÍTICO** | Apaga evidência GE/baseline; guarda parcial via `history_preservation_policy` | Bloquear/ocultar | **Limpeza Controlada (protegida)** | Fail-closed; lista de labels protegidos | **bloquear** + reestruturar |
| 21 | Gerar Jogos (órfã) | Geração legada | `_render_generator_page` | **CRÍTICO** | Em `allowed_pages`; bypass CORE_002 | Ocultar + remover | — | Código legado | **ocultar** → remover após autorização |
| 22 | _render_generation_page (morta) | Bateria completa | Nunca despachada | Alto | Código morto com geração | Remover após autorização | — | Legado | mover para legado |
| 23 | admin_app completo | Segundo painel ADM | `dashboard/admin_app.py` | Alto | Duplicidade; ML ranking; reconciliação DB | Mover para legado | — | Arquivo legado documentado | mover para legado |
| 24 | public_app → institutional | Entry público = ADM completo | `public_app.py` L54 | **CRÍTICO** | Superfície ADM sem segregação | Reestruturar | **public_app segregado** | Público ≠ ADM institucional | reestruturar (missão separada) |

### 4.1 Telas ausentes propostas (novas — não existem hoje)

| Tela proposta | Justificativa | Status futuro |
|---------------|---------------|---------------|
| Gestão de Projetos — Fase 0 (read-only) | M-GOV-030 implantada só em Git | read-only (nova) |
| Matriz Soberana CORE_002 | ADR-047 exige visualização da matriz 01–25 | read-only (nova) |
| Leitura pelas 6 Bases | `POLITICA_AVALIACAO_NUCLEO_LEI15_6_BASES.md` | read-only (nova) |
| ADRs e Leis | Corpus constitucional | read-only (nova) |
| Dezenas críticas e papéis | Papéis reforço/controle/penalização | read-only (nova) |

---

## 5. Leitura específica — Cobertura Estrutural

### 5.1 Modelo atual

- Função: `_render_cobertura_estrutural_page` (L8017+).
- Fonte: PostgreSQL via `_cached_card_structure_diagnostics_from_db`.
- Filtros: `analysis_batch_label`, `game_size`, `generation_event_id`, `reconciliation_run_id`, `concurso`.
- Default batch: V3 via `institutional_light_mode.default_batch_index()` / `batch_select_options()`.
- Declarações corretas: `operational_effect=False`, `ml_role=diagnostic_only`, não envia alertas à Central.

### 5.2 O modelo serve?

**Parcialmente.** A estrutura de abertura/fechamento/gaps/travamento 13/14 é útil e aderente ao
diagnóstico observacional. Porém:

| Gap | Impacto |
|-----|---------|
| Default V3, não CORE_002 | Operador interpreta V3 como núcleo vigente |
| Sem painel das 6 bases | Não cumpre `POLITICA_AVALIACAO_NUCLEO_LEI15_6_BASES` |
| Sem matriz de papéis 01–25 | Paradigma fixo 15D implícito nos rankings |
| Label "Cobertura Institucional" | **Não existe** no código — já está como "Cobertura estrutural" ✓ |
| Lote "(todos)" em light mode | Correto bloquear; manter |

### 5.3 Proposta de alinhamento às 6 bases

1. Adicionar seção **Leitura 6 Bases** (read-only) com scores de `lei15_core_six_bases_evaluation`.
2. Trocar default de batch para `STRUCT_LEI15_CORE_CANDIDATE_002_15D_001` (somente leitura).
3. Manter V1/V2/V3/CAND-001 como **evidência histórica** em seletor secundário.
4. Renomear caption "Lote de análise (padrão V3)" → "Lote de evidência (histórico)".
5. Banner fixo: "Diagnóstico observacional — hit isolado ≠ veredicto institucional".

---

## 6. Leitura específica — Central de Diagnósticos ML

### 6.1 Validade da leitura atual

**Continua válida** como camada ADM-verdict. Texto institucional forte (L7732–7735):

- ML propõe; ADM emite veredito.
- Sem efeito operacional, geração ou recalibração.

### 6.2 O que precisa mudar

| Item | Proposta |
|------|----------|
| Nome "Central de Diagnósticos ML" | → **Central ML Assistiva** |
| Campos `generation_cmd`, `recalibration_cmd` | Exibir como `disabled=true` / riscado / tooltip "não executável" |
| Veredito sugerido | Reforçar "orientação apenas" em destaque visual |
| Integração Cobertura | Manter separação explícita (já documentada) |
| Drilldown vazamento na Central | Mover link para "Vazamento Lateral Constitucional" |

### 6.3 Riscos de ML parecer operacional

- Presença de `generation_cmd` sem desabilitação visual.
- Home e gerador não repetem política ML assistivo.
- `admin_app` `ml_intelligence` (legado) tem ranking ML — **não** deve voltar ao painel produção.

---

## 7. Leitura específica — Vazamento Lateral

### 7.1 Redefinição proposta

**Vazamento Lateral Constitucional** — camada de auditoria que mede `sobra_real =
cartao_final − resultado_oficial`, detectando:

- bypass de roteamento de geração;
- uso de motor legado com `batch_label=None`;
- exposição de ADM via `public_app`;
- scoring V1 `active` sequestrando pool;
- geração paralela `_generate_direct_15_games`.

### 7.2 Riscos reais de bypass mapeados

| Vetor | Evidência no código | Severidade |
|-------|---------------------|------------|
| `_generate_direct_15_games` | L3989; chamado por clean_law15 e generation órfã | Crítico |
| `batch_label=None` | `lei15_generation_routing_policy.py` bloqueia em código soberano, **não** no painel ADM | Crítico |
| `_run_clean_law15_generation` sem label soberano | L11909 `analysis_batch_label` indefinido | Crítico |
| `generation` page_key em `allowed_pages` | L9551 | Alto |
| GET `/generate/*` | `backend/main.py` L71+ — não usado pelo painel, mas API exposta | Alto |
| V1 `active` global | ADR-047 P5/P6; flag `LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1=active` | Alto |
| `public_app` → institutional | `public_app.py` L54 | Alto |
| Simulação com fallback | `_run_institutional_simulation` session-only — risco baixo | Baixo |
| Purge sem guarda completa | `delete_history` + `history_preservation_policy` parcial | Crítico |

---

## 8. Leitura específica — Evolução 13→14 e 14→15

### 8.1 Decisão proposta

| Tela | Destino |
|------|---------|
| Evolução 13→14 | **Manter** como evidência histórica read-only |
| Evolução 14→15 | **Manter** como evidência histórica read-only |

### 8.2 Linguagem a remover na implementação

- Qualquer implicação de "evolução garantida" ou "progressão prometida".
- Substituir por: "métrica observacional de transição estrutural — sem efeito preditivo".

### 8.3 Agrupamento proposto

Fundir visualmente em submenu **Evidência Histórica de Transição (13/14/15)** no bloco Diagnóstico.

---

## 9. Leitura específica — Área Bloqueada/Restrita

### 9.1 Limpar Históricos

| Aspecto | Estado atual | Proposta |
|---------|--------------|----------|
| Escopo | Só `institutional_*` session keys | Manter |
| Risco | Baixo — não destrutivo | Manter em Área Restrita |
| Nome | "Limpar Históricos" (ambíguo) | → **Limpeza de Sessão** |

### 9.2 Apagar Histórico

| Aspecto | Estado atual | Proposta |
|---------|--------------|----------|
| Escopo | `HISTORICAL_TEST_TABLES` + `PURGE_ONLY_TABLES` | Restringir |
| Preserva | `imported_contests` | Manter |
| Guarda | `assert_generic_institutional_purge_blocked` (ADR-047) | Reforçar lista de labels GE/baseline |
| Risco Lei 001 | Apaga `generation_events` com evidência congelada | **Bloquear** botão até missão de proteção |
| UX | One-click com confirmação interna | Exigir confirmação dupla + missão Git |

### 9.3 Compatibilidade Lei 001

Purge atual **não está plenamente compatível** com preservação de evidência institucional.
Proposta: ocultar botão; exibir status "bloqueado por ADR-047"; link para registro M-OPS-INC-001
e Gestão de Projetos.

---

## 10. Nova arquitetura proposta de menus

```
A. GOVERNANÇA                                    [novo bloco]
   ├── Status Constitucional                     (reestrutura home)
   ├── Gestão de Projetos — Fase 0              (read-only Git)
   ├── ADRs e Leis                              (read-only)
   └── Auditoria Git / Railway                  (funde audit runtime)

B. NÚCLEO LEI 15                                [novo bloco]
   ├── Matriz Soberana CORE_002                 (read-only)
   ├── Cobertura Estrutural                     (reestruturada)
   ├── Leitura pelas 6 Bases                    (read-only)
   └── Dezenas críticas e papéis                (read-only)

C. OPERAÇÃO ADM                                 [bloqueada Fase 1]
   ├── Gerador ADM CORE_002 — BLOQUEADO         (substitui clean_law15)
   ├── Conferência de Resultados                (manter)
   ├── Simulação Institucional                  (renomear)
   └── Histórico de Gerações                    (funde analítico parcial)

D. DIAGNÓSTICO                                  [read-only]
   ├── Central ML Assistiva                     (renomear)
   ├── Vazamento Lateral Constitucional         (renomear)
   ├── Benchmark Histórico Resumido             (manter)
   └── Evolução 13/14/15 — evidência histórica  (agrupar)

E. RASTREABILIDADE                              [read-only]
   ├── Histórico Institucional Protegido        (manter)
   ├── Histórico Analítico                      (manter)
   ├── Comparativos Históricos                  (manter)
   ├── Auditoria Runtime                        (manter)
   └── Monitoramento pós-conferência            (fundir 3 telas audit)

F. ÁREA RESTRITA                                [bloqueada]
   ├── Limpeza de Sessão                        (manter)
   ├── Limpeza Controlada                       (substitui Apagar Histórico)
   └── Operações bloqueadas — status            (read-only)
```

---

## 11. Plano de implementação em fases

| Fase | Escopo | Agente | Pré-requisito |
|------|--------|--------|---------------|
| **F0** | Este inventário — aprovação institucional | governança | — |
| **F1** | Bloqueios: gerador, purge, páginas órfãs; fix `NameError` | plataforma + visual | Aprovação F0 |
| **F2** | Bloco Governança read-only (Status, Gestão Projetos, ADRs) | visual + governança | F1 |
| **F3** | Bloco Núcleo CORE_002 (matriz, 6 bases, cobertura) | visual + estatístico | F1 |
| **F4** | Operação ADM com roteamento ADR-047 (`lei15_generation_routing_policy`) | plataforma + geração | `GENERATION_ENABLED` + ADR |
| **F5** | Área Restrita com purge protegido (`history_preservation_policy`) | dados + governança | F1 |
| **F6** | Segregar `public_app` do ADM completo | plataforma | F2 |
| **F7** | Remover código morto (`_render_generation_page`, duplicata HB) | qualidade + visual | F1 |

Cada fase exige cartão Gestão de Projetos, checklist e veredicto (M-GOV-030).

---

## 12. Riscos se implementar tudo de uma vez

| Risco | Consequência |
|-------|--------------|
| Regressão de boot Streamlit | Painel inoperante (repetir M-OPS-INC-001) |
| Quebra de conferência operacional | Impacto Lei 001 |
| Liberação acidental de geração | Bypass CORE_002 |
| Purge de evidência durante refactor | Perda irreversível GE/baseline |
| UX drift entre operadores | Confusão constitucional |
| Conflito com hotfix `f0c1261` | `institutional_light_mode` frágil |

**Recomendação:** máximo 1 bloco de menu por PR; pytest + smoke Streamlit por fase.

---

## 13. Recomendações de bloqueio antes de qualquer geração

1. Manter `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0` até F4 aprovada.
2. Desabilitar botão "Gerar com Lei 15" na UI (mesmo com flag=0).
3. Remover `generation` de `allowed_pages`.
4. Corrigir `_run_clean_law15_generation` para usar `lei15_generation_routing_policy` ou bloquear.
5. Bloquear `delete_history` até proteção de labels institucionais.
6. Auditar `public_app` — não expor gerador até segregação (F6).
7. Exibir banner constitucional fixo: "Geração bloqueada — ADR-047 em transição".

---

## 14. Próxima missão sugerida

**M-VIS-031 — Painel ADM Fase 1: Bloqueios Constitucionais e Status**

| Campo | Valor |
|-------|-------|
| Escopo | F1 do plano: bloquear gerador, purge, órfãos; banner Status Constitucional mínimo |
| Agentes | `agent_visual` + `agent_plataforma` |
| Proibido | Liberar geração; alterar CORE_002; purge |
| Entregável | PR pequena com testes de smoke |

---

## Anexo A — Arquivos lidos/analisados

| Arquivo | Papel |
|---------|-------|
| `dashboard/institutional_app.py` | Painel produção (~13.400 linhas) |
| `dashboard/institutional_light_mode.py` | Lazy-load, batch default V3 |
| `dashboard/public_app.py` | Entrypoint Railway/cloud |
| `dashboard/admin_app.py` | Legacy ADM (Mission 29) |
| `dashboard/labels.py` | Labels legacy admin |
| `backend/main.py` | Rotas GET `/generate/*` |
| `src/lotoia/governance/lei15_generation_routing_policy.py` | Roteamento ADR-047 |
| `src/lotoia/governance/history_preservation_policy.py` | Guarda purge ADR-047 |
| `docs/adr/ADR-047-TRANSICAO-CONSTITUCIONAL-LEI15-CORE002.md` | Constituição transição |
| `docs/governance/AUDITORIA_CONSTITUCIONAL_LOTOIA_2026_06_17.md` | Auditoria |
| `docs/governance/MISSION_29_ADM_FUNCTIONAL_INVENTORY.md` | Inventário legacy |
| `docs/governance/MISSION_29_ADM_REDUNDANCY_MATRIX.md` | Redundâncias |
| `docs/governance/POLITICA_GESTAO_PROJETOS_LOTOIA.md` | Gestão Projetos F0 |
| `docs/governance/POLITICA_AVALIACAO_NUCLEO_LEI15_6_BASES.md` | 6 bases |
| `docs/governance/POLITICA_ML_ASSISTIVO.md` | ML assistivo |
| `docs/governance/POLITICA_PRESERVACAO_HISTORICO_LOTOIA.md` | Preservação histórico |

---

## Anexo B — Lista consolidada de menus/telas encontrados

**Produção sidebar:** 20 entradas + 2 área restrita = **22 navegáveis**.

**Órfãs/dispatch:** 12 page_keys adicionais no código.

**Legacy admin_app:** 16+ page_keys (não produção).

**Total inventariado:** **50+ superfícies** (incluindo sub-seções audit_monitoring).

---

## Anexo C — Pontos de bypass (checklist institucional)

| # | Vetor | Status no painel | Ação proposta |
|---|-------|------------------|---------------|
| 1 | `batch_label=None` | ADM não aplica routing policy | Bloquear geração |
| 2 | `_generate_direct_15_games` | Ativo em clean_law15 | Substituir por CORE_002 path |
| 3 | GET `/generate/*` | API exposta; painel não usa | Missão plataforma separada |
| 4 | V1 active global | Env flag; painel não exibe | Status Constitucional |
| 5 | `public_app` expõe ADM | Ativo | Segregar F6 |
| 6 | Botões geração paralela | clean_law15 + generation órfã | Desabilitar UI |
| 7 | Simulação fallback | Session-only | Manter; renomear |
| 8 | Purge/delete sem guarda | Ativo com guarda parcial | Bloquear UI |

---

## Anexo D — Confirmações da missão (read-only)

| Confirmação | Status |
|-------------|--------|
| Nenhum código funcional alterado | ✓ |
| Nenhuma geração executada | ✓ |
| Nenhum purge executado | ✓ |
| Nenhum deploy manual | ✓ |
| Nenhuma alteração em banco/schema | ✓ |
| Nenhuma alteração em LEI15_CORE_002 | ✓ |
| Nenhuma ativação Lei 15A | ✓ |
| Testes de código | N/A — missão documental de leitura estática |

---

## Referências

- ADR-047: `docs/adr/ADR-047-TRANSICAO-CONSTITUCIONAL-LEI15-CORE002.md`
- M-GOV-030: Gestão de Projetos Fase 0
- M-OPS-INC-001: Incidente `institutional_light_mode` (encerrado)
- Auditoria: `docs/governance/AUDITORIA_CONSTITUCIONAL_LOTOIA_2026_06_17.md`
