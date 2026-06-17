# Relatório Institucional — Núcleo Antigo Lei 15 = Baseline Congelado

## Status

**REGISTRADO — BASELINE CONGELADO / READ-ONLY**

| Campo | Valor |
|-------|-------|
| Missão | Diretriz Institucional — Núcleo Antigo Lei 15 |
| Agentes | `agent_governanca` + `agent_qualidade` |
| Data | 2026-06-17 |
| Registro | `NUCLEO_ANTIGO_LEI15_BASELINE_CONGELADO_2026_06_17` |
| Modo operacional | **shadow_test only** para linhagem CDX; núcleo antigo **sem novos lotes** |

---

## 1. Objetivo

Formalizar que o **motor de geração legado Lei 15** (perfis R-03/R-04, pool round-robin,
composição R-06 com relabeling) deixa de ser candidato ativo de evolução e passa a ser usado
**exclusivamente** como baseline congelado, evidência histórica e controle negativo.

> **Distinção institucional:** este documento trata do **pipeline legado de geração**
> (`STRUCT_TEST_15D_001` e realinhamentos V2–V4 sobre o mesmo núcleo). Não revoga o
> **núcleo operacional 15D congelado** (dezenas `01…25`) registrado em
> `ADR_LEI15_NUCLEO_15D_CONGELADO.md`.

---

## 2. Decisão

| Decisão | Estado |
|---------|--------|
| Núcleo antigo Lei 15 = baseline congelado | **SIM** |
| Núcleo antigo Lei 15 = reprovado como candidato ativo | **SIM** |
| Variante D (CDX N-C1..N-C6) = linhagem de validação | **SIM** — piloto executado |
| Promoção `active` | **NÃO AUTORIZADA** |
| Novos lotes extensos no núcleo antigo | **PROIBIDOS** |

---

## 3. Justificativa (evidência consolidada)

Auditoria CDX e pilotos EPOCH_001 (concursos 3705–3711) confirmaram ineficiência estrutural
e platô de hits no motor legado:

| Achado | Evidência |
|--------|-----------|
| Viço prefixo 01-02-03 | R-03 Recurrent: **69%** no pool legado; GP baseline **42%** |
| Viço sufixo 22-24-25 | Pool **26%**; GP baseline **53%** (amplificado por R-06) |
| Relabeling mascarando origem | Composição R-06 distorce distribuição real vs label |
| Platô V2/V3/V3.1/V4 | melhor=**11**, média=**9.286**, runs 13+=**0** |
| Ausência de 13+ consistente | 64 cartões V1≥13 no histórico; núcleo legado não recupera |
| Correção só na filtragem falhou | V2–V4 reduziram parcialmente viés, hits inalterados |

Label baseline congelado: `STRUCT_TEST_15D_001`  
Evidências V1 intactas: `STRUCT_REALIGN_V1_15D_001` (melhor=14, média≈12.14, 47 runs 13+).

---

## 4. Uso permitido do núcleo antigo

1. **Baseline comparativo congelado** — referência read-only em benchmarks.
2. **Evidência histórica** — lotes já persistidos no PostgreSQL (Lei No 001).
3. **Controle negativo** — contraste estrutural e de hits contra linhagem CDX.

---

## 5. Uso proibido

1. Novos lotes de produção no motor legado.
2. Novos pilotos extensos do núcleo antigo como candidato ativo.
3. Promoção para `active`.
4. Ajustes remendados no núcleo legado (scoring/composição/perfil).
5. Revalidação com lote 20 GEs no motor legado.
6. Tentativas de “salvar” o núcleo antigo via filtragem final ou relabeling.

---

## 6. Linhagem CDX — Variante D (executada)

Conforme autorização controlada, o piloto **Variante D** foi executado **sem gerar novo volume
no núcleo antigo**, comparando contra baseline já existente:

| Métrica | BASELINE legado | CAND-A (N-C4+N-C5) | CAND-D (N-C1..N-C6) |
|---------|-----------------|--------------------|---------------------|
| GE piloto | existente | **114** | **115** |
| prefixo 01-02-03 | 42.0% | 32.0% | **4.0%** |
| sufixo 22-24-25 | 53.0% | 30.0% | **8.0%** |
| relabeling | — | 0 | **0** |
| melhor hit | 12 | 11 | 11 |
| média hits | 11.280 | 9.286 | 9.286 |
| runs 13+ | 0 | 0 | 0 |

**Veredicto piloto D (legado Base 1):** `REPROVADA POR HITS` — sinal parcial apenas.

**Leitura institucional 6 bases (CAND-D):** controle estrutural e diversidade **fortes**;
força de acerto **fraca**; cobertura crítica e estabilidade **inconclusivas**.
Ver `POLITICA_AVALIACAO_NUCLEO_LEI15_6_BASES.md`.

---

## Gate institucional para qualquer promoção futura

> **Atualização 2026-06-17:** gate ampliado pela política das **6 bases**
> (`POLITICA_AVALIACAO_NUCLEO_LEI15_6_BASES.md`). Hit isolado não é veredicto final.

Promoção `active` exige **equilíbrio progressivo** entre as 6 bases — não apenas hits
ou estrutura isolados. Ver leituras registradas em
`src/lotoia/governance/lei15_core_six_bases_evaluation.py`.

---

## 8. Próximo passo correto (pós-diretriz)

| Ação | Autorização |
|------|-------------|
| Comparar CDX vs baseline legado existente | **Permitido** (read-only) |
| Novos lotes no motor legado | **Proibido** |
| Evolução CDX em shadow_test | **Permitido** somente com ADR + gate hits |
| Promoção active | **Bloqueada** |

A linhagem **CDX Candidate 001 Variante D** permanece como **referência evolutiva** (não o
motor legado). Próximas iterações devem partir do CDX, nunca de remendos no núcleo antigo.

---

## 9. Veredicto institucional

```
NUCLEO_ANTIGO_LEI15     → BASELINE CONGELADO (read-only)
NUCLEO_ANTIGO_LEI15     → REPROVADO como candidato ativo de evolução
CDX_VARIANTE_D          → Piloto executado; estrutura OK; hits REPROVADO
PROMOCAO_ACTIVE         → NÃO AUTORIZADA
```

---

## 10. Referências

- `docs/adr/ADR-NUCLEO-LEI15-CANDIDATE-001.md`
- `docs/adr/ADR-044-REAVALIACAO-NUCLEOS-LEI15-15A.md`
- `docs/governance/ADR_LEI15_NUCLEO_15D_CONGELADO.md`
- `src/lotoia/governance/lei15_legacy_core_baseline.py`
- `scripts/ops/report_core_cdx_pilot_d_final_15d.py`
- `scripts/ops/audit_lei15_core_cdx_report_15d.py`
- PostgreSQL: GE 114 (CAND-A), GE 115 (CAND-D), baseline `STRUCT_TEST_15D_001`

---

## Histórico

| Data | Agente | Nota |
|------|--------|------|
| 2026-06-17 | agent_governanca + agent_qualidade | Baseline legado congelado; CDX-D piloto registrado |
