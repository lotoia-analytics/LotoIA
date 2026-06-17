# ADR-046 — Proposta Institucional Núcleo Lei 15 CAND-002 (Síntese V1 + CDX-D)

## Status

**NÚCLEO SOBERANO IMPLANTADO — LEI15_CORE_002**

| Campo | Valor |
|-------|-------|
| Registro | `ADR_046_NUCLEO_LEI15_CANDIDATE_002` |
| Núcleo soberano | `LEI15_CORE_002` |
| Label técnico rastreável | `STRUCT_LEI15_CORE_CANDIDATE_002_15D_001` |
| Status institucional | `NUCLEO_SOBERANO_LEI15` |
| Flag implantação | `LOTOIA_LEI15_CORE_002=sovereign` |
| Geração | **BLOQUEADA** (`LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0` padrão) |
| Modo `active` público | **BLOQUEADO** |
| Lei 15A | **BLOQUEADA** até ordem posterior |
| Execução futura | **Painel ADM 100% funcional** |
| Piloto / teste resultado | **NÃO EXECUTADO** nesta implantação |

---

## Contexto

A fase de investigação EPOCH_001 (concursos 3705–3711) está encerrada.

Conclusões consolidadas:

- O **núcleo antigo legado** (`STRUCT_TEST_15D_001`) está **congelado read-only** — não é caminho de evolução.
- **Hit isolado não é veredicto** — avaliação oficial pelas **6 bases** (`POLITICA_AVALIACAO_NUCLEO_LEI15_6_BASES.md`).
- **V1** lidera força de acerto e estabilidade; **CAND-D** lidera diversidade e controle prefixo/sufixo.
- **V2, V3 e V4** não resolveram o Núcleo (platô de hits ~11, média 9.286).
- **V1 e CAND-D são complementares**, não substitutas.

Decisão ML assistiva (`ML_LEI15_CORE_CANDIDATE_DECISION_2026_06_17`, papel `diagnose`, `operational_effect=false`) recomendou síntese híbrida **CAND-002**.

Esta ADR registra a proposta institucional e, após ordem `agent_geracao` de 2026-06-17, **implanta a arquitetura soberana LEI15_CORE_002** sem geração operacional nesta etapa.

---

## Implantação soberana (2026-06-17)

| Item | Estado |
|------|--------|
| Módulo governança | `src/lotoia/governance/lei15_core_002_sovereign.py` |
| Módulo geração | `src/lotoia/generation/lei15_core_002.py` |
| Integração | `src/lotoia/generator/basic_generator.py` |
| Geração executada | **Não** |
| Piloto 15D | **Não** |
| Relatório | `docs/governance/RELATORIO_LEI15_CORE_002_IMPLANTACAO_2026_06_17.md` |

## Por que a CAND-002 existe

A CAND-002 existe para resolver o **desequilíbrio estrutural-estatístico** observado quando V1 e CAND-D são tratadas isoladamente:

| Variante | Força (Base 1) | Controle estrutural (Base 4) | Núcleo pleno? |
|----------|----------------|------------------------------|---------------|
| V1 pura | forte | parcial | **Não** |
| CAND-D pura | fraca/inconclusiva | forte | **Não** |
| **CAND-002 (proposta)** | projetada forte | projetada forte | **Candidata** |

Objetivo: encontrar o **ponto de equilíbrio das 6 bases**, em que 12/13+ emergem como consequência natural da estrutura — não por hit isolado perseguido.

---

## Evidências que sustentam a proposta

### V1 (`STRUCT_REALIGN_V1_15D_001`)

| Evidência | Valor |
|-----------|-------|
| Melhor hit | 14 |
| Média cartões fortes (≥13) | 13.07 |
| Runs ≥13 | 75 |
| Runs =14 | 5 |
| Concursos com ≥13 | **7/7** |
| Cartões únicos ≥13 | 64 |
| Padrão V1-strong nos ≥13 | **85.9%** |
| Leitura 6 bases (segmento forte) | B1 forte, B6 forte; B3 fraca; B4 parcial |

Fontes: `report_lei15_v1_strong_cards_6_bases_audit.py`, `report_lei15_core_6_bases_comparative.py`.

### CAND-D (`STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001`, GE 115)

| Evidência | Valor |
|-----------|-------|
| Prefixo 01-02-03 | **4.0%** |
| Sufixo 22-24-25 | **8.0%** |
| Relabeling | **0** |
| Diversidade / controle P-S | **forte** |
| Melhor hit / média / runs 13+ | 11 / 9.286 / **0** |
| Leitura 6 bases | B2 e B4 fortes; B1 inconclusiva |

Fontes: piloto CDX GE 115, `report_core_cdx_pilot_d_final_15d.py`.

