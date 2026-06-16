# Relatorio EPOCH_001 — Resultados Estruturais 15D a 20D

**Gerado em:** 2026-06-16 09:05 UTC
**Fonte:** Railway PostgreSQL
**Operacional:** Apenas leitura. Sem efeito em geracao, Lei 15, pesos ou filtros.

---

## STRUCT_TEST_15D_001  (game_size=15D)

**Status:** INCOMPLETO (incompleto)
**Evidence level:** LOCAL_DIAGNOSTIC

### Resumo quantitativo

| Metrica | Valor | Esperado |
|---|---|---|
| generation_events | 4 | 20 |
| jogos analisados | 1300 | — |
| concursos analisados | 7 ([3705, 3706, 3707, 3708, 3709, 3710, 3711]) | 5 |
| generation_event_ids | [27, 28, 29, 30] | — |
| reconciliation_run_ids | [186, 187, 188, 189, 190, 191, 192, 193, 194, 195]... | — |

### Distribuicao de acertos (reconciliation_runs)

| Melhor acerto (stuck 15) | Stuck 14 | Stuck 13 |
|---|---|---|
| 0 jogos com 15 hits | 0 jogos com 14 hits | 0 jogos com 13 hits |

### Estrutura do cartao

| | Mais gerado | Frequencia |
|---|---|---|
| Prefixo 3 | `01-02-03` | 546 |
| Prefixo 4 | `01-03-04-05` | 311 |
| Sufixo 3 | `22-24-25` | 689 |
| Sufixo 4 | `21-22-24-25` | 558 |

**Ranking prefixo 3:** `01-02-03` (546x) | `01-03-04` (344x) | `01-03-05` (78x)
**Ranking prefixo 4:** `01-03-04-05` (311x) | `01-02-03-05` (278x) | `01-02-03-04` (182x)
**Ranking sufixo 3:** `22-24-25` (689x) | `21-24-25` (388x) | `21-22-25` (198x)
**Ranking sufixo 4:** `21-22-24-25` (558x) | `18-21-24-25` (388x) | `18-21-22-25` (198x)

### Faixas e gaps

**Maior gap observado:** `6`
**Gaps mais comuns:** `[2, 1, 1, 5, 1, 1, 1, 1, 1, 3, 3, 1, 2, 1]`(26x), `[2, 1, 1, 3, 1, 1, 1, 2, 1, 4, 3, 1, 2, 1]`(26x), `[1, 1, 2, 3, 1, 1, 1, 2, 1, 1, 3, 4, 2, 1]`(26x)

### Redundancia GP

| Similaridade media | Sobreposicao maxima | Quase repetidos |
|---|---|---|
| 0.8158 | 15 | 303567 |

**Dezenas mais ausentes no GP:**

| Dezena | Jogos ausente |
|---|---|
| `07` | 1300 |
| `17` | 1300 |
| `19` | 1300 |
| `20` | 1300 |
| `23` | 1294 |
| `16` | 1198 |
| `06` | 702 |
| `12` | 612 |

### Travamento em 13/14/15

| Faixa | Jogos |
|---|---|
| 13 hits | 0 |
| 14 hits | 0 |
| 15 hits | 0 |

#### Jogos travados em 13 hits

**Quantidade:** 0

_Nenhum._

#### Jogos travados em 14 hits

**Quantidade:** 0

_Nenhum._

#### Jogos travados em 15 hits

**Quantidade:** 0

_Nenhum._

### Comparacao LotoIA vs concursos oficiais

**Prefixos oficiais raros na LotoIA:**
- `01-05-06` oficial:2 LotoIA:0
- `01-04-06` oficial:4 LotoIA:0
- `01-03-07` oficial:1 LotoIA:0
- `02-04-05` oficial:1 LotoIA:0
- `02-05-06` oficial:1 LotoIA:0

**Prefixos LotoIA excessivos:**
- `01-04-05` LotoIA:72 oficial:0
- `03-04-05` LotoIA:40 oficial:0
- `01-03-06` LotoIA:27 oficial:0
- `01-02-05` LotoIA:46 oficial:0
- `03-05-06` LotoIA:6 oficial:0

---

## STRUCT_TEST_16D_001  (game_size=16D)

**Status:** INCOMPLETO (incompleto)
**Evidence level:** LOCAL_DIAGNOSTIC

### Resumo quantitativo

| Metrica | Valor | Esperado |
|---|---|---|
| generation_events | 5 | 20 |
| jogos analisados | 1400 | — |
| concursos analisados | 7 ([3705, 3706, 3707, 3708, 3709, 3710, 3711]) | 5 |
| generation_event_ids | [6, 7, 8, 9, 10] | — |
| reconciliation_run_ids | [47, 48, 49, 50, 51, 52, 53, 54, 55, 56]... | — |

### Distribuicao de acertos (reconciliation_runs)

| Melhor acerto (stuck 15) | Stuck 14 | Stuck 13 |
|---|---|---|
| 0 jogos com 15 hits | 2 jogos com 14 hits | 21 jogos com 13 hits |

### Estrutura do cartao

| | Mais gerado | Frequencia |
|---|---|---|
| Prefixo 3 | `01-02-03` | 609 |
| Prefixo 4 | `01-03-04-05` | 385 |
| Sufixo 3 | `22-24-25` | 840 |
| Sufixo 4 | `21-22-24-25` | 672 |

**Ranking prefixo 3:** `01-02-03` (609x) | `01-03-04` (427x) | `01-03-05` (77x)
**Ranking prefixo 4:** `01-03-04-05` (385x) | `01-02-03-04` (287x) | `01-02-03-05` (252x)
**Ranking sufixo 3:** `22-24-25` (840x) | `21-24-25` (350x) | `21-22-25` (140x)
**Ranking sufixo 4:** `21-22-24-25` (672x) | `18-21-24-25` (280x) | `18-22-24-25` (140x)

### Faixas e gaps

**Maior gap observado:** `6`
**Gaps mais comuns:** `[1, 1, 2, 3, 1, 1, 1, 2, 1, 1, 3, 3, 1, 2, 1]`(28x), `[2, 1, 1, 3, 1, 1, 1, 2, 1, 1, 3, 3, 1, 2, 1]`(21x), `[2, 2, 1, 2, 1, 1, 1, 2, 1, 4, 2, 1, 1, 2, 1]`(21x)

### Redundancia GP

| Similaridade media | Sobreposicao maxima | Quase repetidos |
|---|---|---|
| 0.806 | 16 | 643405 |

**Dezenas mais ausentes no GP:**

| Dezena | Jogos ausente |
|---|---|
| `19` | 1344 |
| `23` | 1344 |
| `17` | 1260 |
| `07` | 1218 |
| `20` | 1176 |
| `16` | 1113 |
| `06` | 679 |
| `08` | 609 |

### Travamento em 13/14/15

| Faixa | Jogos |
|---|---|
| 13 hits | 21 |
| 14 hits | 2 |
| 15 hits | 0 |

