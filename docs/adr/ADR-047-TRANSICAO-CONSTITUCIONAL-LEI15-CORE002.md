# ADR-047 — Transição Constitucional da Lei 15 pós-Auditoria (LEI15_CORE_002)

## Status

**TRANSIÇÃO CONSTITUCIONAL REGISTRADA**

| Campo | Valor |
|-------|-------|
| Registro | `ADR_047_TRANSICAO_CONSTITUCIONAL_LEI15_CORE002` |
| Data | 2026-06-17 |
| Agente | `agent_governanca` |
| Escopo desta ADR | **Governança e registro institucional apenas** — sem implementação de runtime |
| Núcleo soberano | `LEI15_CORE_002` |
| Label técnico | `STRUCT_LEI15_CORE_CANDIDATE_002_15D_001` |
| Status institucional | `NUCLEO_SOBERANO_LEI15` |
| Geração operacional | **BLOQUEADA** até missões posteriores |
| Painel ADM | **NÃO ATUALIZADO** nesta ADR — atualização autorizada **somente após** este registro |
| Lei 15A operacional | **SUSPENSA** |
| Implementação de código | **NÃO AUTORIZADA** por esta ADR |

---

## Contexto

A **Auditoria Constitucional da LotoIA** (`AUDITORIA_CONSTITUCIONAL_LOTOIA_2026_06_17`) concluiu:

> **LOTOIA CONFLITANTE — EXIGE CORREÇÃO ANTES DO PAINEL**

A auditoria confirmou que o **Núcleo Soberano LEI15_CORE_002** existe e está implantado (ADR-046, `src/lotoia/governance/lei15_core_002_sovereign.py`, `src/lotoia/generation/lei15_core_002.py`), com geração bloqueada por padrão (`LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0`).

Porém, a plataforma ainda opera com **camadas constitucionais concorrentes**:

- documento `LEI_15_NUCLEO_OPERACIONAL_15D.md` tratando a Lei 15 como **núcleo fixo de 15 dezenas**;
- Painel ADM gerando por `_generate_direct_15_games` (caminho paralelo);
- Lei 15A antiga com expansão mecânica 15+1/15+2 e reservas fixas;
- purge de histórico sem proteção de evidência institucional;
- rotas/API legadas com `batch_label=None` ou sem label soberano;
- V1 em modo `active` capaz de sequestrar composição global;
- baseline legado ainda disponível como default operacional.

Esta ADR **não corrige o sistema**. Registra a **Constituição nova** da Lei 15 e a **ordem de transição** para missões posteriores, roteadas por agente, sem mistura de responsabilidades.

---

## Problema constitucional identificado

| # | Conflito | Classificação |
|---|----------|---------------|
| P1 | Dois conceitos de Núcleo Lei 15: cartão fixo 15D vs matriz soberana CORE_002 | **CONFLITANTE** |
| P2 | Dois motores de geração Lei 15: `basic_generator` (soberano) vs `_generate_direct_15_games` (ADM) | **CONFLITANTE** |
| P3 | Lei 15A mecânica vs gate soberano `open_15a: False` | **CONFLITANTE** |
| P4 | Política de congelamento na **criação** vs purge na **destruição** sem guarda por label | **CONFLITANTE** com Lei 001 |
| P5 | Label metadata-only vs expectativa operacional no painel | **SUSPEITO** |
| P6 | `batch_label=None` como default → motor legado | **CONFLITANTE** como default operacional |

**Raiz do conflito:** a implantação técnica do CORE_002 (ADR-046) antecedeu a **reconciliação documental, operacional e de painel** com o novo paradigma constitucional.

---

## Decisão

A LotoIA adota oficialmente, a partir desta ADR, o seguinte paradigma constitucional da **Lei 15**:

### A Lei 15 **não é** um conjunto fixo de 15 dezenas.

### A Lei 15 **é** uma matriz soberana de papéis das dezenas **01–25**, governada pelo **LEI15_CORE_002**.

Todas as dezenas 01–25 permanecem **elegíveis** para composição de cartões de 15 dezenas. Cada dezena ou bloco estrutural pode atuar, conforme política institucional, sob um ou mais papéis:

