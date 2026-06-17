# Relatório Técnico — Roteamento Único LEI15_CORE_002

**Data:** 2026-06-17  
**Registro:** `LEI15_GENERATION_ROUTING_ADR_047`  
**ADR:** ADR-047-TRANSICAO-CONSTITUCIONAL-LEI15-CORE002  
**Agente:** agent_geracao  

## Objetivo

Bloquear caminhos legados de geração Lei 15 e garantir que qualquer geração futura só possa ocorrer pelo Núcleo Soberano **LEI15_CORE_002**, com label institucional explícito.

## Veredicto

**PATH ÚNICO CORE_002 GARANTIDO — LEGACY DEFAULT BLOQUEADO — V1 ACTIVE GLOBAL BLOQUEADO FORA DO CORE_002 — GERAÇÃO BLOQUEADA POR FLAG**

## Implementação

### Política central

Módulo: `src/lotoia/governance/lei15_generation_routing_policy.py`

- `enforce_lei15_generation_routing()` — fail-closed antes de qualquer geração
- `enforce_legacy_lei15_entry_blocked()` — bloqueia `batch_label=None`
- `assert_v1_active_global_blocked()` — impede `LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1=active` fora do compose interno
- `effective_should_apply_gp_realignment()` — V1 global desabilitado quando `apply_sovereign=True`
- `resolve_generation_routing()` — matriz de decisão institucional
- `attach_routing_payload_to_games()` — rastreabilidade obrigatória

### Entradas bloqueadas

| Entrada | Bloqueio |
|---------|----------|
| `batch_label=None` | Legacy default operacional |
| `generate_filtered_game()` | Sem label soberano |
| `generate_multiple_games()` | Sem label soberano |
| Labels V1/V2/V3/V4/CAND-001/baseline | Evidência histórica — não operacional |
| `STRUCT_TEST_15D_001` | Congelado — `assert_no_new_legacy_extensive_lot` |
| V1 `active` global | Sequestro de GP bloqueado |

### Caminho soberano autorizado (quando flag=1)

```python
generate_best_games(
    batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001"
)
```

- **batch_type:** `LEI15_CORE_002_SOVEREIGN`
- **generation_path:** `LEI15_CORE_002`
- **Flag:** `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=1` (padrão: `0`)

### Payload de rastreabilidade

Campos anexados a cada jogo e ao retorno de `generate_best_games`:

- `lei15_core_002_applied`
- `sovereign_core_status`
- `batch_label`
- `batch_type`
- `generation_path`
- `legacy_path_blocked`
- `v1_active_global_blocked`
- `perfil_origem_real` / `perfil_label_final` (via camadas CORE_002)
- `prefix_signature` / `suffix_signature`
- `relabeling_applied` / `relabeling_reason`

### Integração

- `src/lotoia/generator/basic_generator.py` — guardas em todas as entradas de geração Lei 15
- `backend/main.py` — endpoints GET `/generate/*` propagam erro institucional (422/500)
- Testes: `tests/test_lei15_core_002_generation_routing.py`, `tests/conftest.py`

## Fora de escopo (próximas missões)

- Painel ADM (`_generate_direct_15_games`) — agent_visual + agent_plataforma
- Lei 15A — suspensa
- Promoção active — não autorizada

## Artefatos

- JSON: `reports/lei15_core_002_generation_routing_2026_06_17.json`
- Script: `scripts/ops/report_lei15_core_002_generation_routing.py`

## Confirmação

Esta missão **não gerou jogos**. Geração permanece bloqueada por `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0`.