#### Jogos travados em 13 hits

**Quantidade:** 21

**generation_event_ids:** [6, 7, 8, 9, 10]
**reconciliation_run_ids:** [52, 53, 54, 56, 69, 71, 73, 74, 75, 76, 80, 81]

**Dezenas mais presentes:** `01`(21x), `15`(21x), `18`(21x), `25`(21x), `14`(20x)
**Dezenas mais ausentes:** `19`(21x), `23`(21x), `17`(20x), `07`(19x), `20`(18x)
**Faltantes para 14:** `16`(8x), `06`(6x), `20`(4x), `08`(4x), `17`(4x)
**Prefixo 3 dominante:** `01,03,04` (12x) | `01,02,03` (5x) | `01,04,05` (2x)
**Prefixo 4 dominante:** `01,03,04,05` (6x) | `01,03,04,06` (4x) | `01,03,04,08` (2x)
**Sufixo 3 dominante:** `22,24,25` (14x) | `21,22,25` (4x) | `21,24,25` (2x)
**Sufixo 4 dominante:** `21,22,24,25` (13x) | `18,21,22,25` (4x) | `18,21,24,25` (2x)
**Pares quase-identicos (sobreposicao >= size-2):** 62

**Amostra (ate 10 jogos):**

| ge_id | rr_id | hits | dezenas | faltantes |
|---|---|---|---|---|
| 10 | 81 | 13 | 01 03 06 08 09 10 11 13 14 15 18 20 21 22 24 25 | 04 16 |
| 10 | 81 | 13 | 01 03 05 06 08 10 11 13 14 15 18 20 21 22 24 25 | 04 16 |
| 9 | 80 | 13 | 01 03 04 08 09 10 11 13 14 15 16 18 21 22 24 25 | 06 20 |
| 9 | 80 | 13 | 01 03 04 05 06 08 10 11 13 15 16 18 21 22 24 25 | 14 20 |
| 9 | 80 | 13 | 01 03 04 06 09 10 11 13 14 15 18 20 21 22 24 25 | 08 16 |
| 10 | 76 | 13 | 01 03 04 05 08 09 10 12 13 14 15 16 18 21 22 25 | 06 24 |
| 10 | 76 | 13 | 01 04 05 09 10 11 12 13 14 15 16 18 21 22 24 25 | 06 08 |
| 9 | 75 | 13 | 01 03 04 06 08 09 10 11 12 13 14 15 18 21 22 25 | 16 24 |
| 9 | 75 | 13 | 01 03 04 08 09 10 11 13 14 15 16 18 21 22 24 25 | 06 12 |
| 9 | 75 | 13 | 01 04 05 06 08 09 10 11 12 13 14 15 18 21 22 25 | 16 24 |

#### Jogos travados em 14 hits

**Quantidade:** 2

**generation_event_ids:** [8, 10]
**reconciliation_run_ids:** [54, 56]

**Dezenas mais presentes:** `01`(2x), `02`(2x), `03`(2x), `05`(2x), `06`(2x)
**Dezenas mais ausentes:** `07`(2x), `08`(2x), `10`(2x), `11`(2x), `19`(2x)
**Faltantes para 15:** `04`(1x), `17`(1x)
**Prefixo 3 dominante:** `01,02,03` (2x)
**Prefixo 4 dominante:** `01,02,03,05` (1x) | `01,02,03,04` (1x)
**Sufixo 3 dominante:** `21,24,25` (2x)
**Sufixo 4 dominante:** `18,21,24,25` (2x)
**Pares quase-identicos (sobreposicao >= size-2):** 1

**Amostra (ate 10 jogos):**

| ge_id | rr_id | hits | dezenas | faltantes |
|---|---|---|---|---|
| 10 | 56 | 14 | 01 02 03 05 06 09 12 13 14 15 16 17 18 21 24 25 | 04 |
| 8 | 54 | 14 | 01 02 03 04 05 06 09 12 13 14 15 16 18 21 24 25 | 17 |

#### Jogos travados em 15 hits

**Quantidade:** 0

_Nenhum._

### Dezenas faltantes mais frequentes

**Para 14 hits:** `16`(8x), `06`(6x), `20`(4x), `08`(4x), `17`(4x), `04`(3x), `24`(3x), `10`(2x)
**Para 15 hits:** `04`(1x), `17`(1x)

### Comparacao LotoIA vs concursos oficiais

**Prefixos oficiais raros na LotoIA:**
- `01-05-06` oficial:2 LotoIA:0
- `01-04-06` oficial:4 LotoIA:0
- `01-03-07` oficial:1 LotoIA:0
- `02-04-05` oficial:1 LotoIA:0
- `02-05-06` oficial:1 LotoIA:0

**Prefixos LotoIA excessivos:**
- `03-04-05` LotoIA:28 oficial:0
- `01-03-06` LotoIA:14 oficial:0
- `01-02-05` LotoIA:49 oficial:0
- `01-04-05` LotoIA:35 oficial:0
- `03-05-06` LotoIA:7 oficial:0

---

## STRUCT_TEST_17D_001  (game_size=17D)

**Status:** INCOMPLETO (incompleto)
**Evidence level:** LOCAL_DIAGNOSTIC

### Resumo quantitativo

| Metrica | Valor | Esperado |
|---|---|---|
| generation_events | 4 | 20 |
| jogos analisados | 1450 | — |
| concursos analisados | 7 ([3705, 3706, 3707, 3708, 3709, 3710, 3711]) | 5 |
| generation_event_ids | [11, 12, 13, 14] | — |
| reconciliation_run_ids | [82, 83, 84, 85, 86, 87, 88, 89, 90, 91]... | — |

### Distribuicao de acertos (reconciliation_runs)

| Melhor acerto (stuck 15) | Stuck 14 | Stuck 13 |
|---|---|---|
| 0 jogos com 15 hits | 10 jogos com 14 hits | 92 jogos com 13 hits |

### Estrutura do cartao

| | Mais gerado | Frequencia |
|---|---|---|
| Prefixo 3 | `01-02-03` | 643 |
| Prefixo 4 | `01-02-03-04` | 356 |
| Sufixo 3 | `22-24-25` | 913 |
| Sufixo 4 | `21-22-24-25` | 805 |

**Ranking prefixo 3:** `01-02-03` (643x) | `01-03-04` (366x) | `01-02-04` (88x)
**Ranking prefixo 4:** `01-02-03-04` (356x) | `01-03-04-05` (308x) | `01-02-03-05` (257x)
**Ranking sufixo 3:** `22-24-25` (913x) | `21-24-25` (248x) | `23-24-25` (160x)
**Ranking sufixo 4:** `21-22-24-25` (805x) | `22-23-24-25` (109x) | `20-21-24-25` (103x)

### Faixas e gaps

**Maior gap observado:** `6`
**Gaps mais comuns:** `[2, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 3, 3, 1, 2, 1]`(23x), `[1, 1, 1, 3, 2, 1, 1, 1, 1, 1, 2, 1, 2, 1, 2, 1]`(22x), `[1, 1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 3, 3, 3, 1]`(22x)

