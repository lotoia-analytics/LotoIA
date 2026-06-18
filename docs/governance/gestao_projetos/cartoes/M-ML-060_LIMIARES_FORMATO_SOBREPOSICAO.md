# M-ML-060 — Limiares de sobreposição por formato (15D–23D)

| Campo | Valor |
|-------|-------|
| **Missão** | M-ML-060 |
| **Build ADM** | `institutional-adm-runtime-v42` |
| **Status** | CONCLUÍDA |

## Objetivo

Registrar memória ML de limiares de sobreposição máxima para formatos 15D–23D e exibir vereditos por formato na Central ML, cruzando overlap com similaridade, quase repetidos e diversidade.

## Entregáveis

- `src/lotoia/ml/overlap_format_thresholds.py` — memória e classificação por formato
- `redundancia_por_formato` no payload da Cobertura Estrutural
- Central ML — seção limiares/veredito por formato no cockpit
- Plano de calibração usa formato correto na recomendação

## Regra geral

Para formato N: N=crítico; N-1=ruim; N-2=atenção; até N-3=bom (com cruzamento estrutural).
