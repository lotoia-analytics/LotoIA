# Lei 15 — Núcleo Operacional 15D (Congelado)

## Status

`NUCLEO_LEI15_15D_CONGELADO_REGISTRADO`

Documento-fonte **soberano** da Lei 15.  
**Não altera runtime Lei 15A, expansão 16D–23D, banco, gateway, guardrails ou deploy de produção por si só.**

---

## Escopo

Este documento formaliza o **núcleo operacional 15D congelado** da **Lei 15**, derivado de
auditoria read-only sobre baterias GP50, GP30, GP20 e GP10 (15 dezenas por jogo), contra
histórico oficial validado (janelas 100 / 300 / 500 concursos).

O núcleo pertence à **geração soberana Lei 15**. A **Lei 15A** pode **consumir** este núcleo
na montagem do cartão de registro da aposta — sem substituir a soberania da geração Lei 15.

---

## Fronteira Lei 15 / Lei 15A

| Norma | Papel | Função |
|-------|-------|--------|
| **Lei 15** | Documento-fonte soberano | Gerar base / contexto / núcleo operacional 15D |
| **Lei 15A** | Documento-fonte normativo | Montar cartão de registro da aposta |

Política de cartão de registro (Lei 15A): `docs/governance/ADR_LEI15A_CARTAO_REGISTRO_APOSTA.md`.

```yaml
nucleo_operacional_15D:
  origem: Lei_15
  documento: LEI_15_NUCLEO_OPERACIONAL_15D
  uso_lei15a: insumo_para_cartao_registro  # não reclassifica soberania da geração
```

---

## Núcleo congelado Lei 15 (15D)

```
01 02 03 04 09 10 11 12 13 18 20 22 23 24 25
```

| Posição | Dezena | Papel |
|--------:|--------|-------|
| 1–15 | 01 02 03 04 09 10 11 12 13 18 20 22 23 24 25 | Núcleo operacional GP congelado (Lei 15) |

---

## Reservas prioritárias

Ordem de prioridade operacional (substituição / expansão observacional — **não automática**):

```
15  05  07  14  19
```

| Dezena | Nota |
|--------|------|
| **15** | Reserva prioritária — sinal forte em GP30/GP10; oscila entre escalas |
| 05 | Reserva estrutural recorrente |
| 07 | Reserva com estabilidade parcial em GP30 |
| 14 | Reserva de cobertura moderada |
| 19 | Reserva instável; contribuição 12+/13+ moderada |

---

## Vigilância

Dezenas do núcleo ou adjacentes que exigem monitoramento em baterias futuras:

```
04  11  12  15
```

| Dezena | Motivo |
|--------|--------|
| **04** | Âncora GP50/GP20 (estab. 5/5); rebaixada no top-15 por frequência GP10 |
| **11** | Núcleo congelado; estabilidade GP10 parcial (2/5 no top-15 intra-bateria) |
| **12** | Confirmada no núcleo; oscilou GP30 (reserva) → GP20/GP10 (retorno) |
| **15** | Reserva prioritária; entrou no top-15 GP10/GP30 |

---

## Blind spots confirmados

Ausência estrutural persistente em GP50, GP30, GP20 e GP10 (400+ jogos auditados):

```
06  16  17  21
```

Nenhuma destas dezenas apareceu nas baterias validadas. Expansão 16D–23D que dependa delas
exige troca controlada via reservas — matriz normativa em
`docs/governance/ADR_EXPANSAO_DIMENSIONAL_16D_23D.md`.

---

## Marginal

| Dezena | GP50 | GP30 | GP20 | GP10 | Decisão |
|--------|------|------|------|------|---------|
| **08** | 69/250 | 47/150 | 37/100 | 12/50 | Sub-representada decrescente — **não promover** |

---

## Evidências de validação

| Campo | Valor |
|-------|-------|
| GPS validados | GP50 · GP30 · GP20 · GP10 |
| Formato | 15D (15 dezenas por jogo) |
| Baterias | 5 por escala |
| Jogos auditados | 250 + 150 + 100 + 50 = **550** |
| Histórico | `data/raw/historico_lotofacil.csv` (oficial / espelho validado) |
| Janela principal | 300 concursos |
| Janelas controle | 100 · 500 concursos |
| Status | `congelado_candidato_institucional` → **`congelado_registrado`** |

### Resumo por escala (agregado @300)

| GP | Jogos | avg_hits | best_hit | hit_13 (agregado) |
|----|-------|----------|----------|-------------------|
| GP50 | 250 | 9,0612 | 14 | 153 |
| GP30 | 150 | 9,0593 | 14 | 107 |
| GP20 | 100 | 9,0579 | 14 | 59 |
| GP10 | 50 | 9,0669 | 14 | 38 |

### Trajetória 12 ↔ 15

| Escala | Dezena 12 | Dezena 15 |
|--------|-----------|-----------|
| GP50 | núcleo | reserva |
| GP30 | rebaixada (reserva) | promovida (top-15) |
| GP20 | retorno ao núcleo | rebaixada (reserva) |
| GP10 (freq.) | top-15 | top-15 (reserva prioritária) |
| **Decisão final** | **no núcleo** | **reserva prioritária** |

---

## O que este registro **não** faz

- Não substitui a geração soberana Lei 15 por núcleo fixo na Conferência.
- Não recalibra motor, rerank ou expansão combinatória científica (ver ADR-034).
- Não substitui a matriz de expansão dimensional documentada em `ADR_EXPANSAO_DIMENSIONAL_16D_23D.md`.
- Não modifica schema, gateway, guardrails ou Railway.
- Não promove ML assistivo a decisor do núcleo.
- Não autoriza deploy ou mudança de runtime do dashboard por si só.

---

## Observação operacional

> Núcleo congelado **Lei 15** como documento-fonte soberano 15D.  
> A Conferência deve usar `cartao_final` por jogo gerado — não este núcleo como atalho repetido.  
> A Lei 15A consome o núcleo apenas na montagem do cartão de registro (ADR dedicada).

---

## Referências

- ADR núcleo congelado: `docs/governance/ADR_LEI15_NUCLEO_15D_CONGELADO.md`
- ADR expansão dimensional 15D→23D: `docs/governance/ADR_EXPANSAO_DIMENSIONAL_16D_23D.md`
- ADR cartão de registro (Lei 15A): `docs/governance/ADR_LEI15A_CARTAO_REGISTRO_APOSTA.md`
- Política ML assistivo: `docs/governance/POLITICA_ML_ASSISTIVO.md`
- Governança operacional: `docs/governance/GOVERNANCA_OPERACIONAL_LOTOIA.md`

---

## Histórico do documento

| Data | Evento |
|------|--------|
| 2026-06-09 | Registro institucional do núcleo congelado pós-auditoria GP50→GP10 |
| 2026-06-10 | Renomeado e reclassificado como documento-fonte **Lei 15** (não Lei 15A) |