### Redundancia GP

| Similaridade media | Sobreposicao maxima | Quase repetidos |
|---|---|---|
| 0.799 | 17 | 889289 |

**Dezenas mais ausentes no GP:**

| Dezena | Jogos ausente |
|---|---|
| `23` | 1254 |
| `17` | 1246 |
| `19` | 1210 |
| `20` | 1052 |
| `07` | 1027 |
| `16` | 971 |
| `02` | 605 |
| `06` | 593 |

### Travamento em 13/14/15

| Faixa | Jogos |
|---|---|
| 13 hits | 92 |
| 14 hits | 10 |
| 15 hits | 0 |

#### Jogos travados em 13 hits

**Quantidade:** 92

**generation_event_ids:** [11, 12, 13, 14]
**reconciliation_run_ids:** [86, 87, 88, 89, 90, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109]...

**Dezenas mais presentes:** `18`(92x), `25`(92x), `14`(91x), `15`(90x), `01`(88x)
**Dezenas mais ausentes:** `23`(90x), `17`(89x), `19`(82x), `07`(75x), `20`(66x)
**Faltantes para 14:** `16`(41x), `08`(17x), `17`(16x), `06`(15x), `04`(14x)
**Prefixo 3 dominante:** `01,03,04` (40x) | `01,02,03` (17x) | `01,04,05` (8x)
**Prefixo 4 dominante:** `01,03,04,05` (31x) | `01,02,03,04` (16x) | `01,03,04,06` (9x)
**Sufixo 3 dominante:** `22,24,25` (67x) | `21,24,25` (12x) | `21,22,25` (10x)
**Sufixo 4 dominante:** `21,22,24,25` (62x) | `18,21,22,25` (7x) | `18,21,24,25` (6x)
**Pares quase-identicos (sobreposicao >= size-2):** 378

**Amostra (ate 10 jogos):**

| ge_id | rr_id | hits | dezenas | faltantes |
|---|---|---|---|---|
| 14 | 110 | 13 | 01 03 04 06 08 09 11 12 13 14 15 16 18 21 22 24 25 | 10 20 |
| 14 | 110 | 13 | 01 03 04 05 06 08 09 10 11 13 14 15 18 21 22 24 25 | 16 20 |
| 14 | 110 | 13 | 01 03 05 06 08 09 10 11 12 14 15 18 20 21 22 24 25 | 04 16 |
| 14 | 110 | 13 | 01 03 04 05 06 09 10 13 14 15 16 18 21 22 23 24 25 | 08 20 |
| 14 | 110 | 13 | 01 03 04 05 06 08 09 10 11 13 14 15 18 21 22 24 25 | 16 20 |
| 14 | 110 | 13 | 01 02 03 04 06 08 09 10 11 13 14 15 18 20 21 24 25 | 16 22 |
| 14 | 110 | 13 | 01 03 04 06 08 09 10 11 12 13 14 15 16 18 21 24 25 | 20 22 |
| 13 | 109 | 13 | 01 04 05 06 08 09 10 11 13 14 15 18 20 21 22 24 25 | 03 16 |
| 13 | 109 | 13 | 01 03 04 05 06 08 09 10 11 13 14 18 20 21 22 24 25 | 15 16 |
| 13 | 109 | 13 | 01 03 06 07 08 09 10 11 13 14 15 18 20 21 22 24 25 | 04 16 |

#### Jogos travados em 14 hits

**Quantidade:** 10

**generation_event_ids:** [11, 12, 14]
**reconciliation_run_ids:** [102, 103, 104, 106, 108]

**Dezenas mais presentes:** `01`(10x), `13`(10x), `14`(10x), `15`(10x), `18`(10x)
**Dezenas mais ausentes:** `17`(10x), `19`(10x), `23`(10x), `02`(8x), `07`(8x)
**Faltantes para 15:** `16`(3x), `22`(2x), `23`(2x), `10`(1x), `24`(1x)
**Prefixo 3 dominante:** `01,03,04` (7x) | `01,02,03` (2x) | `01,04,05` (1x)
**Prefixo 4 dominante:** `01,03,04,06` (5x) | `01,03,04,05` (2x) | `01,04,05,06` (1x)
**Sufixo 3 dominante:** `22,24,25` (7x) | `21,24,25` (2x) | `21,22,25` (1x)
**Sufixo 4 dominante:** `21,22,24,25` (7x) | `18,21,24,25` (2x) | `18,21,22,25` (1x)
**Pares quase-identicos (sobreposicao >= size-2):** 19

**Amostra (ate 10 jogos):**

| ge_id | rr_id | hits | dezenas | faltantes |
|---|---|---|---|---|
| 12 | 108 | 14 | 01 03 04 05 06 08 10 11 13 14 15 18 20 21 22 24 25 | 16 |
| 12 | 108 | 14 | 01 03 04 05 06 08 10 11 13 14 15 18 20 21 22 24 25 | 16 |
| 14 | 106 | 14 | 01 03 04 06 08 09 11 12 13 14 15 16 18 21 22 24 25 | 10 |
| 14 | 106 | 14 | 01 03 04 06 08 09 10 11 12 13 14 15 16 18 21 24 25 | 22 |
| 12 | 104 | 14 | 01 03 04 06 08 09 10 11 12 13 14 15 16 18 21 22 25 | 24 |
| 12 | 104 | 14 | 01 03 04 06 08 09 10 11 12 13 14 15 16 18 21 24 25 | 22 |
| 11 | 103 | 14 | 01 04 05 06 09 10 11 12 13 14 15 16 18 21 22 24 25 | 08 |
| 11 | 103 | 14 | 01 03 04 06 08 09 10 11 12 13 14 15 18 21 22 24 25 | 16 |
| 14 | 102 | 14 | 01 02 03 07 08 09 10 11 13 14 15 18 20 21 22 24 25 | 23 |
| 14 | 102 | 14 | 01 02 03 05 07 08 09 10 13 14 15 18 20 21 22 24 25 | 23 |

#### Jogos travados em 15 hits

**Quantidade:** 0

_Nenhum._

### Dezenas faltantes mais frequentes

**Para 14 hits:** `16`(41x), `08`(17x), `17`(16x), `06`(15x), `04`(14x), `10`(12x), `20`(11x), `22`(11x)
**Para 15 hits:** `16`(3x), `22`(2x), `23`(2x), `10`(1x), `24`(1x), `08`(1x)

### Comparacao LotoIA vs concursos oficiais

**Prefixos oficiais raros na LotoIA:**
- `01-05-06` oficial:2 LotoIA:0
- `01-04-06` oficial:4 LotoIA:0
- `01-03-07` oficial:1 LotoIA:0
- `02-04-05` oficial:1 LotoIA:0
- `02-05-06` oficial:1 LotoIA:0

