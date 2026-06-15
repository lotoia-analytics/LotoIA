# ADR — Expansão Científica Governada e Limites de Fechamento

| Campo | Valor |
|-------|-------|
| **Número** | ADR-EXPANSAO-FECHAMENTO-LIMITES |
| **Status** | Accepted |
| **Data** | 12/06/2026 |
| **Missão** | `DOC_SEPARATE_EXPANSION_FROM_MATHEMATICAL_CLOSURE` |

---

## Contexto

A plataforma LotoIA opera com:

- **Geração soberana Lei 15** (`basic_generator`) para cartões 15D
- **Expansão dimensional** 16D–23D documentada em ADR dedicada
- **Motor de expansão científica** (`scientific_expansion_engine`) para amostragem governada de candidatos expandidos
- **Ciclo operacional** com reconciliação, retenção e telemetria — historicamente referido como "fechamento" em CLI e dashboard

Surge risco institucional de **colisão semântica**:

| Termo ambíguo | Leitura incorreta | Leitura correta na LotoIA |
|---------------|-------------------|---------------------------|
| Fechamento | Fechamento matemático / covering design | Fechamento **operacional** (fim de ciclo) |
| Expansão | Fechamento comercial de loteria | Expansão **científica governada** (amostragem ADR) |
| Garantia | Premiação assegurada por combinatória | Evidência estatística sem promessa de ganho |

Sem ADR explícita, agentes, comunicação e auditoria podem atribuir à LotoIA capacidades **não implementadas e não aprovadas**.

---

## Decisão

### 1. Expansão científica governada — permitida

A LotoIA **possui** expansão científica governada, definida como:

> Amostragem inteligente de candidatos expandidos, submetida a regras institucionais, scoring estrutural, limites de overlap/Hamming, política dimensional e rastreabilidade — **sem garantia formal de premiação**.

**Componentes no escopo:**
- `src/lotoia/combinatorics/scientific_expansion_engine.py`
- Expansão dimensional Lei 15 / Lei 15A (16D–20D operacional; 21D–23D observacional)
- Memória científica e lifecycle de expansão validada (ADR-035)

**Classificação:** experimental ou ADR-scoped — **não** componente institucional soberano de geração 15D.

### 2. Fechamento matemático — vetado

A LotoIA **não implementa** e **não aprova** fechamento matemático clássico, incluindo:

- covering designs com garantia de cobertura de subconjuntos
- wheeling systems com promessa de faixa de acertos
- esquemas que asseguram premiação alvo por combinatória finita

**Veto institucional:**
- Nenhum módulo de geração ou conferência pode ser documentado ou comercializado como "fechamento matemático"
- Nenhuma promoção a motor principal sem ADR + benchmark temporal + relatório comparativo

### 3. Fechamento operacional — mantido com disambiguação

O termo **fechamento operacional** permanece válido para:

- `operational_lifecycle` / CLI `operational-lifecycle`
- reconciliação pós-sorteio, retenção de jogos premiados, telemetria, backups
- encerramento de ciclo diário no painel ADM

**Obrigatório:** em documentação nova, usar **"fechamento operacional"** ou **"encerramento de ciclo"** — nunca "fechamento" isolado quando o leitor possa inferir combinatória.

---

## Limites explícitos

| Capacidade | LotoIA | Requisito para mudança |
|------------|--------|------------------------|
| Geração 15D soberana (Lei 15) | ✅ Sim | Intocável sem ADR Lei 15 |
| Expansão 16D–20D governada | ✅ Sim (ADR dimensional) | ADR + testes |
| Amostragem `scientific_expansion_engine` | ✅ Sim (experimental) | ADR + benchmark |
| Fechamento matemático / covering | ❌ Não | Nova ADR + comitê + benchmark — **não iniciado** |
| Garantia de prêmio por combinatória | ❌ Não | Proibido por comunicação institucional |
| Fechamento operacional | ✅ Sim | Manter; disambiguar em docs |

---

## Guardrails (não negociáveis)

1. **`basic_generator` permanece soberano Lei 15** — expansão não substitui geração 15D.
2. **`combinatorics` não é promovido a motor principal** — permanece auxiliar/experimental.
3. **`scientific_expansion_engine` permanece experimental ou ADR-scoped** — sem promoção institucional sem relatório comparativo temporal.
4. **Nenhuma alegação de garantia de prêmio** — em código, docs, dashboard ou canais (WhatsApp, ManyChat).
5. **Nenhum uso de "fechamento" para geração de cartão** sem ADR explícita que não existe hoje.

---

## Consequências

### Positivas

- Terminologia auditável para agentes, ADM e comunicação externa
- Proteção contra expectativa de "fechamento de loteria" no produto LotoIA
- Separação clara: **porteiro/captação** (ManyChat) ≠ **operação** (WhatsApp) ≠ **expansão científica** ≠ **ciclo operacional**

### Negativas / trade-offs

- Termo "fechamento" em código legado (CLI) permanece — exige qualificador em docs
- Expansão científica não pode ser vendida como diferencial de "garantia combinatória"
- Qualquer futuro covering design exige trilha ADR completa — fora do escopo atual

---

## Conformidade

| Critério da missão | Status |
|--------------------|--------|
| Termo fechamento matemático não usado para expansão atual | ✅ |
| Fechamento operacional disambiguated | ✅ |
| Lei 15 intocada | ✅ |
| Nenhum código alterado | ✅ |
| Documentação criada | ✅ |

**Documento complementar:** `docs/governance/EXPANSAO_GOVERNADA_VS_FECHAMENTO_MATEMATICO.md`

---

## Referências

- `docs/governance/ADR_EXPANSAO_DIMENSIONAL_16D_23D.md`
- `docs/governance/LEI_15_NUCLEO_OPERACIONAL_15D.md`
- `docs/governance/ADR_LEI15A_CARTAO_REGISTRO_APOSTA.md`
- `docs/governance/COMUNICACAO_INSTITUCIONAL.md`
- `docs/architecture/EXPANSION_POLICY.md`
- `docs/governance/POLITICA_ML_ASSISTIVO.md` (ML auxiliar — paralelo: não substituir soberania)
- `ADRs/ADR-035-CYCLE-CLOSURE-HYBRID-OPERATIONAL-MATURATION.md`

---

## Histórico

| Data | Evento |
|------|--------|
| 12/06/2026 | ADR aceita — missão `DOC_SEPARATE_EXPANSION_FROM_MATHEMATICAL_CLOSURE` |
