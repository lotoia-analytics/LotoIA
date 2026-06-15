# Expansão Governada vs Fechamento Matemático

| Campo | Valor |
|-------|-------|
| **Missão** | `DOC_SEPARATE_EXPANSION_FROM_MATHEMATICAL_CLOSURE` |
| **Status** | Formalizado |
| **Data** | 12/06/2026 |
| **Owner** | agent_governanca |

---

## Objetivo

Eliminar ambiguidade terminológica entre:

1. **Expansão científica governada** — o que a LotoIA **possui e permite**
2. **Fechamento matemático** — o que a LotoIA **não implementa nem aprova**
3. **Fechamento operacional** — rotina institucional de fim de ciclo/dia (termo mantido, sentido distinto)

Este documento **não altera** Lei 15, Lei 15A, `basic_generator`, motores combinatórios, regras de geração ou conferência.

---

## Posicionamento oficial

> A LotoIA possui **expansão científica governada** (amostragem inteligente sob regras institucionais).
>
> A LotoIA **não possui fechamento matemático clássico** (covering design com garantia formal de prêmio alvo).

---

## Definições normativas

### 1. Expansão científica governada

| Atributo | Valor |
|----------|-------|
| **Significado** | Amostragem inteligente governada por regras institucionais, scoring estrutural, limites de overlap/Hamming, quotas de perfil e política dimensional Lei 15 / Lei 15A |
| **Status** | **Permitida** — escopo experimental ou ADR |
| **Implementação** | `scientific_expansion_engine`, expansão dimensional 16D–20D sob ADR, memória científica pós-reconciliação |
| **Garantia** | **Nenhuma** garantia de premiação ou cobertura formal |

**O que faz:**
- explora candidatos expandidos (16D–20D) com filtros e ranking
- respeita soberania da Lei 15 na geração 15D
- opera sob limites de runtime, candidatos e distância mínima
- produz evidência auditável (métricas, logs, ADR)

**O que não faz:**
- não promete acerto de faixa-alvo (11+, 14, 15)
- não substitui `basic_generator` como motor soberano 15D
- não é covering design nem wheeling system clássico

**Referências:**
- `src/lotoia/combinatorics/scientific_expansion_engine.py`
- `docs/governance/ADR_EXPANSAO_DIMENSIONAL_16D_23D.md`
- `docs/architecture/EXPANSION_POLICY.md`

---

### 2. Fechamento matemático

| Atributo | Valor |
|----------|-------|
| **Significado** | Esquema combinatório (ex.: covering design, fechamento por garantia de t-cover) que **assegura formalmente** cobertura de combinações ou premiação em faixa declarada |
| **Status** | **Não implementado. Não aprovado.** |
| **Uso do termo** | **Proibido** para descrever expansão atual, geração de cartões ou promessa institucional |

**Exemplos de linguagem proibida:**
- "fechamento matemático da Lotofácil"
- "garantia combinatória de 14 pontos"
- "cobertura total de subconjuntos"
- "fechamento que assegura premiação"

**Contraste com o mercado** (comunicação institucional):

A LotoIA **não** oferece "fechamentos matemáticos sobre dezenas escolhidas arbitrariamente" — ver `docs/governance/COMUNICACAO_INSTITUCIONAL.md`.

---

### 3. Fechamento operacional

| Atributo | Valor |
|----------|-------|
| **Significado** | Rotina de **fim de ciclo operacional**: reconciliação, detecção de prêmios, retenção/remoção de jogos, telemetria, backups, relatório de dashboard |
| **Status** | **Mantido** — termo válido com escopo operacional |
| **Implementação** | `operational_lifecycle`, CLI `operational-lifecycle`, workflows de reconciliação |

**Disambiguação obrigatória:**

| Termo | Domínio | Pergunta que responde |
|-------|---------|------------------------|
| Fechamento **operacional** | Runtime / persistência | "O ciclo do concurso foi encerrado, reconciliado e arquivado?" |
| Fechamento **matemático** | Combinatória | "Existe garantia formal de cobertura de prêmio?" → **Não na LotoIA** |
| Expansão **governada** | Geração científica | "Como ampliamos cartões 16D–20D com regras auditáveis?" |