**Prefixos LotoIA excessivos:**
- `03-04-05` LotoIA:81 oficial:0
- `01-02-05` LotoIA:43 oficial:0
- `03-05-06` LotoIA:8 oficial:0
- `01-04-05` LotoIA:49 oficial:0
- `01-03-06` LotoIA:21 oficial:0

---

## STRUCT_TEST_18D_001  (game_size=18D)

**Status:** INCOMPLETO (incompleto)
**Evidence level:** LOCAL_DIAGNOSTIC

### Resumo quantitativo

| Metrica | Valor | Esperado |
|---|---|---|
| generation_events | 4 | 20 |
| jogos analisados | 1700 | — |
| concursos analisados | 8 ([3704, 3705, 3706, 3707, 3708, 3709, 3710, 3711]) | 5 |
| generation_event_ids | [15, 16, 17, 18] | — |
| reconciliation_run_ids | [111, 112, 113, 114, 115, 116, 117, 118, 119, 120]... | — |

### Distribuicao de acertos (reconciliation_runs)

| Melhor acerto (stuck 15) | Stuck 14 | Stuck 13 |
|---|---|---|
| 1 jogos com 15 hits | 31 jogos com 14 hits | 211 jogos com 13 hits |

### Estrutura do cartao

| | Mais gerado | Frequencia |
|---|---|---|
| Prefixo 3 | `01-02-03` | 871 |
| Prefixo 4 | `01-02-03-04` | 545 |
| Sufixo 3 | `22-24-25` | 1106 |
| Sufixo 4 | `21-22-24-25` | 1002 |

**Ranking prefixo 3:** `01-02-03` (871x) | `01-03-04` (439x) | `01-02-04` (144x)
**Ranking prefixo 4:** `01-02-03-04` (545x) | `01-03-04-05` (380x) | `01-02-03-05` (299x)
**Ranking sufixo 3:** `22-24-25` (1106x) | `23-24-25` (272x) | `21-24-25` (155x)
**Ranking sufixo 4:** `21-22-24-25` (1002x) | `22-23-24-25` (161x) | `19-21-22-25` (126x)

### Faixas e gaps

**Maior gap observado:** `5`
**Gaps mais comuns:** `[2, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 3, 2, 1, 1, 2, 1]`(25x), `[1, 1, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 3, 3, 1, 2, 1]`(25x), `[2, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 4, 2, 1, 1, 2, 1]`(25x)

### Redundancia GP

| Similaridade media | Sobreposicao maxima | Quase repetidos |
|---|---|---|
| 0.8115 | 18 | 1416104 |

**Dezenas mais ausentes no GP:**

| Dezena | Jogos ausente |
|---|---|
| `23` | 1411 |
| `17` | 1361 |
| `19` | 1205 |
| `20` | 1087 |
| `07` | 997 |
| `16` | 993 |
| `06` | 679 |
| `12` | 570 |

### Travamento em 13/14/15

| Faixa | Jogos |
|---|---|
| 13 hits | 211 |
| 14 hits | 31 |
| 15 hits | 1 |

#### Jogos travados em 13 hits

**Quantidade:** 211

**generation_event_ids:** [15, 16, 17, 18]
**reconciliation_run_ids:** [112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126]...

**Dezenas mais presentes:** `18`(211x), `25`(211x), `14`(207x), `01`(203x), `09`(202x)
**Dezenas mais ausentes:** `17`(200x), `23`(198x), `19`(147x), `07`(128x), `20`(123x)
**Faltantes para 14:** `16`(57x), `23`(49x), `17`(43x), `20`(36x), `06`(35x)
**Prefixo 3 dominante:** `01,02,03` (99x) | `01,03,04` (70x) | `01,02,04` (14x)
**Prefixo 4 dominante:** `01,02,03,04` (66x) | `01,03,04,05` (54x) | `01,02,03,05` (30x)
**Sufixo 3 dominante:** `22,24,25` (150x) | `21,24,25` (25x) | `21,22,25` (20x)
**Sufixo 4 dominante:** `21,22,24,25` (135x) | `19,21,24,25` (19x) | `19,21,22,25` (16x)
**Pares quase-identicos (sobreposicao >= size-2):** 702

**Amostra (ate 10 jogos):**

| ge_id | rr_id | hits | dezenas | faltantes |
|---|---|---|---|---|
| 18 | 144 | 13 | 01 03 04 06 08 09 10 11 12 13 14 15 16 18 19 21 22 25 | 20 23 |
| 18 | 144 | 13 | 01 02 03 04 05 09 10 11 12 13 14 15 18 19 21 22 24 25 | 20 23 |
| 18 | 144 | 13 | 01 03 04 05 06 08 09 10 11 12 13 14 15 16 18 19 22 25 | 20 23 |
| 17 | 143 | 13 | 01 03 04 05 06 09 10 11 12 13 14 15 16 18 19 21 22 25 | 20 23 |
| 17 | 143 | 13 | 01 03 04 06 08 09 10 11 12 13 14 15 16 18 19 21 22 25 | 20 23 |
| 17 | 143 | 13 | 01 02 03 04 09 10 11 12 13 14 15 17 18 19 21 22 24 25 | 20 23 |
| 17 | 143 | 13 | 01 03 04 05 07 09 10 11 12 13 14 15 18 20 21 22 24 25 | 19 23 |
| 16 | 142 | 13 | 01 03 04 05 07 08 09 10 11 12 13 14 15 18 20 22 24 25 | 19 23 |
| 16 | 142 | 13 | 01 02 03 04 07 09 10 11 12 13 14 15 18 20 21 22 24 25 | 19 23 |
| 16 | 142 | 13 | 01 03 04 05 06 09 10 11 12 13 14 15 18 21 22 23 24 25 | 19 20 |

#### Jogos travados em 14 hits

**Quantidade:** 31

**generation_event_ids:** [15, 16, 17, 18]
**reconciliation_run_ids:** [119, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140]

**Dezenas mais presentes:** `01`(31x), `14`(31x), `18`(31x), `21`(31x), `22`(31x)
**Dezenas mais ausentes:** `23`(31x), `17`(30x), `19`(27x), `02`(18x), `07`(17x)
**Faltantes para 15:** `16`(8x), `23`(6x), `06`(5x), `10`(3x), `08`(3x)
**Prefixo 3 dominante:** `01,03,04` (17x) | `01,02,03` (11x) | `01,02,04` (2x)
**Prefixo 4 dominante:** `01,03,04,05` (11x) | `01,03,04,06` (5x) | `01,02,03,04` (5x)
**Sufixo 3 dominante:** `22,24,25` (28x) | `21,22,25` (3x)
**Sufixo 4 dominante:** `21,22,24,25` (28x) | `19,21,22,25` (3x)
**Pares quase-identicos (sobreposicao >= size-2):** 133

**Amostra (ate 10 jogos):**

