# M-UI-ML-001 — Central ML: simplificação e redesign operacional

**Status:** CONCLUÍDA  
**BUILD_MARKER:** `institutional-adm-runtime-v76`  
**Branch:** `cursor/m-ui-ml-001-central-ml-redesign-a4bb`

## Objetivo

Transformar a Central ML em tela operacional simples, responsiva e orientada à decisão — sem alterar geração, cálculos ML, Lei 15 ou CORE_002.

## Antes

- Layout em duas colunas com dezenas de cards técnicos visíveis na área principal.
- Diagnóstico misturava métricas operacionais com `generation_event_ids`, checksums e filtros.
- Hierarquia ML (M-ML-073), pools (M-ML-071/072), routing (M-GOV-AGENTS-002), overlap matrix e política 15D ocupavam a visão principal.
- Seções “Impacto esperado” e “Resultado da calibração” competiam com o fluxo de decisão.
- Múltiplas linhas de metadados (Lei 15A, purge, GE, formato) acima do conteúdo decisório.
- Rolagem vertical longa antes de chegar aos comandos supervisionados.

## Depois

Estrutura vertical única:

```
Central ML
├── 1. Diagnóstico geral da saída (7 métricas operacionais)
├── 2. Evidências e decisão (veredito, motivo, liberação, próxima ação)
├── 3. Plano de calibração recomendado
├── 4. Comando supervisionado (5 botões)
└── Auditoria Técnica (recolhida por padrão)
```

## Removido da visão principal

| Item | Destino |
|------|---------|
| `generation_event_ids`, checksums, filtros de leitura | Auditoria Técnica → Diagnóstico — detalhes técnicos |
| Gerações/jogos agregados, Risco 6 Bases, hits 13/14/15 | Auditoria Técnica → Diagnóstico — detalhes técnicos |
| Hierarquia operacional ML (M-ML-073) | Auditoria Técnica |
| Pool estrutural 15D (M-ML-072) | Auditoria Técnica |
| Pool pré-final calibrado (M-ML-071) | Auditoria Técnica |
| Plano autorizado N→N+1 (M-ML-075) | Auditoria Técnica |
| Política estrutural 15D (M-ML-070) | Auditoria Técnica |
| Calibração estrutural automática (M-ML-069) | Auditoria Técnica |
| Agente responsável / routing matrix (M-GOV-AGENTS-002) | Auditoria Técnica |
| Limiares overlap por formato (M-ML-060/067) | Auditoria Técnica |
| Impacto esperado | Auditoria Técnica |
| Resultado da calibração / validação N vs N+1 | Auditoria Técnica |
| Metadados Lei 15A, purge, public_app, GE detalhado | Auditoria Técnica → Escopo operacional |
| Blocos decisórios extensos, política 15D inline | Auditoria Técnica → Evidências — detalhes técnicos |
| Seção “Detalhes técnicos” aberta | Fundida em Auditoria Técnica (recolhida) |

## Preservado em Auditoria Técnica

- Todos os expanders de rastreabilidade (`_render_technical_expanders`).
- Traces, feature attribution, 6 bases, histórico PostgreSQL.
- Proteções constitucionais, registro completo da decisão ML.
- Memória ML format-aware 15D–23D.
- Auditoria M-ML-068 concentração estrutural.

## Parecer agent_direito (UX operacional)

| Critério | Avaliação |
|----------|-----------|
| Legibilidade | Aprovado — 4 blocos numerados, leitura vertical |
| Objetividade | Aprovado — pergunta “lote saudável?” respondida no bloco 1 |
| Proporcionalidade | Aprovado — métricas em 2 linhas (4+3), sem blocos gigantes |
| Excesso de texto | Reduzido — captions técnicas removidas da área principal |
| Rolagem para decisão | Melhorada — comandos após 4 seções curtas |
| Desktop / notebook | Mantida — colunas responsivas dentro de cada bloco |
| Rastreabilidade | Preservada — Auditoria Técnica recolhida, não removida |

## Confirmação funcional

- Nenhuma alteração em `src/lotoia/ml/`, geração, persistência, promoção de lotes ou Lei 15.
- Botões de comando supervisionado inalterados (mesmas ações e persistência).
- Snapshot e cálculos ML consumidos sem modificação — apenas reorganização de renderização.

## Veredito

**M-UI-ML-001 CONCLUÍDA — CENTRAL ML REDESENHADA, RESPONSIVA E ORIENTADA À DECISÃO OPERACIONAL**
