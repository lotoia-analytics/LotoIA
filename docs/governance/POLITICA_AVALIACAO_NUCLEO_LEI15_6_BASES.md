# Política Institucional — Avaliação do Núcleo Lei 15 pelas 6 Bases

## Status

**VIGENTE — critério oficial de leitura do Núcleo Lei 15**

| Campo | Valor |
|-------|-------|
| Registro | `POLITICA_NUCLEO_LEI15_6_BASES_2026_06_17` |
| Agentes | `agent_governanca` + `agent_qualidade` |
| Escopo | Leitura e status de variantes do Núcleo Lei 15 (15D) |
| Módulo | `src/lotoia/governance/lei15_core_six_bases_evaluation.py` |

---

## 1. Conceito oficial

Um **Núcleo forte** gera dezenas estruturalmente válidas, reaproveitáveis e sustentáveis
entre concursos.

Performance baixa em **um** concurso não invalida a geração se o equilíbrio estrutural,
cobertura, diversidade e estabilidade forem preservados para ciclos seguintes.

**Hit não é veredicto final.** Hit é evidência dentro da **Base 1 — Força de acerto**.

O objetivo não é perseguir um 13 isolado. O objetivo é encontrar o ponto de equilíbrio em
que resultados 12/13+ emergem como **consequência natural da estrutura**.

---

## 2. As 6 bases obrigatórias

| # | Base | Pergunta central |
|---|------|------------------|
| 1 | **Força de acerto** | A estrutura produz bons resultados de forma cruzável? |
| 2 | **Diversidade suficiente** | A geração distribui bem perfis e assinaturas? |
| 3 | **Baixa redundância** | Os cartões evitam clones estruturais? |
| 4 | **Controle prefixo/sufixo** | O núcleo controla vícios dominantes? |
| 5 | **Cobertura das dezenas críticas** | Dezenas sensíveis estão presentes de forma inteligente? |
| 6 | **Estabilidade em vários concursos** | A estrutura se sustenta ao longo do tempo? |

---

## 3. Escala de leitura por base

Cada base recebe uma das quatro leituras:

| Leitura | Significado |
|---------|-------------|
| **forte** | Evidência consistente; atende critério institucional |
| **parcial** | Progresso real, mas incompleto ou com trade-off |
| **fraca** | Evidência negativa ou regressão clara |
| **inconclusiva** | Amostra insuficiente ou métricas ausentes |

Formato mínimo obrigatório em todo relatório de variante:

```
Base 1 — Força de acerto:           [forte|parcial|fraca|inconclusiva]
Base 2 — Diversidade suficiente:    [forte|parcial|fraca|inconclusiva]
Base 3 — Baixa redundância:         [forte|parcial|fraca|inconclusiva]
Base 4 — Controle prefixo/sufixo:   [forte|parcial|fraca|inconclusiva]
Base 5 — Cobertura dezenas críticas:[forte|parcial|fraca|inconclusiva]
Base 6 — Estabilidade multi-concurso:[forte|parcial|fraca|inconclusiva]
```

---

## 4. Indicadores por base

### Base 1 — Força de acerto

- melhor hit; média de hits; runs 12+; runs 13+
- comparação vs baseline, V1, V2, V3, V4
- evolução/regressão vs platô atual (9.286 / melhor=11)

**Regra:** nunca ler isoladamente — cruzar com bases 2–6.

### Base 2 — Diversidade suficiente

- `perfil_origem_real` / `perfil_label_final`
- variedade de `prefix_signature` / `suffix_signature`
- dispersão de combinações; equilíbrio recorrente/híbrido/caótico

**Regra:** diversidade demais enfraquece força; diversidade de menos cria vício.

### Base 3 — Baixa redundância

- duplicidade; similaridade entre cartões
- repetição de blocos e assinaturas
- sobreposição excessiva entre cartões do mesmo lote

**Regra:** evitar clones estruturais sem dispersão aleatória cega.

### Base 4 — Controle prefixo/sufixo

- taxa prefixo 01-02-03; taxa sufixo 22-24-25
- `structural_bias_score`
- comparação baseline / CAND-A / CAND-D
- `relabeling_applied` / `relabeling_reason` (zero mascaramento)

**Regra:** controle estrutural sozinho não forma Núcleo.

### Base 5 — Cobertura das dezenas críticas

- presença de dezenas críticas (06, 16, 17, 21 — blind spots históricos)
- subcobertura / sobrecobertura
- distribuição entre jogos; impacto na força de acerto

**Regra:** cobertura ≠ repetir sempre as mesmas dezenas.