| ge_id | rr_id | hits | dezenas | faltantes |
|---|---|---|---|---|
| 18 | 140 | 14 | 01 03 04 06 07 08 09 10 11 13 14 15 18 20 21 22 24 25 | 16 |
| 17 | 139 | 14 | 01 03 04 06 07 08 09 10 11 13 14 15 18 20 21 22 24 25 | 16 |
| 17 | 139 | 14 | 01 03 04 05 06 07 08 10 11 13 14 15 18 20 21 22 24 25 | 16 |
| 17 | 139 | 14 | 01 02 03 05 06 08 09 10 13 14 15 16 18 20 21 22 24 25 | 04 |
| 16 | 138 | 14 | 01 03 04 05 06 08 09 10 11 13 14 15 18 20 21 22 24 25 | 16 |
| 15 | 137 | 14 | 01 02 03 04 06 08 09 10 11 13 14 15 18 20 21 22 24 25 | 16 |
| 15 | 137 | 14 | 01 03 04 06 07 08 09 10 11 13 14 15 18 20 21 22 24 25 | 16 |
| 15 | 137 | 14 | 01 03 04 05 06 07 08 10 11 13 14 15 18 20 21 22 24 25 | 16 |
| 15 | 137 | 14 | 01 03 04 05 06 08 09 10 11 12 14 15 16 18 21 22 24 25 | 20 |
| 18 | 136 | 14 | 01 03 04 06 08 09 10 11 12 13 14 15 16 18 19 21 22 25 | 24 |

#### Jogos travados em 15 hits

**Quantidade:** 1

**generation_event_ids:** [15]
**reconciliation_run_ids:** [133]

**Dezenas mais presentes:** `01`(1x), `03`(1x), `04`(1x), `05`(1x), `06`(1x)
**Dezenas mais ausentes:** `02`(1x), `07`(1x), `13`(1x), `17`(1x), `19`(1x)
**Faltantes (jackpot atingido):** —
**Prefixo 3 dominante:** `01,03,04` (1x)
**Prefixo 4 dominante:** `01,03,04,05` (1x)
**Sufixo 3 dominante:** `22,24,25` (1x)
**Sufixo 4 dominante:** `21,22,24,25` (1x)
**Pares quase-identicos (sobreposicao >= size-2):** 0

**Amostra (ate 10 jogos):**

| ge_id | rr_id | hits | dezenas | faltantes |
|---|---|---|---|---|
| 15 | 133 | 15 | 01 03 04 05 06 08 09 10 11 12 14 15 16 18 21 22 24 25 | — |

### Dezenas faltantes mais frequentes

**Para 14 hits:** `16`(57x), `23`(49x), `17`(43x), `20`(36x), `06`(35x), `04`(29x), `08`(27x), `10`(19x)
**Para 15 hits:** `16`(8x), `23`(6x), `06`(5x), `10`(3x), `08`(3x), `04`(2x), `24`(2x), `20`(1x)

### Comparacao LotoIA vs concursos oficiais

**Prefixos oficiais raros na LotoIA:**
- `01-05-06` oficial:2 LotoIA:0
- `01-04-06` oficial:4 LotoIA:0
- `01-03-07` oficial:1 LotoIA:0
- `02-04-05` oficial:1 LotoIA:0
- `02-05-06` oficial:1 LotoIA:0

**Prefixos LotoIA excessivos:**
- `01-02-05` LotoIA:51 oficial:0
- `03-04-05` LotoIA:35 oficial:0
- `01-04-05` LotoIA:17 oficial:0

---

## STRUCT_TEST_19D_001  (game_size=19D)

**Status:** INCOMPLETO (incompleto)
**Evidence level:** LOCAL_DIAGNOSTIC

### Resumo quantitativo

| Metrica | Valor | Esperado |
|---|---|---|
| generation_events | 4 | 20 |
| jogos analisados | 700 | — |
| concursos analisados | 5 ([3707, 3708, 3709, 3710, 3711]) | 5 |
| generation_event_ids | [19, 20, 21, 22] | — |
| reconciliation_run_ids | [145, 146, 147, 148, 149, 150, 151, 152, 153, 155]... | — |

### Distribuicao de acertos (reconciliation_runs)

| Melhor acerto (stuck 15) | Stuck 14 | Stuck 13 |
|---|---|---|
| 1 jogos com 15 hits | 34 jogos com 14 hits | 126 jogos com 13 hits |

### Estrutura do cartao

| | Mais gerado | Frequencia |
|---|---|---|
| Prefixo 3 | `01-02-03` | 411 |
| Prefixo 4 | `01-02-03-04` | 307 |
| Sufixo 3 | `22-24-25` | 455 |
| Sufixo 4 | `21-22-24-25` | 402 |

**Ranking prefixo 3:** `01-02-03` (411x) | `01-03-04` (165x) | `01-02-04` (71x)
**Ranking prefixo 4:** `01-02-03-04` (307x) | `01-03-04-05` (156x) | `01-02-03-05` (98x)
**Ranking sufixo 3:** `22-24-25` (455x) | `23-24-25` (147x) | `21-24-25` (41x)
**Ranking sufixo 4:** `21-22-24-25` (402x) | `22-23-24-25` (99x) | `21-23-24-25` (48x)

### Faixas e gaps

**Maior gap observado:** `5`
**Gaps mais comuns:** `[2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 3, 2, 1, 1, 2, 1]`(25x), `[1, 1, 1, 1, 4, 1, 1, 1, 1, 1, 1, 1, 2, 1, 2, 1, 2, 1]`(22x), `[1, 1, 1, 1, 2, 2, 1, 1, 1, 1, 1, 1, 1, 2, 3, 1, 2, 1]`(16x)

### Redundancia GP

| Similaridade media | Sobreposicao maxima | Quase repetidos |
|---|---|---|
| 0.8212 | 19 | 244650 |

**Dezenas mais ausentes no GP:**

| Dezena | Jogos ausente |
|---|---|
| `23` | 514 |
| `17` | 456 |
| `19` | 406 |
| `20` | 390 |
| `07` | 358 |
| `16` | 341 |
| `06` | 238 |
| `08` | 219 |

### Travamento em 13/14/15

| Faixa | Jogos |
|---|---|
| 13 hits | 126 |
| 14 hits | 34 |
| 15 hits | 1 |

#### Jogos travados em 13 hits

**Quantidade:** 126

**generation_event_ids:** [19, 20, 21, 22]
**reconciliation_run_ids:** [145, 146, 147, 148, 149, 150, 151, 152, 153, 155, 156, 157, 158, 159]

**Dezenas mais presentes:** `18`(126x), `25`(126x), `01`(122x), `09`(121x), `13`(120x)
**Dezenas mais ausentes:** `23`(94x), `17`(87x), `19`(82x), `07`(67x), `16`(65x)
**Faltantes para 14:** `17`(50x), `23`(36x), `06`(25x), `02`(22x), `16`(21x)
**Prefixo 3 dominante:** `01,02,03` (79x) | `01,03,04` (30x) | `01,02,04` (9x)
**Prefixo 4 dominante:** `01,02,03,04` (56x) | `01,03,04,05` (28x) | `01,02,03,05` (22x)
**Sufixo 3 dominante:** `22,24,25` (84x) | `23,24,25` (27x) | `21,24,25` (7x)
**Sufixo 4 dominante:** `21,22,24,25` (68x) | `22,23,24,25` (19x) | `20,22,24,25` (14x)
**Pares quase-identicos (sobreposicao >= size-2):** 434