### Núcleo antigo e lanes descartadas

- **BASELINE legado:** baseline congelado — `RELATORIO_NUCLEO_ANTIGO_LEI15_BASELINE_CONGELADO_2026_06_17.md`
- **V2/V3/V4:** não resolveram — comparativo 6 bases EPOCH_001

---

## Arquitetura proposta (5 camadas)

| Ordem | Camada | Origem | Função |
|------:|--------|--------|--------|
| L1 | `generation_cdx_d` | CAND-D N-C1..N-C6 | Pool diverso; controle prefixo/sufixo **na geração** |
| L2 | `v1_selection_compose` | Realinhamento V1 | Seleção/composição; preserva `base_score` e cartões fortes |
| L3 | `v1_strong_shield` | `lei15_core_structural_payload` | Penalização estrutural reduzida em padrões V1-strong |
| L4 | `anti_clone_gp` | Política CAND-002 GP | Limita overlap e assinaturas duplicadas no **GP final** |
| L5 | `critical_digit_layer` | Auditoria V1≥13 | Reforço 07/23; penalização contextual 15/25 |

**Label operacional proposto:** `STRUCT_LEI15_CORE_CANDIDATE_002_15D_001`  
**Flag proposta (futura):** `LOTOIA_LEI15_CORE_CANDIDATE_002=shadow_test`

---

## Riscos que a CAND-002 tenta resolver

1. **Viço prefixo/sufixo do núcleo legado** — herança R-03/R-04 e amplificação R-06.
2. **Perda de força ao aplicar só controle estrutural** — CAND-D pura no platô de hits.
3. **Vício estrutural não corrigido por filtragem final** — lição V2/V3/V4.
4. **Mascaramento por relabeling** — N-C5 (sem relabel) incorporado.
5. **Redundância/clones** — anti-clone GP (overlap ≤10, arquitetura ≤12%).
6. **Subcobertura 07/23** nos cartões V1≥13 — camada de dezenas críticas.
7. **Decisão por hit isolado** — gate pelas 6 bases institucionais.

---

## Riscos que permanecem abertos

1. Fusão V1+CDX pode **reintroduzir viço** se shield ou seleção V1 forem enfraquecidos.
2. Penalização insuficiente de `01-02-03` pode manter p3 ~33% nos fortes.
3. Anti-clone agressivo pode **eliminar cartões V1-strong legítimos**.
4. Reforço 07/23 pode **não transferir força** sem validação multi-GE.
5. Cobertura crítica e redundância projetadas como **parciais** — exigem piloto.
6. Estabilidade multi-concurso da síntese **não comprovada** — apenas projetada a partir de componentes.
7. **Nenhuma promoção `active`** até ADR dedicada pós-piloto.

---

## Por que V1 pura não é suficiente

Leitura 6 bases do segmento V1≥13 (EPOCH_001):

| Base | V1 |
|------|-----|
| Força de acerto | **forte** |
| Diversidade | parcial |
| Baixa redundância | **fraca** (overlap ~10.8) |
| Controle prefixo/sufixo | **parcial** (p3=32.8%, s3=46.9% nos fortes) |
| Cobertura crítica | parcial (07/23 subcobertos) |
| Estabilidade | **forte** |

V1 **não é Núcleo pleno**: concentra força em padrões produtivos (`22-24-25` em 46.9% dos ≥13), mantém redundância elevada e controle estrutural incompleto. **Aprovar V1 pura seria aprovar por hits (Base 1) ignorando bases 2–5.**

---

## Por que CAND-D pura não é suficiente

Leitura 6 bases do piloto CAND-D (GE 115):

| Base | CAND-D |
|------|--------|
| Força de acerto | **inconclusiva/fraca** (best=11, 0 runs 13+) |
| Diversidade | **forte** |
| Controle prefixo/sufixo | **forte** |
| Estabilidade | **inconclusiva** (1 GE piloto) |

CAND-D **controla estrutura na origem** mas **não preserva força V1**. **CAND-D pura não pode ser motor principal** nem Núcleo candidato isolado.

---

## Por que a síntese V1 + CAND-D é o caminho institucional

1. **Complementaridade comprovada:** V1 traz força/estabilidade; CAND-D traz diversidade/controle.
2. **Projeção 6 bases (ML assistivo):** balance **16.0** — quatro bases fortes, duas parciais, zero fracas.
3. **Lição CDX:** correção na **geração** (CAND-D) + **seleção** com força (V1) — não filtragem final cega.
4. **Shield institucional:** padrões V1-strong (85.9% dos ≥13) **penalizados, não bloqueados**.
5. **Política de dezenas:** 15/25 produtivas nos fortes — **penalização contextual**, não veto.
6. **Núcleo antigo congelado:** evolução só via candidata nova, não remendos no legado.
7. **15A bloqueada:** Lei 15 candidato deve preceder qualquer abertura 15A.

