# ADR — Expansão Dimensional Lei 15 / Lei 15A (15D → 23D)

## Status

**Accepted**

Registro: `ADR_EXPANSAO_DIMENSIONAL_16D_23D_REGISTRADA`  
Missão documental: **DOC-001**

---

## Contexto

Após o congelamento do núcleo operacional 15D da **Lei 15**
(`ADR_LEI15_NUCLEO_15D_CONGELADO`) e a política de cartão de registro da **Lei 15A**
(`ADR_LEI15A_CARTAO_REGISTRO_APOSTA`), a plataforma passou a operar três camadas distintas
que antes estavam documentadas de forma fragmentada:

| Camada | Pergunta institucional |
|--------|------------------------|
| **Geração** | O que a Lei 15 soberana produz? |
| **Registro** | Qual cartão a Lei 15A registra na aposta operacional GP? |
| **Conferência** | Quais dezenas de cada jogo são comparadas ao resultado oficial? |

Sem ADR unificada, surgiram ambiguidades:

1. **Expansão 16D–23D** citada como “bloqueada” no ADR do núcleo 15D, enquanto o runtime já
   conferia formatos expandidos e registrava 16D–20D na faixa Lei 15A.
2. **Conferência 15D** usava o núcleo congelado repetido em todas as linhas (corrigido em
   **AUD-004** / PR #15).
3. Operadores podiam confundir **núcleo Lei 15**, **cartão de registro Lei 15A** e
   **`cartao_final` por jogo** na conferência.

Esta ADR formaliza a **matriz de expansão dimensional** sem alterar a soberania da Lei 15 na
geração nem abrir expansão combinatória não governada.

---

## Decisão

### Princípio central

A expansão dimensional na LotoIA é **normativa e em camadas**, não um único “modo expandido”:

```text
Lei 15 (geração soberana)
  → cartão final por jogo (final_card_numbers / cartao_final)
    → Conferência institucional (15D–23D)     [AUD-004 guarda 15D]
    → Registro Lei 15A (15D–20D operacional) [21D–23D pendente]
```

### Matriz por formato

| Formato | Geração Lei 15 | Registro Lei 15A | Conferência institucional | Classificação |
|---------|----------------|------------------|---------------------------|---------------|
| **15D** | Soberana — núcleo + saída gerada | `nucleo_lei15_15D` | `cartao_final` por jogo + guarda AUD-004 | **Operacional** |
| **16D** | Cartão expandido na geração | núcleo + 1 reserva Lei 15A | `cartao_final` por jogo | **Operacional** |
| **17D** | Cartão expandido na geração | núcleo + 2 reservas Lei 15A | `cartao_final` por jogo | **Operacional** |
| **18D** | Cartão expandido na geração | núcleo + 3 reservas Lei 15A | `cartao_final` por jogo | **Operacional** |
| **19D** | Cartão expandido na geração | núcleo + 4 reservas Lei 15A | `cartao_final` por jogo | **Operacional** |
| **20D** | Cartão expandido na geração | núcleo + `[15, 05, 07, 14, 19]` | `cartao_final` por jogo | **Operacional** |
| **21D** | Permitido na geração quando existir | **Pendente Lei 15A** — registro bloqueado | `cartao_final` por jogo (leitura observacional) | **Parcial** |
| **22D** | Observacional | **Fora do registro** operacional | `cartao_final` por jogo (leitura observacional) | **Observacional** |
| **23D** | Observacional | **Fora do registro** operacional | `cartao_final` por jogo (leitura observacional) | **Observacional** |

### Núcleo e reservas (referência normativa)

**Núcleo congelado Lei 15 (15D):**

```
01 02 03 04 09 10 11 12 13 18 20 22 23 24 25
```

**Reservas prioritárias Lei 15A** (ordem para montagem 16D–20D):

```
15  05  07  14  19
```

Documento-fonte do núcleo: `docs/governance/LEI_15_NUCLEO_OPERACIONAL_15D.md`.

### Regras de Conferência (AUD-004)

Para **15D**, a conferência institucional deve:

1. Usar **`cartao_final` / `final_card_numbers` de cada jogo** — nunca o núcleo congelado
   repetido como atalho.
2. Registrar `origem_dezenas_conferencia = cartao_final`.
3. Passar pela guarda `validate_conference_15d_source()` antes de persistir
   `reconciliation_runs`.
4. Bloquear persistência com `BLOQUEADO_NUCLEO_FIXO_15D` quando jogos gerados forem
   distintos mas a conferência repetir o mesmo cartão ou usar origem proibida
   (`nucleo_lei_15a_congelado`, `nucleo_operacional_gp`, `fallback_15d`, etc.).

Para **16D–23D**, a conferência já seguia `cartao_final` por jogo; esta ADR apenas
**formaliza** o alinhamento com a matriz acima sem alterar o runtime desses formatos.

### Regras de Registro Lei 15A

- **15D–20D:** `build_lei15A_registration_card()` — status `registro_lei15a`, `operational: true`.
- **21D–23D:** status `pendente Lei 15A`, `operational: false` — registro bloqueado na faixa
  inferior do painel até ADR dedicado de promoção.

Constantes runtime: `LEI15A_REGISTRATION_MAX_FORMAT = 20`,
`LEI15A_REGISTRATION_PENDING_FORMATS = (21, 22, 23)`.

### O que permanece bloqueado

| Expansão | Status |
|----------|--------|
| Novo motor gerador dimensional automático (além do runtime atual) | **Bloqueado** — exige ADR + benchmark |
| Registro operacional Lei 15A em 21D–23D | **Bloqueado** |
| Conferência usando núcleo fixo repetido em 15D | **Bloqueado** — AUD-004 |
| Expansão combinatória científica sem lifecycle ADR-034 | **Bloqueado** |
| Promoção de 21D–23D a operacional sem validação prospectiva | **Bloqueado** |
| Substituição da soberania Lei 15 por Lei 15A na geração | **Proibido** |

### Fonte de verdade operacional (Lei 001)

Toda leitura de histórico, conferência persistida e exportação institucional deve obedecer à
**Lei No 001** — PostgreSQL Institucional como fonte única. CSV e `session_state` não disputam
a verdade operacional (ver `LEI_001_FONTE_UNICA_DA_VERDADE.md`, AUD-005, AUD-006).

---

## Consequências

### Positivas

- Matriz única 15D→23D para geração, registro e conferência.
- AUD-004 integrado à governança documental de expansão.
- Fim da contradição “expansão bloqueada” vs runtime 16D–20D já aplicado.
- Base para promover 21D–23D no futuro com critérios explícitos.

### Trade-offs

- Três leituras de cartão podem coexistir na UI (geração Lei 15, registro Lei 15A,
  conferência por jogo) — exige rótulos semânticos claros no painel.
- 21D–23D permanecem observacionais na conferência sem registro operacional Lei 15A.

---

## Conformidade

| Requisito | Atendido |
|-----------|----------|
| ADR de expansão dimensional criada | Este documento |
| Núcleo 15D congelado preservado | Sim — referência Lei 15 |
| Lei 15 soberana na geração | Sim — inalterada |
| Registro Lei 15A 15D–20D documentado | Sim |
| Conferência 15D AUD-004 documentada | Sim |
| 21D–23D observacionais / pendentes | Sim |
| Alteração de código nesta missão DOC-001 | **Não** — apenas documentação |

---

## Implementação runtime (referência)

| Componente | Localização |
|------------|-------------|
| Núcleo 15D congelado | `NUCLEO_LEI15_15D_CONGELADO` em `dashboard/institutional_app.py` |
| Registro Lei 15A | `build_lei15A_registration_card()` |
| Conferência por jogo | `_extract_conference_card_numbers()`, `_compare_games_against_contest()` |
| Guarda 15D | `validate_conference_15d_source()` |

Status runtime registrado: `RUNTIME_LEI15A_APLICADO_ATE_20D` (2026-06-09).

---

## Testes de conformidade

| Auditoria | Arquivo |
|-----------|---------|
| AUD-004 Conferência 15D | `tests/test_conferencia_formatos_expandidos.py` |
| Lei 001 P0 | `tests/test_aud_005_p0_lei_001.py` |
| HAI DB-first | `tests/test_aud_006_db_first_hai.py` |

---

## Referências

- `docs/governance/LEI_15_NUCLEO_OPERACIONAL_15D.md`
- `docs/governance/ADR_LEI15_NUCLEO_15D_CONGELADO.md`
- `docs/governance/ADR_LEI15A_CARTAO_REGISTRO_APOSTA.md`
- `docs/governance/LEI_001_FONTE_UNICA_DA_VERDADE.md`
- `docs/architecture/EXPANSION_POLICY.md`
- `ADRs/ADR-034-EXPANSION-LIFECYCLE-RETENTION-POLICY.md`
- PR #15 — Conferência 15D `cartao_final` por jogo
- PR #18 — AUD-005 Lei 001

---

## Histórico

| Data | Autor / agente | Nota |
|------|----------------|------|
| 2026-06-10 | Cloud agent | DOC-001 — ADR de expansão dimensional 15D→23D formalizada |