**Amostra (ate 10 jogos):**

| ge_id | rr_id | hits | dezenas | faltantes |
|---|---|---|---|---|
| 22 | 159 | 13 | 01 02 03 04 08 09 10 11 13 14 15 17 18 19 21 22 23 24 25 | 07 20 |
| 22 | 159 | 13 | 01 02 03 05 06 08 09 10 11 13 14 15 17 18 20 21 23 24 25 | 07 22 |
| 22 | 159 | 13 | 01 03 04 05 06 07 08 09 10 11 13 14 15 18 20 21 22 24 25 | 02 23 |
| 22 | 159 | 13 | 01 02 03 04 05 06 08 09 10 11 13 14 15 18 20 21 22 24 25 | 07 23 |
| 22 | 159 | 13 | 01 02 03 04 06 07 08 09 10 11 12 13 15 18 20 21 22 24 25 | 14 23 |
| 22 | 159 | 13 | 01 02 04 05 06 07 08 09 10 11 13 14 15 18 20 21 22 24 25 | 03 23 |
| 22 | 159 | 13 | 01 02 03 04 05 06 07 08 09 10 11 13 14 15 18 20 21 24 25 | 22 23 |
| 22 | 159 | 13 | 01 02 03 04 05 06 07 08 10 11 13 14 15 18 20 21 22 24 25 | 09 23 |
| 22 | 159 | 13 | 01 02 03 04 05 07 08 09 10 11 12 13 14 15 18 20 22 24 25 | 21 23 |
| 21 | 158 | 13 | 01 02 03 05 06 08 09 10 11 13 14 15 17 18 21 22 23 24 25 | 07 20 |

#### Jogos travados em 14 hits

**Quantidade:** 34

**generation_event_ids:** [19, 20, 21, 22]
**reconciliation_run_ids:** [149, 150, 151, 152, 155, 156, 157, 158, 159]

**Dezenas mais presentes:** `01`(34x), `02`(34x), `03`(34x), `14`(34x), `18`(34x)
**Dezenas mais ausentes:** `23`(25x), `19`(20x), `07`(19x), `20`(17x), `17`(16x)
**Faltantes para 15:** `23`(13x), `06`(4x), `05`(4x), `21`(3x), `07`(2x)
**Prefixo 3 dominante:** `01,02,03` (34x)
**Prefixo 4 dominante:** `01,02,03,04` (26x) | `01,02,03,05` (8x)
**Sufixo 3 dominante:** `22,24,25` (17x) | `23,24,25` (7x) | `21,24,25` (6x)
**Sufixo 4 dominante:** `21,22,24,25` (17x) | `19,21,24,25` (6x) | `22,23,24,25` (5x)
**Pares quase-identicos (sobreposicao >= size-2):** 139

**Amostra (ate 10 jogos):**

| ge_id | rr_id | hits | dezenas | faltantes |
|---|---|---|---|---|
| 22 | 159 | 14 | 01 02 03 04 05 06 07 08 09 10 11 13 14 18 20 22 23 24 25 | 21 |
| 22 | 159 | 14 | 01 02 03 04 07 08 09 10 11 12 13 14 15 18 20 21 22 24 25 | 23 |
| 22 | 159 | 14 | 01 02 03 05 06 08 09 10 11 12 13 14 18 20 21 22 23 24 25 | 07 |
| 22 | 159 | 14 | 01 02 03 05 06 07 08 09 10 11 13 14 15 18 20 21 22 24 25 | 23 |
| 22 | 159 | 14 | 01 02 03 05 06 07 08 09 10 13 14 15 16 18 20 21 22 24 25 | 23 |
| 22 | 159 | 14 | 01 02 03 04 05 07 08 09 10 11 13 14 15 18 20 21 22 24 25 | 23 |
| 21 | 158 | 14 | 01 02 03 04 05 06 07 08 09 10 11 13 14 18 20 22 23 24 25 | 21 |
| 21 | 158 | 14 | 01 02 03 04 07 08 09 10 11 12 13 14 15 18 20 21 22 24 25 | 23 |
| 21 | 158 | 14 | 01 02 03 05 06 07 08 09 10 11 12 13 14 18 20 21 22 24 25 | 23 |
| 21 | 158 | 14 | 01 02 03 04 06 07 08 09 10 11 13 14 15 18 20 21 22 24 25 | 23 |

#### Jogos travados em 15 hits

**Quantidade:** 1

**generation_event_ids:** [20]
**reconciliation_run_ids:** [150]

**Dezenas mais presentes:** `01`(1x), `02`(1x), `03`(1x), `04`(1x), `05`(1x)
**Dezenas mais ausentes:** `07`(1x), `08`(1x), `10`(1x), `11`(1x), `20`(1x)
**Faltantes (jackpot atingido):** —
**Prefixo 3 dominante:** `01,02,03` (1x)
**Prefixo 4 dominante:** `01,02,03,04` (1x)
**Sufixo 3 dominante:** `23,24,25` (1x)
**Sufixo 4 dominante:** `21,23,24,25` (1x)
**Pares quase-identicos (sobreposicao >= size-2):** 0

**Amostra (ate 10 jogos):**

| ge_id | rr_id | hits | dezenas | faltantes |
|---|---|---|---|---|
| 20 | 150 | 15 | 01 02 03 04 05 06 09 12 13 14 15 16 17 18 19 21 23 24 25 | — |

### Dezenas faltantes mais frequentes

**Para 14 hits:** `17`(50x), `23`(36x), `06`(25x), `02`(22x), `16`(21x), `07`(15x), `04`(13x), `12`(10x)
**Para 15 hits:** `23`(13x), `06`(4x), `05`(4x), `21`(3x), `07`(2x), `16`(2x), `09`(2x), `12`(2x)

### Comparacao LotoIA vs concursos oficiais

**Prefixos oficiais raros na LotoIA:**
- `01-05-06` oficial:2 LotoIA:0
- `01-04-06` oficial:4 LotoIA:0
- `01-03-05` oficial:4 LotoIA:0
- `01-03-07` oficial:1 LotoIA:0
- `02-04-05` oficial:1 LotoIA:0

**Prefixos LotoIA excessivos:**
- `03-04-05` LotoIA:6 oficial:0
- `01-04-05` LotoIA:14 oficial:0
- `01-02-05` LotoIA:5 oficial:0

---

## STRUCT_TEST_20D_001  (game_size=20D)

**Status:** INCOMPLETO (incompleto)
**Evidence level:** LOCAL_DIAGNOSTIC

### Resumo quantitativo