---

## Políticas registradas na proposta (referência — não implementadas)

### Prefixo/sufixo

- Soft caps: p3 `01-02-03` ≤15% pool; s3 `22-24-25` ≤35% pool (com exceções shield).
- Preservar sufixos produtivos: `22-24-25`, `23-24-25`, `18-24-25`, `21-24-25`.
- Preservar prefixos com shield: `01-02-03`, `01-03-04`, `01-03-06`, `01-04-06`.
- **Relabeling:** proibido (N-C5).

### Dezenas críticas

- **Reforço:** 07, 12, 16, 23 (meta presença ~45% no pool).
- **Penalização contextual:** 02, 04, 11, 15, 24, 25 — **nunca hard-block** em 15, 24, 25.

### Anti-clone / redundância

- GP: overlap máximo **10**; mesma arquitetura ≤**12%**.
- Pool: overlap tolerável ~**10.8**; bloqueio de clones acima de **11** no GP.
- Escopo anti-clone: **GP final**; exceção para padrões V1-strong no pool.

---

## Gates do piloto 15D (obrigatórios pós-implementação)

Esta ADR **não autoriza** o piloto; define os gates que **deverão** ser cumpridos quando `agent_geracao` implementar e `agent_qualidade` validar:

| # | Gate | Critério |
|---|------|----------|
| G1 | Modo | `shadow_test` exclusivo; flag `LOTOIA_LEI15_CORE_CANDIDATE_002` |
| G2 | Volume | 1 GE × 50 jogos; **sem** lote 20 GEs na primeira fase |
| G3 | Legado | **Zero** novo volume em `STRUCT_TEST_15D_001` |
| G4 | Reconcile | Concursos **3705–3711** persistidos |
| G5 | Relatório | 6 bases obrigatório (`report_lei15_core_6_bases_comparative.py`) |
| G6 | Estrutura | p3/s3 abaixo baseline legado; relabeling = 0 |
| G7 | Força | Evidência Base 1 **cruzada** com bases 2–6 — hit isolado insuficiente |
| G8 | Estabilidade | Amostra multi-GE antes de considerar promoção |
| G9 | Promoção | `active` **somente** via ADR posterior aprovada |
| G10 | 15A | **Bloqueada** até Núcleo Lei 15 candidato validado |

---

## Decisão desta ADR

1. **Registrar** a proposta `LEI15_CORE_CANDIDATE_002` como candidata institucional a Núcleo Lei 15.
2. **Manter bloqueado:** implementação, geração, `active`, Lei 15A.
3. **Encaminhar** para `agent_geracao` **somente após** ordem explícita de implementação shadow_test.
4. **Preservar intactas:** evidências CAND-001, V1, V2/V3/V4, baseline legado congelado.

---

## Consequências

### Positivas

- Proposta auditável e rastreável antes de qualquer código.
- Síntese V1+CAND-D alinhada às 6 bases e à política ML assistivo.
- Fronteira clara: proposta ≠ implementação ≠ promoção.

### Limitações

- Projeção 6 bases é **assistiva**, não comprovada em runtime.
- Gates de piloto ainda **não executados** para CAND-002.
- ADR adicional será necessária para `active` ou abertura 15A.

---

## Referências

| Documento | Papel |
|-----------|-------|
| `reports/ml_lei15_core_candidate_decision_2026_06_17.json` | Decisão ML assistiva |
| `docs/governance/POLITICA_AVALIACAO_NUCLEO_LEI15_6_BASES.md` | 6 bases |
| `docs/governance/RELATORIO_NUCLEO_ANTIGO_LEI15_BASELINE_CONGELADO_2026_06_17.md` | Legado congelado |
| `docs/adr/ADR-NUCLEO-LEI15-CANDIDATE-001.md` | CDX CAND-001 / CAND-D |
| `docs/adr/ADR-043-REALINHAMENTO-ESTRUTURAL-LEI15-V1.md` | V1 |
| `scripts/ops/report_lei15_v1_strong_cards_6_bases_audit.py` | Auditoria V1≥13 |
| `scripts/ops/report_lei15_core_6_bases_comparative.py` | Comparativo 6 bases |
| `src/lotoia/ml/lei15_core_candidate_decision.py` | Matriz ML interpretável |

---

## Histórico

| Data | Agente | Nota |
|------|--------|------|
| 2026-06-17 | agent_governanca | ADR-046 — proposta CAND-002 registrada; sem implementação |
| 2026-06-17 | agent_geracao | LEI15_CORE_002 implantado como Núcleo Soberano; geração bloqueada |