| Papel | Descrição |
|-------|-----------|
| **Reforço** | Boost suave na geração/seleção (ex.: 07, 12, 16, 23) |
| **Preservação** | Padrões V1-strong protegidos contra penalização cega |
| **Controle** | Caps estruturais prefixo/sufixo na origem (CAND-D) |
| **Penalização contextual** | Redução de score sem veto absoluto (ex.: 15, 24, 25) |
| **Blind spot** | Injeção estrutural em perfil híbrido (ex.: 06, 16, 17) |
| **Sufixo/prefixo controlado** | Monitoramento de blocos 01–03 / 22–25 sem hard-block |
| **Função estrutural 6 bases** | Avaliação pelas bases institucionais — hit isolado ≠ veredicto |

A avaliação do Núcleo permanece subordinada à **Política das 6 Bases** (`POLITICA_AVALIACAO_NUCLEO_LEI15_6_BASES.md`).

---

## Registro constitucional obrigatório (16 itens)

| # | Registro | Decisão ADR-047 |
|---|----------|-----------------|
| 1 | LEI15_CORE_002 como interpretação soberana vigente da Lei 15 | **Confirmado — SOBERANO** |
| 2 | Conceito antigo de Núcleo fixo 15D | **Obsoleto como fonte soberana** |
| 3 | `LEI_15_NUCLEO_OPERACIONAL_15D.md` | **EVIDÊNCIA HISTÓRICA / LEGADO CONGELADO / NÃO SOBERANO** |
| 4 | Lei 15A antiga (15+1/15+2, reservas mecânicas) | **SUSPENSA** |
| 5 | Lei 15A futura | **Somente camada adaptativa complementar ao CORE_002** — nunca expansão mecânica do antigo 15D |
| 6 | Painel ADM | **Proibido** executar geração Lei 15 por caminho paralelo (missão posterior) |
| 7 | Geração futura | **Obrigatório** passar por `generate_best_games(batch_label=STRUCT_LEI15_CORE_CANDIDATE_002_15D_001)` ou equivalente aprovado por ADR |
| 8 | `_generate_direct_15_games` | **Inválido** como caminho de geração Lei 15 soberana |
| 9 | `batch_label=None` como default | **Inválido** como default operacional para geração Lei 15 |
| 10 | V1, V2, V3, V4, CAND-001, CAND-D, baseline | **EVIDÊNCIA HISTÓRICA** — não caminhos soberanos isolados |
| 11 | Purge / delete_history | **Deve** respeitar proteção de evidência institucional (missão posterior) |
| 12 | Preservação obrigatória | GE 114, GE 115, baseline EPOCH_001, V1, relatórios 6 bases, ADRs, memória institucional |
| 13 | Limpeza operacional | **Somente após** backup + congelamento + classificação por label + autorização `agent_dados` + `agent_governanca` + relatório de preservação |
| 14 | Atualização Painel ADM | **Autorizada somente após** esta ADR registrada |
| 15 | Copy Painel | Lei 15 = matriz soberana 01–25, **não** cartão fixo |
| 16 | Testes/geração futura | **Somente após** Painel corrigido, path CORE_002, purge protegido, legacy default bloqueado, 15A antiga suspensa, geração habilitada explicitamente |

---

## Novo conceito soberano da Lei 15

```yaml
lei_15_constituicao:
  paradigma: matriz_soberana_papeis_dezenas
  universo_elegivel: "01-25"
  tamanho_cartao: 15D
  nucleo_soberano: LEI15_CORE_002
  label_operacional: STRUCT_LEI15_CORE_CANDIDATE_002_15D_001
  status: NUCLEO_SOBERANO_LEI15
  avaliacao: politica_6_bases
  hit_isolado: nao_veredicto
  camadas:
    - generation_cand_d
    - v1_selection_compose
    - v1_strong_shield
    - anti_clone_gp
    - critical_digit_layer
  matriz_papeis_exemplo:
    reforco: [07, 12, 16, 23]
    blind_spot: [06, 16, 17]
    penalizacao_contextual: [02, 04, 11, 15, 24, 25]
    nunca_hard_block: [15, 24, 25]
    sufixo_controlado: [22, 23, 24, 25]
    prefixo_controlado: [01, 02, 03]
```