| Metrica | Valor | Esperado |
|---|---|---|
| generation_events | 4 | 20 |
| jogos analisados | 1200 | — |
| concursos analisados | 6 ([3705, 3706, 3708, 3709, 3710, 3711]) | 5 |
| generation_event_ids | [23, 24, 25, 26] | — |
| reconciliation_run_ids | [154, 160, 161, 162, 163, 164, 165, 166, 167, 168]... | — |

### Distribuicao de acertos (reconciliation_runs)

| Melhor acerto (stuck 15) | Stuck 14 | Stuck 13 |
|---|---|---|
| 19 jogos com 15 hits | 137 jogos com 14 hits | 366 jogos com 13 hits |

### Estrutura do cartao

| | Mais gerado | Frequencia |
|---|---|---|
| Prefixo 3 | `01-02-03` | 753 |
| Prefixo 4 | `01-02-03-04` | 587 |
| Sufixo 3 | `22-24-25` | 695 |
| Sufixo 4 | `21-22-24-25` | 622 |

**Ranking prefixo 3:** `01-02-03` (753x) | `01-03-04` (237x) | `01-02-04` (129x)
**Ranking prefixo 4:** `01-02-03-04` (587x) | `01-03-04-05` (217x) | `01-02-03-05` (141x)
**Ranking sufixo 3:** `22-24-25` (695x) | `23-24-25` (429x) | `22-23-25` (71x)
**Ranking sufixo 4:** `21-22-24-25` (622x) | `22-23-24-25` (299x) | `21-23-24-25` (130x)

### Faixas e gaps

**Maior gap observado:** `5`
**Gaps mais comuns:** `[2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 2, 1, 1, 2, 1]`(64x), `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 3, 2, 1, 1, 2, 1]`(42x), `[1, 1, 1, 1, 4, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 2, 1]`(31x)

### Redundancia GP

| Similaridade media | Sobreposicao maxima | Quase repetidos |
|---|---|---|
| 0.838 | 20 | 719400 |

**Dezenas mais ausentes no GP:**

| Dezena | Jogos ausente |
|---|---|
| `23` | 700 |
| `17` | 650 |
| `20` | 588 |
| `19` | 547 |
| `07` | 503 |
| `16` | 391 |
| `06` | 357 |
| `08` | 339 |

### Travamento em 13/14/15

| Faixa | Jogos |
|---|---|
| 13 hits | 366 |
| 14 hits | 137 |
| 15 hits | 19 |

#### Jogos travados em 13 hits

**Quantidade:** 366

**generation_event_ids:** [23, 24, 25, 26]
**reconciliation_run_ids:** [154, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173]...

**Dezenas mais presentes:** `18`(366x), `25`(366x), `15`(356x), `01`(354x), `13`(353x)
**Dezenas mais ausentes:** `23`(225x), `17`(211x), `19`(193x), `20`(159x), `07`(149x)
**Faltantes para 14:** `16`(85x), `06`(80x), `17`(79x), `19`(60x), `23`(59x)
**Prefixo 3 dominante:** `01,02,03` (215x) | `01,03,04` (85x) | `01,02,04` (45x)
**Prefixo 4 dominante:** `01,02,03,04` (175x) | `01,03,04,05` (80x) | `01,02,04,05` (45x)
**Sufixo 3 dominante:** `22,24,25` (224x) | `23,24,25` (125x) | `22,23,25` (16x)
**Sufixo 4 dominante:** `21,22,24,25` (186x) | `22,23,24,25` (84x) | `21,23,24,25` (41x)
**Pares quase-identicos (sobreposicao >= size-2):** 1161

**Amostra (ate 10 jogos):**

| ge_id | rr_id | hits | dezenas | faltantes |
|---|---|---|---|---|
| 26 | 182 | 13 | 01 02 03 04 06 07 09 10 11 12 13 14 15 16 18 19 21 22 24 25 | 08 20 |
| 26 | 182 | 13 | 01 02 03 04 08 09 10 11 12 13 14 15 16 17 18 19 21 22 24 25 | 06 20 |
| 26 | 182 | 13 | 01 02 03 04 05 08 09 10 11 13 14 15 16 17 18 19 21 22 24 25 | 06 20 |
| 26 | 182 | 13 | 01 02 03 04 05 06 07 08 09 11 12 13 14 15 16 18 20 22 24 25 | 10 21 |
| 26 | 182 | 13 | 02 03 04 05 06 07 08 09 10 11 12 13 14 15 18 20 21 22 24 25 | 01 16 |
| 26 | 182 | 13 | 01 03 04 05 06 07 09 10 11 12 13 14 15 16 18 19 20 22 24 25 | 08 21 |
| 26 | 182 | 13 | 01 02 04 05 06 07 08 09 10 11 12 13 14 15 16 18 21 22 24 25 | 03 20 |
| 26 | 182 | 13 | 01 03 04 05 07 08 09 10 11 12 13 14 15 16 18 19 21 22 24 25 | 06 20 |
| 26 | 182 | 13 | 01 02 03 04 05 06 08 09 10 11 13 14 15 17 18 20 22 23 24 25 | 16 21 |
| 26 | 182 | 13 | 01 02 03 04 05 06 07 08 09 11 12 13 14 15 18 20 21 22 24 25 | 10 16 |

#### Jogos travados em 14 hits

**Quantidade:** 137

**generation_event_ids:** [23, 24, 25, 26]
**reconciliation_run_ids:** [154, 160, 161, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175]...

**Dezenas mais presentes:** `18`(137x), `25`(137x), `14`(136x), `01`(135x), `15`(135x)
**Dezenas mais ausentes:** `23`(100x), `17`(92x), `19`(71x), `20`(59x), `02`(49x)
**Faltantes para 15:** `16`(35x), `06`(31x), `08`(15x), `17`(11x), `10`(7x)
**Prefixo 3 dominante:** `01,02,03` (68x) | `01,03,04` (46x) | `01,02,04` (19x)
**Prefixo 4 dominante:** `01,02,03,04` (64x) | `01,03,04,05` (42x) | `01,02,04,05` (19x)
**Sufixo 3 dominante:** `22,24,25` (99x) | `23,24,25` (33x) | `22,23,25` (4x)
**Sufixo 4 dominante:** `21,22,24,25` (88x) | `22,23,24,25` (18x) | `21,23,24,25` (15x)
**Pares quase-identicos (sobreposicao >= size-2):** 640

**Amostra (ate 10 jogos):**

