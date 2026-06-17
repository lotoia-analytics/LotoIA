# Relatório Técnico — Implantação Núcleo Soberano LEI15_CORE_002

| Campo | Valor |
|-------|-------|
| Registro | `RELATORIO_LEI15_CORE_002_IMPLANTACAO_2026_06_17` |
| Data | 2026-06-17 |
| Agente | `agent_geracao` |
| ADR | `ADR-046-NUCLEO-LEI15-CANDIDATE-002` |
| Veredicto | **NÚCLEO SOBERANO LEI 15 IMPLANTADO** |

---

## Decisão institucional

`LEI15_CORE_CANDIDATE_002` deixa de ser tratada como candidata em termos institucionais.

A partir desta ordem, o sistema reconhece:

- **ID soberano:** `LEI15_CORE_002`
- **Status:** `NUCLEO_SOBERANO_LEI15`
- **Label técnico rastreável:** `STRUCT_LEI15_CORE_CANDIDATE_002_15D_001`

---

## Arquitetura implantada (5 camadas)

| Camada | Módulo | Função |
|--------|--------|--------|
| L1 `generation_cand_d` | `lei15_core_002.build_sovereign_pool` | Pool CAND-D N-C1..N-C6 |
| L2 `v1_selection_compose` | `compose_diverse_gp` (V1) | Seleção com força V1 |
| L3 `v1_strong_shield` | `lei15_core_structural_payload` | Proteção padrões V1-strong |
| L4 `anti_clone_gp` | `apply_anti_clone_gp` | Overlap ≤10; arquitetura ≤12% |
| L5 `critical_digit_layer` | `apply_critical_digit_layer` | Reforço 07/23; penalização contextual 15/25 |

**Arquivos:**

- `src/lotoia/governance/lei15_core_002_sovereign.py`
- `src/lotoia/generation/lei15_core_002.py`
- Integração: `src/lotoia/generator/basic_generator.py`
- Labels: `src/lotoia/governance/analysis_batch_labels.py`

---

## Flags e bloqueios

| Controle | Valor padrão |
|----------|--------------|
| `LOTOIA_LEI15_CORE_002` | `sovereign` |
| `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED` | `0` (bloqueado) |
| Geração automática | **Proibida** |
| Piloto 15D | **Não executado** |
| Teste de resultado | **Não executado** |
| `active` público | **Bloqueado** |
| Lei 15A | **Bloqueada** |

Execução futura: **somente Painel ADM 100% funcional** com autorização explícita (`LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=1`).

---

## Status institucional preservado

| Lane | Status |
|------|--------|
| Núcleo antigo (`STRUCT_TEST_15D_001`) | Congelado read-only |
| V1 pura | Evidência histórica — não soberana isolada |
| CAND-D pura | Evidência estrutural — não soberana isolada |
| V2 / V3 / V4 | Intactos — não alterados |
| CAND-001 A..D | Intactos — não alterados |

---

## Payload obrigatório (por cartão futuro)

- `lei15_core_002_applied`
- `sovereign_core_status`
- `candidate_origin_label`
- `generation_cand_d_applied`
- `v1_selection_compose_applied`
- `v1_strong_shield_applied`
- `anti_clone_gp_applied`
- `critical_digit_layer_applied`
- `perfil_origem_real`
- `perfil_label_final`
- `prefix_signature`
- `suffix_signature`
- `structural_bias_score`
- `relabeling_applied`
- `relabeling_reason`

---

## Confirmações da missão

1. Núcleo Soberano LEI15_CORE_002 implantado em código e governança.
2. **Nenhuma geração** foi executada nesta missão.
3. **Nenhum teste de resultado** foi executado nesta missão.
4. **Active público** permanece bloqueado.
5. **Lei 15A** permanece bloqueada.
6. **Núcleo antigo** permanece congelado/read-only.
7. Execução futura depende do **Painel ADM 100% funcional**.

---

## Verificação automatizada

```bash
python scripts/ops/report_lei15_core_002_implantation.py
python -m pytest tests/test_lei15_core_002_sovereign.py -q
```

Saída JSON: `reports/lei15_core_002_implantation_2026_06_17.json`