**Nota:** a matriz acima descreve **papéis institucionais**, não um cartão fixo de 15 dezenas nem um pool fechado.

---

## Classificações constitucionais obrigatórias

| Componente | Classificação ADR-047 |
|------------|----------------------|
| **LEI15_CORE_002** | **SOBERANO** |
| **`LEI_15_NUCLEO_OPERACIONAL_15D.md`** | **LEGADO CONGELADO / EVIDÊNCIA HISTÓRICA / NÃO SOBERANO** |
| **Lei 15A mecânica** (15+1/15+2, `NUCLEO_LEI15_15D_CONGELADO` como expansão) | **SUSPENSA / CONFLITANTE COM O NOVO PARADIGMA** |
| **V1** (`STRUCT_REALIGN_V1_15D_001`) | **EVIDÊNCIA HISTÓRICA / MATRIZ DE FORÇA / NÃO SOBERANA ISOLADA** |
| **CAND-D** (`STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001`) | **EVIDÊNCIA HISTÓRICA / MATRIZ DE CONTROLE / NÃO SOBERANA ISOLADA** |
| **V2 / V3 / V4** | **EVIDÊNCIA HISTÓRICA / NÃO CAMINHO DE EVOLUÇÃO** |
| **Baseline legado** (`STRUCT_TEST_15D_001`) | **LEGADO CONGELADO / CONTROLE HISTÓRICO / NÃO OPERACIONAL** |
| **`_generate_direct_15_games`** | **CONFLITANTE PARA LEI 15 SOBERANA** |
| **`batch_label=None` como default** | **CONFLITANTE COMO DEFAULT OPERACIONAL** |
| **`delete_history` / purge sem guarda por label** | **CONFLITANTE COM LEI 001** |
| **V1 `active` global** | **CONFLITANTE** — compose não pode sequestrar GP soberano |
| **API GET `/generate/*`** | **LEGADO / CONFLITANTE** — bypass institucional |
| **`public_app.py` → painel ADM completo** | **CONFLITANTE** — exposição indevida |

---

## Componentes soberanos

| Componente | Papel |
|------------|-------|
| `LEI15_CORE_002` | Única interpretação vigente da Lei 15 como Núcleo |
| `STRUCT_LEI15_CORE_CANDIDATE_002_15D_001` | Label operacional rastreável |
| `generate_best_games(batch_label=...)` com label soberano + flags | Caminho canônico de geração futura |
| `POLITICA_AVALIACAO_NUCLEO_LEI15_6_BASES.md` | Critério de avaliação do Núcleo |
| `LEI_001_FONTE_UNICA_DA_VERDADE.md` | Verdade operacional em PostgreSQL |
| `POLITICA_ML_ASSISTIVO.md` | ML subordinado, não soberano |

---

## Componentes congelados

| Componente | Uso permitido |
|------------|---------------|
| `STRUCT_TEST_15D_001` e `FROZEN_LEGACY_LABELS` | Leitura comparativa; **zero** novo volume extenso |
| `LEI_15_NUCLEO_OPERACIONAL_15D.md` | Evidência histórica de auditoria GP50/GP30 — **não** doc-fonte soberano |
| GE 114 (CAND-A), GE 115 (CAND-D) | Evidência CDX EPOCH_001 |
| Runs V1, V2–V4, CAND-001 em PostgreSQL | Evidência histórica read-only |
| Relatórios `reports/lei15_*_2026_06_17.*` | Preservação institucional |

---

## Componentes suspensos

| Componente | Motivo |
|------------|--------|
| Lei 15A operacional (expansão 16D–23D mecânica) | Incompatível com matriz CORE_002 até redefinição |
| `lei15a_operational.py` como motor de expansão | Suspenso — sync/tagging legado |
| Geração via Painel ADM (`clean_law15`, `_generate_direct_15_games`) | Suspenso até missão visual/plataforma |
| Promoção `active` público | Bloqueado |
| Piloto / teste resultado CORE_002 | Bloqueado até pré-requisitos da seção 16 |

---

## Componentes conflitantes (correção em missões posteriores)

