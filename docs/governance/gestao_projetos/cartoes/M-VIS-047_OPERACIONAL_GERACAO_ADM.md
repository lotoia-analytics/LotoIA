# M-VIS-047 — Simplificação Operacional da Página de Geração ADM CORE_002

| Campo | Valor |
|-------|-------|
| Missão | M-VIS-047 |
| Tipo | Simplificação visual / operacional |
| Build ADM | `institutional-adm-runtime-v23` |
| Pré-requisito | M-VIS-046, M-GER-044, M-ML-045 |

## Problema

A página de geração ADM exibia excesso de banners, textos explicativos, alertas repetidos e blocos institucionais na área principal — poluição visual incompatível com operação diária.

## Correção

- Título operacional: **Gerador ADM CORE_002**
- Quantidade de jogos: campo numérico livre **1–100**
- Quantidade de dezenas: seleção **15–23** (formato multidezena CORE_002 — **não** Lei 15A)
- Estratégia: **CORE_002 + ML supervisionado**
- Botão: **Gerar lote**
- Resultado compacto: generation_event_id, batch_label, solicitados, persistidos, gerados
- Status em chips: CORE_002 ativo · ML supervisionado · Lei 15A inoperante
- Governança, PostgreSQL, path técnico e avisos longos → expansores fechados
- Persistência 16D–23D: bloqueio técnico explícito (preview permitido; persistência apenas 15D validada)

## Proibições respeitadas

- Lei 15A não reativada
- Sem linguagem "reserva auditada", "15+1", "15+2", "Leitura operacional Lei 15A"
- `public_app` inalterado
- Sem purge, sem alteração de schema, sem deploy manual

## Veredicto alvo

**M-VIS-047 CONCLUÍDA — PÁGINA DE GERAÇÃO ADM CORE_002 SIMPLIFICADA, COM QUANTIDADE DE JOGOS 1–100 E SELEÇÃO DE DEZENAS 15–23**