**Onde aparece no código (sem renomear):**
- `lotoia operational-lifecycle` — "fechamento operacional completo"
- Dashboard ADM — "fechamento diário" em fluxos operacionais

Ao documentar ou comunicar, preferir **"encerramento operacional"** ou **"ciclo operacional"** quando houver risco de confusão com combinatória.

---

## Mapa conceitual

```text
Geração soberana (Lei 15 / basic_generator)
        │
        ├─► 15D operacional ─────────────────► Conferência / WhatsApp
        │
        └─► Expansão dimensional governada (16D–20D, ADR)
                    │
                    └─► scientific_expansion_engine
                              (amostragem + filtros + ranking)
                              ≠ fechamento matemático

Ciclo pós-sorteio
        │
        └─► Fechamento OPERACIONAL
              (reconciliação, retenção, telemetria, backup)
              ≠ fechamento MATEMÁTICO
```

---

## Guardrails institucionais (intocáveis)

| Guarda | Estado |
|--------|--------|
| `basic_generator` permanece soberano Lei 15 | ✅ Confirmado |
| `combinatorics` não promovido a motor principal | ✅ Confirmado |
| `scientific_expansion_engine` permanece experimental/ADR | ✅ Confirmado |
| Nenhuma alegação de garantia de prêmio | ✅ Confirmado |
| Nenhum uso de "fechamento" para geração de cartão sem ADR | ✅ Confirmado |

**Não alterar sem nova ADR:**
- Lei 15 / Lei 15A
- `basic_generator`
- `scientific_expansion_engine` (promoção a componente institucional principal)
- `combinatorics` / `expansion_engine` como motor de produção
- Regras de conferência (`conference_rules`)

---

## Termos: uso correto vs incorreto

| Contexto | ✅ Usar | ❌ Não usar |
|----------|---------|-------------|
| Expansão 16D–20D | expansão científica governada, expansão dimensional ADR | fechamento, fechamento matemático |
| Motor combinatório experimental | amostragem governada, candidatos premium | garantia combinatória |
| Fim do dia operacional | fechamento operacional, encerramento de ciclo | fechamento (isolado, sem qualificador) |
| Comunicação pública | análise estrutural, evidência estatística | método infalível, garantia de ganho |
| Lotofácil mercado tradicional | (contraste) fechamentos comerciais de terceiros | atribuir isso à LotoIA |

---

## Auditoria terminológica (repositório)

Verificação em 12/06/2026:

| Verificação | Resultado |
|-------------|-----------|
| `fechamento matemático` usado para expansão atual | **Não encontrado** |
| `covering design` como feature implementada | **Não encontrado** |
| `fechamento` em contexto operacional (lifecycle) | Presente — **manter com disambiguação** |
| `scientific_expansion_engine` descrito como garantia | **Não encontrado** |
| Lei 15 / basic_generator alterados nesta missão | **Não** — somente documentação |

---

## Referências cruzadas

| Documento | Papel |
|-----------|-------|
| `docs/adr/ADR_EXPANSAO_E_FECHAMENTO_LIMITES.md` | ADR de limites e veto formal |
| `docs/governance/ADR_EXPANSAO_DIMENSIONAL_16D_23D.md` | Matriz 15D→23D |
| `docs/governance/LEI_15_NUCLEO_OPERACIONAL_15D.md` | Soberania 15D |
| `docs/governance/COMUNICACAO_INSTITUCIONAL.md` | Tom e alegações proibidas |
| `docs/architecture/EXPANSION_POLICY.md` | Política de expansão arquitetural |
| `ADRs/ADR-035-CYCLE-CLOSURE-HYBRID-OPERATIONAL-MATURATION.md` | Maturação operacional (não combinatória) |

---

## Regra para agentes e revisores

Antes de usar a palavra **fechamento**, responder:

1. É **operacional** (ciclo, logs, reconciliação)? → OK com qualificador.
2. É **combinatório** (garantia de prêmio/cobertura)? → **Vetado** — não existe na LotoIA.
3. É **expansão de cartão** (16D–20D)? → Usar **expansão científica governada**.

Em caso de dúvida, preferir termos explícitos e evitar "fechamento" isolado.