| Componente | Agente responsável |
|------------|-------------------|
| `_generate_direct_15_games` no Painel | `agent_visual` + `agent_plataforma` |
| `batch_label=None` default em API/admin | `agent_geracao` + `agent_plataforma` |
| Purge sem guarda por label | `agent_dados` |
| `LEI_15_NUCLEO_OPERACIONAL_15D.md` como referência operacional | `agent_governanca` (banner de reclassificação) |
| Lei 15A mecânica em código/painel | `agent_governanca` + `agent_ml` (redefinição ou aposentadoria) |
| V1 `active` global | `agent_geracao` |
| `public_app` = ADM completo | `agent_plataforma` |

---

## Impacto sobre a Lei 15A

1. A Lei 15A no formato **expansão mecânica 15+1/15+2** com reservas fixas `(15, 05, 07, 14, 19)` sobre núcleo 15D congelado **deixa de ser interpretação válida** da relação Lei 15 ↔ Lei 15A.

2. **Permanece suspenso** até ADR dedicada pós-transição (`lei15_core_002_sovereign.lei15a_operational_gate()` → `open_15a: False`).

3. **Lei 15A futura** (quando autorizada) deverá:
   - consumir cartões gerados pelo **CORE_002**;
   - atuar como **camada adaptativa complementar** (registro, conferência, entrega);
   - **nunca** reintroduzir expansão mecânica do antigo núcleo fixo 15D como soberania paralela.

4. Documentos afetados (reclassificar, não apagar nesta ADR):
   - `docs/governance/LEI_15_NUCLEO_OPERACIONAL_15D.md`
   - `docs/governance/ADR_LEI15A_CARTAO_REGISTRO_APOSTA.md`

---

## Impacto sobre o Painel ADM

1. **Esta ADR autoriza** — mas **não executa** — a atualização do Painel ADM.

2. **Antes** da missão de painel, o ADM permanece **constitucionalmente desalinhado** (auditoria R1, R8).

3. **Após** missão `agent_visual` + `agent_plataforma`, o Painel deverá:
   - rotear geração Lei 15 **exclusivamente** via path CORE_002;
   - remover `_generate_direct_15_games` como caminho Lei 15;
   - exibir copy: **“Lei 15 = matriz soberana de papéis 01–25”**;
   - corrigir defecto `analysis_batch_label` indefinido;
   - aplicar gate de confirmação em delete/purge;
   - separar entrada pública de superfície ADM destrutiva.

---

## Impacto sobre históricos e purge

1. Evidência institucional em PostgreSQL **não é descartável** por purge genérico.

2. **Preservação obrigatória** (mínimo):
   - GE **114**, GE **115**;
   - baseline EPOCH_001 (`STRUCT_TEST_15D_001` e correlatos);
   - runs **V1** (`STRUCT_REALIGN_V1_15D_001`);
   - labels CDX, realign V2–V4, CAND-001;
   - `imported_contests`, `lotofacil_official_history`;
   - memória científica/institucional.

3. **Limpeza operacional** futura exige sequência institucional:

```text
backup → congelamento → classificação por label → autorização agent_dados + agent_governanca → relatório de preservação → execução
```

4. `delete_history` atual (Painel) classificado como **CONFLITANTE COM LEI 001** até implementação de guarda por label.

---

## Impacto sobre geração futura

Geração Lei 15 soberana **permanece bloqueada** (`LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0`).

**Pré-requisitos cumulativos** antes de qualquer novo teste ou geração operacional:

| # | Pré-requisito | Missão |
|---|---------------|--------|
| 1 | ADR-047 registrada | **Esta ADR** ✓ |
| 2 | Painel ADM corrigido | `agent_visual` + `agent_plataforma` |
| 3 | Path CORE_002 roteado no ADM | `agent_geracao` + `agent_visual` |
| 4 | Purge protegido por label | `agent_dados` |
| 5 | Legacy default bloqueado | `agent_geracao` + `agent_plataforma` |
| 6 | Lei 15A antiga suspensa/arquivada | `agent_governanca` + `agent_ml` |
| 7 | Geração habilitada explicitamente | Ordem institucional + `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=1` |

**Caminho canônico aprovado:**

```python
generate_best_games(
    count=...,
    pool_size=...,
    batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
    ml_enabled=False,  # salvo ordem explícita
)
```

Equivalentes institucionais exigem **ADR ou ordem `agent_governanca`**.

---

## Restrições

