# M-ML-060-FIX-01 — Veredito ML e Bloqueio de Oficialização

## Status

**CONCLUÍDA** — Central ML emite veredito operacional forte e bloqueia oficialização de lote crítico.

## Build marker

`institutional-adm-runtime-v43`

## Objetivo

Transformar limiares críticos da Cobertura Estrutural em **VEREDITO ML** operacional, impedindo liberação oficial de lotes críticos sem calibração.

## Vereditos

| Veredito | Liberação oficial |
|----------|-------------------|
| APROVADO | Sim |
| APROVADO COM ALERTA | Sim |
| PRECISA CALIBRAR | Não |
| REPROVADO | Não |
| BLOQUEADO PARA OFICIALIZAÇÃO | Não |

## Componentes

| Módulo | Responsabilidade |
|--------|------------------|
| `src/lotoia/ml/ml_operational_verdict.py` | Regras de veredito e bloqueio |
| `coverage_evidence_interpreter.py` | Veredito na leitura soberana |
| `institutional_ml_calibration_cockpit.py` | Exibição VEREDITO ML |
| `institutional_app.py` | Gate na persistência + filtros Histórico/Conferência |

## Persistência

Campos em `GenerationEvent.context_json`:

- `ml_verdict`
- `ml_verdict_reason` / `motivo_principal`
- `official_release_allowed`
- `officialization_status`
- `ml_verdict_trace`

## Restrições respeitadas

- CORE_002, Lei 15, Lei 15A e `public_app` intactos
- Sem purge
- Sem alteração de schema