### Base 6 — Estabilidade em vários concursos

- janelas 5, 7, 10+ concursos
- variação da média; estabilidade runs 12+/13+
- manutenção das bases 2–5 entre concursos-alvo

**Regra:** Núcleo válido não depende de um único concurso.

---

## 5. Regras de status

| Proibição | Detalhe |
|-----------|---------|
| Núcleo por hit alto isolado | **Proibido** |
| Descarte por hit baixo isolado | **Proibido** em piloto pequeno |
| Avanço como candidata | Só com **equilíbrio progressivo** nas 6 bases |

Labels de veredicto legado (`REPROVADA POR HITS`, etc.) permanecem como **sinal parcial**
da Base 1, não como veredicto institucional final.

---

## 6. Leitura atual (EPOCH_001 — concursos 3705–3711)

### CAND-D (`STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001`, GE 115)

| Base | Leitura | Evidência resumida |
|------|---------|-------------------|
| 1 — Força de acerto | **fraca** | melhor=11, média=9.286, runs 13+=0 (platô V2–V4) |
| 2 — Diversidade | **forte** | perfis 20/20/10; assinaturas dispersas (top prefix 02-03-04) |
| 3 — Baixa redundância | **parcial** | melhora vs legado; amostra piloto única (50 jogos) |
| 4 — Controle prefixo/sufixo | **forte** | p3=4%, s3=8%, relabel=0, bias≈14.8 |
| 5 — Cobertura crítica | **inconclusiva** | N-C3 injeta blind spots; auditoria fina pendente |
| 6 — Estabilidade | **inconclusiva** | 1 GE × 7 concursos — amostra insuficiente |

**Leitura institucional:** CAND-D **não** se resume a “reprovada por hits”. Avançou
fortemente em controle estrutural, diversidade e redução de vício; ainda **não** demonstra
equilíbrio em força de acerto, cobertura crítica auditada e estabilidade multi-ciclo.

### V1 (`STRUCT_REALIGN_V1_15D_001`)

| Base | Leitura | Evidência resumida |
|------|---------|-------------------|
| 1 — Força de acerto | **forte** | melhor=14, média≈12.14, 47 runs 13+ |
| 2 — Diversidade | **inconclusiva** | auditoria fina de perfil/assinatura pendente |
| 3 — Baixa redundância | **inconclusiva** | similaridade entre cartões não consolidada |
| 4 — Controle prefixo/sufixo | **parcial** | sufixo controlado (26.7%); prefixo ainda alto (40.4%) |
| 5 — Cobertura crítica | **inconclusiva** | cobertura 06/16/17/21 não auditada sob 6 bases |
| 6 — Estabilidade | **parcial** | 140 runs / 7 concursos; lote extenso, bases 2–5 abertas |

**Leitura institucional:** V1 **não** se resume a “aprovada por hits”. Demonstra força e
estabilidade inicial de acerto; ainda precisa auditoria fina nas demais bases antes de
status de Núcleo pleno.

### Núcleo antigo legado (`STRUCT_TEST_15D_001`)

| Base | Leitura |
|------|---------|
| 1 | parcial (melhor=12, média=11.28, 0 runs 13+) |
| 2 | fraca (concentração R-03/R-04) |
| 3 | fraca (blocos repetidos 01-02-03 / 22-24-25) |
| 4 | fraca (p3=42%, s3=53%, relabeling histórico) |
| 5 | fraca (blind spots persistentes) |
| 6 | parcial (25 runs, sem 13+) |

**Status:** baseline congelado — ver `RELATORIO_NUCLEO_ANTIGO_LEI15_BASELINE_CONGELADO_2026_06_17.md`.

---

## 7. Objetivo operacional

1. Encontrar equilíbrio progressivo das 6 bases — **não** hit isolado.
2. **Não** gerar novo volume no núcleo antigo legado.
3. Evoluir linhagem CDX (ou sucessoras) com relatórios sempre no formato 6 bases.
4. Nenhuma promoção `active` sem equilíbrio demonstrado — gate ampliado além da Base 1.

---

## 8. Referências

- `docs/governance/RELATORIO_NUCLEO_ANTIGO_LEI15_BASELINE_CONGELADO_2026_06_17.md`
- `docs/adr/ADR-NUCLEO-LEI15-CANDIDATE-001.md`
- `scripts/ops/report_core_cdx_pilot_d_final_15d.py`
- `AGENTS.md`

---

## Histórico

| Data | Nota |
|------|------|
| 2026-06-17 | Política 6 bases — alinhamento conceitual obrigatório pré-missões |