Esta ADR **não autoriza**:

- implementação de código;
- geração de jogos;
- testes de resultado;
- alteração de Painel ADM, API, ML ou schema;
- purge ou limpeza de banco;
- abertura operacional de Lei 15A;
- promoção `active`;
- alteração de produção.

**Lei de Missões e Tarefas:** correções posteriores **devem** ser roteadas por agente único por missão, sem mistura de banco + geração + painel + governança na mesma ordem operacional.

---

## Consequências positivas

1. **Clareza constitucional:** um único paradigma Lei 15 (matriz CORE_002).
2. **Fronteira explícita** entre soberano, evidência histórica e legado congelado.
3. **Sequência de correção** auditável por agente.
4. **Proteção de evidência** EPOCH_001 formalizada antes de limpeza.
5. **Painel ADM** desbloqueado para missão de atualização **após** este registro.
6. **Lei 15A** impedida de reintroduzir expansão mecânica sem ADR nova.

---

## Riscos remanescentes

| Risco | Mitigação (missão posterior) |
|-------|------------------------------|
| Runtime ainda conflitante até implementação | Missões agent_geracao, visual, plataforma, dados |
| Doc antigo citado por engano | Banner de reclassificação em `LEI_15_NUCLEO_OPERACIONAL_15D.md` |
| Ops scripts com env shadow_test persistente | Tier ops + checklist ADM |
| Corpus ADR dual (`ADRs/` + `docs/adr/`) | Consolidação referencial futura |
| API pública com `ml_enabled` opcional | Gate plataforma |

---

## Próximas missões recomendadas por agente

| Ordem | Agente | Missão |
|------:|--------|--------|
| 1 | **agent_dados** | Proteger histórico; backup; bloquear purge destrutivo por label |
| 2 | **agent_geracao** | Bloquear legacy default; garantir path único CORE_002; wire `assert_no_new_legacy_extensive_lot` |
| 3 | **agent_visual** + **agent_plataforma** | Atualizar Painel ADM; remover bypass; copy matriz; gate delete; separar public/ADM |
| 4 | **agent_governanca** + **agent_ml** | Redefinir ou aposentar Lei 15A antiga; ADR Lei 15A adaptativa (se aplicável) |
| 5 | **agent_qualidade** | Reescrever testes obsoletos; regressão CORE_002 + painel |
| 6 | **agent_estatistico** | Recalibrar métricas legadas vs 6 bases |

**Nenhuma** destas missões é autorizada ou executada por ADR-047.

---

## Referências normativas

| Documento | Papel |
|-----------|-------|
| `docs/governance/LEI_001_FONTE_UNICA_DA_VERDADE.md` | Lei 001 |
| `docs/governance/POLITICA_AVALIACAO_NUCLEO_LEI15_6_BASES.md` | 6 bases |
| `docs/governance/POLITICA_ML_ASSISTIVO.md` | ML assistivo |
| `docs/adr/ADR-046-NUCLEO-LEI15-CANDIDATE-002.md` | Implantação CORE_002 |
| `docs/governance/AUDITORIA_CONSTITUCIONAL_LOTOIA_2026_06_17.md` | Auditoria origem |
| `reports/auditoria_constitucional_lotoia_2026_06_17.json` | Export auditoria |
| `docs/governance/RELATORIO_LEI15_CORE_002_IMPLANTACAO_2026_06_17.md` | Implantação técnica |
| `AGENTS.md` / `.cursor/rules/agent_*.mdc` | Lei de Missões e roteamento |

---

## Histórico

| Data | Agente | Nota |
|------|--------|------|
| 2026-06-17 | agent_governanca | ADR-047 — Transição Constitucional Lei 15 / CORE_002 registrada |

---

## Veredicto final

# **TRANSIÇÃO CONSTITUCIONAL REGISTRADA**

A Constituição nova da Lei 15 — **matriz soberana de papéis 01–25 governada pelo LEI15_CORE_002** — está **oficialmente registrada**. O conflito entre paradigma antigo (núcleo fixo 15D) e paradigma novo permanece **no runtime até missões posteriores**, mas a **ordem institucional de transição** está definida e vinculante para todos os agentes.

**Próximo passo institucional:** missão `agent_dados` — proteção de histórico e purge.
