# ADR — Lei 15A Núcleo Operacional 15D Congelado

## Status

**Accepted**

Registro: `NUCLEO_LEI15A_15D_CONGELADO_REGISTRADO`

---

## Contexto

A plataforma LotoIA concluiu auditoria read-only progressiva sobre baterias oficiais 15D nas
escalas GP50, GP30, GP20 e GP10 (5 baterias × N jogos), comparando desempenho contra histórico
oficial (janelas 100 / 300 / 500 concursos).

Objetivo da série: identificar **núcleo operacional 15D** para a Lei 15A — leitura operacional
da matriz GP — sem alterar geração, Lei 15 ou expansão dimensional.

Principais achados:

- Convergência alta (14–15/15) entre escalas na faixa avg_hits ~9,06 @300.
- Blind spots estruturais persistentes: **06, 16, 17, 21** (zero aparições em 550 jogos).
- Oscilação **12 ↔ 15** entre GP30 e GP20/GP10; decisão final mantém **12 no núcleo** e **15
  como reserva prioritária**.
- Dezena **04** permanece no núcleo como âncora GP50/GP20 apesar de rebaixamento na frequência
  GP10 isolada.

---

## Decisão

Congelar institucionalmente o seguinte **Núcleo Lei 15A 15D**:

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

Documento normativo associado: `docs/governance/LEI_15A_NUCLEO_OPERACIONAL_15D.md`.

---

## Limites explícitos

Esta ADR é **registro institucional**, não change request de runtime:

1. **Lei 15** permanece soberana na geração.
2. **Lei 15A** recebe referência documental; UI existente não é alterada por esta ADR.
3. **Expansão 16D–23D** permanece bloqueada até missão e ADR específicos.
4. **Produção Railway** (`rescue-institutional-panel`) não é alvo de deploy desta decisão.
5. Nenhum campo de banco, schema ou gateway é criado ou modificado.

---

## Consequências

### Positivas

- Referência única auditável para núcleo operacional GP 15D.
- Rastreabilidade GP50 → GP30 → GP20 → GP10 documentada.
- Fronteira clara entre núcleo congelado, reservas e blind spots.
- Base para futura conferência Lei 15A sem ambiguidade de dezenas.

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
| Documento governança | `LEI_15A_NUCLEO_OPERACIONAL_15D.md` |
| ADR de congelamento | Este documento |
| Alteração de geração | **Não** |
| Alteração Lei 15 | **Não** |
| Deploy produção | **Não** |

---

## Referências

- `docs/governance/LEI_15A_NUCLEO_OPERACIONAL_15D.md`
- `docs/governance/POLITICA_ML_ASSISTIVO.md`
- `AGENTS.md` — posicionamento LotoIA (plataforma estatística estrutural)
- ADR-032 — Operational Scientific Audit Baseline
- ADR-042 — Política de ML Assistivo

---

## Histórico

| Data | Autor / agente | Nota |
|------|----------------|------|
| 2026-06-09 | Cloud agent | Congelamento pós-auditoria GP50–GP10 |
