# M-ML-VIS-058-FIX-01 — Plano de calibração detalhado na Central ML

| Campo | Valor |
|-------|-------|
| **Missão** | M-ML-VIS-058-FIX-01 |
| **Agentes** | agent_ml + agent_visual + agent_dados + agent_qualidade |
| **Build ADM** | `institutional-adm-runtime-v40` |
| **PR mergeada** | [#177](https://github.com/lotoia-analytics/LotoIA/pull/177) → `main` @ `611dddc` |
| **Commit** | `7bd3035` |
| **Status** | CONCLUÍDA |

## Rastreio de PR

| PR | Base | Resultado |
|----|------|-----------|
| [#176](https://github.com/lotoia-analytics/LotoIA/pull/176) | `cursor/gestao-projetos-fase0-cae6` | **Fechado sem merge** (draft + base incorreta) |
| [#177](https://github.com/lotoia-analytics/LotoIA/pull/177) | `main` | **Mergeada** — PR canônico desta missão |

## Objetivo

Ampliar a Central ML para transformar evidências da Cobertura Estrutural em **Plano de calibração recomendado** operacional, com impacto detalhado, persistência completa na autorização e uso do plano autorizado na próxima geração CORE_002.

## Entregáveis

- `build_calibration_plan()` em `coverage_evidence_interpreter.py`
- Seção UI **Plano de calibração recomendado** (lista numerada)
- Seção **Impacto esperado** (bullets por ação)
- `build_cockpit_persist_bundle()` persiste plano, impacto, parâmetros, operador, trace
- `resolve_authorized_calibration_plan()` + passagem para `generate_best_games` → `apply_supervised_output_calibration`

## Restrições respeitadas

- CORE_002, Lei 15, Lei 15A e `public_app` intactos
- Sem alteração de schema
- Sem purge