| ge_id | rr_id | hits | dezenas | faltantes |
|---|---|---|---|---|
| 26 | 182 | 14 | 01 02 03 04 05 06 08 09 10 11 13 14 15 18 20 21 22 23 24 25 | 16 |
| 26 | 182 | 14 | 01 03 04 05 06 07 08 09 10 11 12 13 14 15 18 20 21 22 24 25 | 16 |
| 26 | 182 | 14 | 01 02 03 04 05 06 07 08 09 10 11 13 14 15 18 20 21 22 24 25 | 16 |
| 26 | 182 | 14 | 01 03 04 05 06 07 08 09 10 11 12 13 14 15 18 20 21 22 24 25 | 16 |
| 26 | 182 | 14 | 01 03 04 05 06 07 08 09 10 11 12 13 14 15 18 20 21 22 24 25 | 16 |
| 26 | 182 | 14 | 01 02 03 04 05 07 08 10 11 12 13 14 15 16 18 20 21 22 24 25 | 06 |
| 26 | 182 | 14 | 01 02 03 04 05 06 07 08 09 13 14 15 16 18 20 21 22 23 24 25 | 10 |
| 26 | 182 | 14 | 01 02 03 04 05 06 07 08 09 10 11 13 14 15 18 20 21 22 24 25 | 16 |
| 26 | 182 | 14 | 01 03 04 05 06 07 08 09 10 11 12 13 14 15 18 20 21 22 24 25 | 16 |
| 26 | 182 | 14 | 01 03 04 05 07 08 09 10 11 12 14 15 16 18 19 20 21 22 24 25 | 06 |

#### Jogos travados em 15 hits

**Quantidade:** 19

**generation_event_ids:** [23, 24, 25, 26]
**reconciliation_run_ids:** [173, 176, 177, 178, 179, 180, 181, 182]

**Dezenas mais presentes:** `01`(19x), `04`(19x), `06`(19x), `08`(19x), `14`(19x)
**Dezenas mais ausentes:** `17`(18x), `23`(18x), `19`(16x), `02`(13x), `13`(6x)
**Faltantes (jackpot atingido):** —
**Prefixo 3 dominante:** `01,03,04` (13x) | `01,02,03` (3x) | `01,02,04` (3x)
**Prefixo 4 dominante:** `01,03,04,05` (9x) | `01,03,04,06` (4x) | `01,02,03,04` (3x)
**Sufixo 3 dominante:** `22,24,25` (18x) | `23,24,25` (1x)
**Sufixo 4 dominante:** `21,22,24,25` (18x) | `21,23,24,25` (1x)
**Pares quase-identicos (sobreposicao >= size-2):** 96

**Amostra (ate 10 jogos):**

| ge_id | rr_id | hits | dezenas | faltantes |
|---|---|---|---|---|
| 26 | 182 | 15 | 01 03 04 05 06 07 08 10 11 12 13 14 15 16 18 20 21 22 24 25 | — |
| 25 | 181 | 15 | 01 03 04 05 06 07 08 09 10 11 12 14 15 16 18 20 21 22 24 25 | — |
| 25 | 181 | 15 | 01 03 04 05 06 07 08 10 11 12 13 14 15 16 18 20 21 22 24 25 | — |
| 25 | 181 | 15 | 01 03 04 06 07 08 09 10 11 12 13 14 15 16 18 20 21 22 24 25 | — |
| 25 | 181 | 15 | 01 02 03 04 05 06 07 08 09 10 13 14 15 16 18 20 21 22 24 25 | — |
| 25 | 181 | 15 | 01 03 04 05 06 07 08 09 10 11 13 14 15 16 18 20 21 22 24 25 | — |
| 23 | 180 | 15 | 01 03 04 05 06 07 08 09 10 11 12 14 15 16 18 20 21 22 24 25 | — |
| 23 | 180 | 15 | 01 03 04 06 07 08 09 10 11 12 13 14 15 16 18 20 21 22 24 25 | — |
| 26 | 179 | 15 | 01 02 04 05 06 07 08 09 10 11 12 13 14 15 16 18 21 22 24 25 | — |
| 26 | 179 | 15 | 01 02 03 04 06 08 09 10 11 12 13 14 15 16 18 19 21 22 24 25 | — |

### Dezenas faltantes mais frequentes

**Para 14 hits:** `16`(85x), `06`(80x), `17`(79x), `19`(60x), `23`(59x), `12`(52x), `08`(51x), `10`(46x)
**Para 15 hits:** `16`(35x), `06`(31x), `08`(15x), `17`(11x), `10`(7x), `12`(6x), `09`(5x), `19`(5x)

### Comparacao LotoIA vs concursos oficiais

**Prefixos oficiais raros na LotoIA:**
- `01-05-06` oficial:2 LotoIA:0
- `01-04-06` oficial:4 LotoIA:0
- `01-03-05` oficial:4 LotoIA:0
- `01-03-07` oficial:1 LotoIA:0
- `02-04-05` oficial:1 LotoIA:0

**Prefixos LotoIA excessivos:**
- `01-02-05` LotoIA:6 oficial:0
- `01-04-05` LotoIA:11 oficial:0
- `03-04-05` LotoIA:5 oficial:0

---

## Comparativo final 15D-20D

| Lote | size | status | ge | jogos | conc | stuck_13 | stuck_14 | stuck_15 | redundancia |
|---|---|---|---|---|---|---|---|---|---|
| STRUCT_TEST_15D_001 | 15D | INCOMPLETO | 4 | 1300 | 7 | 0 | 0 | 0 | 0.8158 |
| STRUCT_TEST_16D_001 | 16D | INCOMPLETO | 5 | 1400 | 7 | 21 | 2 | 0 | 0.806 |
| STRUCT_TEST_17D_001 | 17D | INCOMPLETO | 4 | 1450 | 7 | 92 | 10 | 0 | 0.799 |
| STRUCT_TEST_18D_001 | 18D | INCOMPLETO | 4 | 1700 | 8 | 211 | 31 | 1 | 0.8115 |
| STRUCT_TEST_19D_001 | 19D | INCOMPLETO | 4 | 700 | 5 | 126 | 34 | 1 | 0.8212 |
| STRUCT_TEST_20D_001 | 20D | INCOMPLETO | 4 | 1200 | 6 | 366 | 137 | 19 | 0.838 |

---

## Analise comparativa

### Em qual formato a cobertura melhora?
- stuck_15 (jackpots) aparece apenas a partir do 18D, crescendo para 19 jogos no 20D.
- stuck_14 cresce consistentemente: 16D(2) → 17D(10) → 18D(31) → 19D(34) → 20D(137).
- O aumento de dezenas nao corrige o travamento — apenas desloca o threshold.

### Quais dezenas aparecem como vazamento recorrente?
- Verificar 'Dezenas mais ausentes no GP' por lote acima.

### Quais prefixos/sufixos dominam indevidamente?
- Prefixo `01-02-03` e sufixo `22-24-25` dominam em todos os lotes.
- Isso indica viés estrutural na abertura e fechamento do cartao.

### Qual formato parece mais estavel?
- 15D e 16D apresentam menor stuck_14 e stuck_15.
- 20D mostra maior diversidade de hits mas maior travamento absoluto.

---

## Observacoes institucionais

- Relatorio de somente leitura. Nenhuma acao operacional executada.
- Lotes INCOMPLETO requerem mais geracoes antes de comparacao definitiva.
- Lei 15, Lei 15A, pesos e filtros nao foram alterados.