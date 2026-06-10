# ADR — Lei 15 Núcleo Operacional 15D Congelado

## Status

**Accepted**

Registro: `NUCLEO_LEI15_15D_CONGELADO_REGISTRADO`

---

## Contexto

A plataforma LotoIA concluiu auditoria read-only progressiva sobre baterias oficiais 15D nas
escalas GP50, GP30, GP20 e GP10 (5 baterias × N jogos), comparando desempenho contra histórico
oficial (janelas 100 / 300 / 500 concursos).

Objetivo da série: identificar **núcleo operacional 15D** para a **Lei 15** — documento-fonte
soberano da geração — sem alterar runtime Lei 15A nem expansão dimensional.

Principais achados:

- Convergência alta (14–15/15) entre escalas na faixa avg_hits ~9,06 @300.
- Blind spots estruturais persistentes: **06, 16, 17, 21** (zero aparições em 550 jogos).
- Oscilação **12 ↔ 15** entre GP30 e GP20/GP10; decisão final mantém **12 no núcleo** e **15
  como reserva prioritária**.
- Dezena **04** permanece no núcleo como âncora GP50/GP20 apesar de rebaixamento na frequência
  GP10 isolada.

---

## Decisão

Congelar institucionalmente o seguinte **Núcleo Lei 15 15D**:

```
01 02 03 04 09 10 11 12 13 18 20 22 23 24 25
```

Com camadas operacionais:

| Camada | Dezenas |
|--------|---------|
| Reservas prioritárias | 15 · 05 · 07 · 14 · 19 |
| Vigilância | 04 · 11 · 12 · 15 |
| Blind spots | 06 · 16 · 17 · 21 |
| Marginal | 08 |

Documento-fonte associado: `docs/governance/LEI_15_NUCLEO_OPERACIONAL_15D.md`.

A Lei 15A **consome** este núcleo na montagem do cartão de registro da aposta — ver
`docs/governance/ADR_LEI15A_CARTAO_REGISTRO_APOSTA.md`.

---

## Limites explícitos

Esta ADR é **registro institucional Lei 15**, não change request de runtime Lei 15A:

1. **Lei 15** permanece soberana na geração.
2. **Lei 15A** usa o núcleo apenas como insumo normativo de registro — sem reclassificar soberania.
3. **Conferência** usa `cartao_final` por jogo — não o núcleo congelado como atalho repetido.
4. **Expansão 16D–23D** permanece bloqueada até missão e ADR específicos.
5. Nenhum campo de banco, schema ou gateway é criado ou modificado por esta ADR.

---

## Consequências

### Positivas

- Referência única auditável para núcleo operacional GP 15D sob **Lei 15**.
- Rastreabilidade GP50 → GP30 → GP20 → GP10 documentada.
- Fronteira clara entre núcleo Lei 15, reservas e blind spots.
- Base normativa para montagem Lei 15A sem confundir papéis.

### Trade-offs

- Núcleo pode divergir pontualmente do top-15 por frequência de uma bateria GP10 isolada
  (caso 04 vs 15).
- Blind spots exigem reservas para qualquer expansão dimensional futura.
- Registro não substitui validação prospectiva em bateria limpa futura.

---

## Conformidade

| Requisito | Atendido |
|-----------|----------|
| Auditoria GP50/GP30/GP20/GP10 | Sim |
| Documento governança Lei 15 | `LEI_15_NUCLEO_OPERACIONAL_15D.md` |
| ADR de congelamento | Este documento |
| Alteração de geração | **Não** |
| Alteração Lei 15A (conceito) | **Não** — apenas referência cruzada |
| Deploy produção | **Não** |

---

## Referências

- `docs/governance/LEI_15_NUCLEO_OPERACIONAL_15D.md`
- `docs/governance/ADR_LEI15A_CARTAO_REGISTRO_APOSTA.md`
- `docs/governance/POLITICA_ML_ASSISTIVO.md`
- `AGENTS.md` — posicionamento LotoIA (plataforma estatística estrutural)
- ADR-032 — Operational Scientific Audit Baseline
- ADR-042 — Política de ML Assistivo

---

## Histórico

| Data | Autor / agente | Nota |
|------|----------------|------|
| 2026-06-09 | Cloud agent | Congelamento pós-auditoria GP50–GP10 |
| 2026-06-10 | Cloud agent | Reclassificado como ADR **Lei 15** (núcleo soberano) |
