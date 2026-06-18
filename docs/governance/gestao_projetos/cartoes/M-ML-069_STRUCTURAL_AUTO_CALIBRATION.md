# M-ML-069 — Calibração Estrutural Automática Format-Aware 16D–23D

**Status:** CONCLUÍDA  
**Build marker:** `institutional-adm-runtime-v57`  
**Missão:** `M-ML-069`

## Contexto

M-ML-068 diagnosticou concentração estrutural (prefixos, sufixos, bases, cobertura, diversidade). M-ML-069 transforma esses diagnósticos em **ações automáticas** da Central ML — o operador apenas valida.

## Escopo

Formatos suportados: **16D, 17D, 18D, 19D, 20D, 21D, 22D, 23D** — sem regras exclusivas para 17D.

## Ações automáticas

| Causa detectada | Ação |
|-----------------|------|
| Prefixo dominante | Reduzir score do prefixo; reforçar alternativas |
| Sufixo dominante | Reduzir score do sufixo; reforçar alternativas |
| Baixa diversidade de bases | Penalizar derivações da base dominante |
| Expansão superficial | Rotacionar dezenas adicionais |
| Dezenas subcobertas | Aumentar peso de cobertura |
| Dezenas excessivas | Reduzir peso de recorrência |
| Rerank concentrado | Rerank com diversidade + cobertura |

## Calibração progressiva

1ª ocorrência: intensidade **baixa**  
2ª ocorrência: intensidade **moderada**  
3ª+: intensidade **alta**

## Memória ML

`structural_calibration_memory` — por formato 16D–23D, registra causa, ação, intensidade e parâmetros.

## Implementação

- Módulo: `src/lotoia/ml/structural_auto_calibration.py`
- Integração calibração: `src/lotoia/ml/supervised_output_calibration.py`
- Evidência Central ML: `src/lotoia/observability/coverage_evidence_interpreter.py`
- Cockpit: `dashboard/institutional_ml_calibration_cockpit.py`
- Testes: `tests/ml/test_m_ml_069_structural_auto_calibration.py`

## Restrições preservadas

- M-ML-067 intacta
- CORE_002, Lei 15, Lei 15A, `public_app` sem alteração
- Sem purge
- Sem `calibration_depth` / aprendizagem acumulativa profunda
