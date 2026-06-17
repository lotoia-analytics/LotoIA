# M-VIS-046 — Corrigir resíduo visual Lei 15A operacional no Runtime Limpo ADM 15

| Campo | Valor |
|-------|-------|
| Missão | M-VIS-046 |
| Tipo | Correção visual / constitucional |
| Build ADM | `institutional-adm-runtime-v21` |
| Pré-requisito | M-GOV-038 (Lei 15A inoperante) |

## Problema

A página **Runtime Limpo ADM 15 / Gerador ADM CORE_002** exibia linguagem incompatível com M-GOV-038:
selectbox 16D–23D, "Lei 15 + N reservas auditadas", "Leitura operacional Lei 15A".

## Correção

- Formato fixo **15D CORE_002** — selectbox expansivo removido
- Bloco constitucional Lei 15A **futura/inoperante** visível
- Resultados sem painel "Leitura operacional Lei 15A"
- Geração soberana + ML supervisionado preservados

## Veredicto alvo

**M-VIS-046 CONCLUÍDA E ATIVA EM PRODUÇÃO — RESÍDUO VISUAL LEI 15A OPERACIONAL REMOVIDO / CORE_002 15D PRESERVADO**
