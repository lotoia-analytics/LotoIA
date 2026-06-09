# Lei 15A — Núcleo Operacional 15D (Congelado)

## Status

`NUCLEO_LEI15A_15D_CONGELADO_REGISTRADO`  
`POLITICA_CARTAO_REGISTRO_LEI15A_REGISTRADA`  
`RUNTIME_LEI15A_APLICADO_ATE_20D`

Registro institucional de referência operacional para a Lei 15A.  
**Não altera geração, Lei 15, expansão 16D–23D, banco, gateway, guardrails ou runtime de produção.**

---

## Escopo

Este documento formaliza o **núcleo operacional 15D congelado** da Lei 15A, derivado de
auditoria read-only sobre baterias GP50, GP30, GP20 e GP10 (15 dezenas por jogo), contra
histórico oficial validado (janelas 100 / 300 / 500 concursos).

A Lei 15A utiliza este núcleo como **referência de leitura operacional** — não como comando
automático de geração nem substituto da soberania da Lei 15.

---

## Política de cartão de registro da aposta

> **Decisão institucional:** o cartão usado para **registro da aposta** é o cartão final
> montado pela **Lei 15A**, e **não** a reclassificação visual do cartão final da Lei 15.

| Norma | Papel | Função |
|-------|-------|--------|
| **Lei 15** | Governança soberana | Gerar base / contexto |
| **Lei 15A** | Operação GP — registro da aposta | Montar cartão final operacional |

```yaml
cartao_registro_aposta:
  origem: Lei_15A
  regra: nucleo_operacional_GP_congelado + reservas_auditadas_Lei15A
  nao_origem: cartao_final_reclassificado_da_Lei15
```

### Montagem do cartão de registro por formato

| Formato | Cartão de registro Lei 15A |
|---------|----------------------------|
| **15D** | Núcleo congelado (`nucleo_lei15A_15D`) |
| **16D** | Núcleo + 1 reserva Lei 15A |
| **17D** | Núcleo + 2 reservas Lei 15A |
| **18D** | Núcleo + 3 reservas Lei 15A |
| **19D** | Núcleo + 4 reservas Lei 15A |
| **20D** | Núcleo + 5 reservas Lei 15A (`15 05 07 14 19`) |
| **21D** | **Pendente Lei 15A** — observacional; runtime bloqueado |
| **22D** | **Observacional** — não é cartão de registro de aposta |
| **23D** | **Observacional** — não é cartão de registro de aposta |

### Runtime aplicado (faixa inferior do painel)

Função: `build_lei15A_registration_card(format_size)` em `dashboard/institutional_app.py`.

| Formato | Cartão inferior (registro Lei 15A) | Auditadas | Vigilantes |
|---------|--------------------------------------|-----------|------------|
| **15D** | Núcleo congelado | `-` | `-` |
| **16D** | Núcleo + `[15]` | `15` | `15` |
| **17D** | Núcleo + `[15, 05]` | `15 05` | `15 05` |
| **18D** | Núcleo + `[15, 05, 07]` | `15 05 07` | `15 05 07` |
| **19D** | Núcleo + `[15, 05, 07, 14]` | `15 05 07 14` | `15 05 07 14` |
| **20D** | Núcleo + `[15, 05, 07, 14, 19]` | `15 05 07 14 19` | `15 05 07 14 19` |
| **21D–23D** | `-` (pendente Lei 15A) | `-` | `-` |

A faixa superior permanece na geração Lei 15 (`Jogos gerados`).

Reservas Lei 15A para expansão 16D–21D seguem a ordem prioritária registrada neste
documento (`15 · 05 · 07 · 14 · 19`).

### O que não equivale a cartão de registro

- Rotular `núcleo_lei_15` e `reservas_auditadas` sobre o cartão final da **geração Lei 15**
  é **reclassificação visual**, não cartão de aposta.
- Espelhar `core_numbers` da geração na faixa operacional inferior **não** satisfaz esta
  política — o registro exige montagem Lei 15A com núcleo congelado e reservas próprias.

ADR normativa: `docs/governance/ADR_LEI15A_CARTAO_REGISTRO_APOSTA.md`.

---

## Núcleo congelado Lei 15A (15D)

```
01 02 03 04 09 10 11 12 13 18 20 22 23 24 25
```

| Posição | Dezena | Papel |
|--------:|--------|-------|
| 1–15 | 01 02 03 04 09 10 11 12 13 18 20 22 23 24 25 | Núcleo operacional GP congelado |

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
exige troca controlada via reservas — **fora do escopo deste registro**.

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

- Não altera a Lei 15 nem seus parâmetros de geração.
- Não recalibra motor, rerank ou expansão 16D–23D.
- Não modifica schema, gateway, guardrails ou Railway.
- Não promove ML assistivo a decisor do núcleo.
- Não autoriza deploy ou mudança de runtime do dashboard.

---

## Observação operacional

> Núcleo congelado para Lei 15A como referência operacional 15D.  
> Ainda **não** promover expansão 16D–23D sem missão específica e ADR dedicado.

---

## Referências

- ADR núcleo congelado: `docs/governance/ADR_LEI15A_NUCLEO_15D_CONGELADO.md`
- ADR cartão de registro: `docs/governance/ADR_LEI15A_CARTAO_REGISTRO_APOSTA.md`
- Política ML assistivo: `docs/governance/POLITICA_ML_ASSISTIVO.md`
- Governança operacional: `docs/governance/GOVERNANCA_OPERACIONAL_LOTOIA.md`

---

## Histórico do documento

| Data | Evento |
|------|--------|
| 2026-06-09 | Registro institucional do núcleo congelado pós-auditoria GP50→GP10 |
| 2026-06-09 | Política de cartão de registro da aposta Lei 15A registrada (ADR dedicado) |
| 2026-06-09 | Runtime Lei 15A aplicado na faixa inferior até 20D (`build_lei15A_registration_card`) |
