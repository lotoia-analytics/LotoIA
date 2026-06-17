# Especificação Estatística — 6 Bases e Cobertura Estrutural

**Agente:** `agent_estatistico`  
**Veredicto:** **CONCLUÍDO — ESPECIFICAÇÃO ENTREGUE (DOCUMENTAL)**

---

## 1. Regra temporal (mandatória)

Concurso **X** usa apenas dados até **X-1**. Walk-forward obrigatório. Sem leakage.

---

## 2. Métricas propostas (6 Bases / cobertura)

| Métrica | Descrição |
|---------|-----------|
| Força de acerto | Média ponderada de hits em janela walk-forward |
| Diversidade suficiente | Entropia / cobertura de combinações sem colapso |
| Baixa redundância | Penalidade de overlap entre jogos do lote |
| Controle prefixo/sufixo | Distribuição faixas 1–9 / 16–25 |
| Cobertura dezenas críticas | Presença de dezenas estruturalmente prioritárias |
| Estabilidade multi-concurso | Variância de métricas em janelas 10/20/30 |

---

## 3. Janelas de validação

10, 20, 30 concursos — comparáveis entre si; nunca misturar futuro.

---

## 4. Diferença entre fluxos (read-only)

| Fluxo | Propósito |
|-------|-----------|
| Conferir Resultados | Confronto seleção × resultado oficial persistido |
| Simular Resultados | Cenário hipotético / stress observacional |
| Benchmark Histórico | Comparativo agregado temporal |
| Cobertura Estrutural | Leitura 6 Bases + dezenas críticas — **sem gerar** |

---

## 5. Próximo passo

Integrar em Pacote Visual Fase C (`RELATORIO_AGENT_VISUAL.md`).

---

## Confirmações

- Nenhuma calibração de produção
- Nenhuma geração executada
