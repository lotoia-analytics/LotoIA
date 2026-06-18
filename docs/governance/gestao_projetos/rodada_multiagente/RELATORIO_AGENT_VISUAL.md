# Pacote Visual Núcleo Lei 15 — Plano Faseado (read-only)

**Agente:** `agent_visual`  
**Missão:** Pacote Visual Núcleo Lei 15 no Painel ADM  
**Veredicto:** **CONCLUÍDO PARCIALMENTE — PLANO FASEADO ENTREGUE (SEM IMPLEMENTAÇÃO EM MASSA)**

---

## Objetivo

Reestruturar leitura visual do Núcleo soberano `LEI15_CORE_002` sem tratar CORE_002 como
cartão fixo de 15 dezenas; separar evidência histórica (V1, CAND-D, V2/V3/V4, baseline)
do Núcleo soberano.

---

## Decisão: não implementar todas as telas nesta rodada

Risco de tocar **muitas telas** (`structural_coverage`, `hb_metrics`, gerador bloqueado,
home, sidebar) simultaneamente → **parar em plano faseado** conforme instrução institucional.

---

## Fases propostas

### Fase A — Labels e banners (baixo risco)

- Renomear captions em Cobertura Estrutural: “evidência histórica” vs “Núcleo soberano”
- Banner read-only em Matriz Soberana CORE_002 (nova sub-rota ou tab em Governança)
- Garantir V1/CAND-D/V2/V3 como **histórico**, não operacional

### Fase B — Menu (médio risco)

- Agrupar “Núcleo Lei 15 — leitura” sob Governança ou submenu dedicado read-only
- Fusões seguras: Benchmark resumido + Métricas HB → “Diagnóstico HB observacional”

### Fase C — 6 Bases + dezenas críticas (médio risco, depende agent_estatistico)

- Integrar especificação estatística (`ESPECIFICACAO_6_BASES_COBERTURA_ESTRUTURAL.md`)
- Cobertura Estrutural: leitura pelas 6 Bases, sem recalibração

---

## Proibido em todas as fases

- Botão de geração; purge; alteração de Núcleo; Lei 15A operacional

---

## Próximo passo

Missão **M-VIS-033** (proposta): Fase A do Pacote Visual — labels e banners read-only.
