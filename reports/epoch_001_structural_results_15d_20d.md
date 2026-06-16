# Relatorio EPOCH_001 — Resultados Estruturais 15D a 20D

**Gerado em:** 2026-06-16 08:30 UTC  
**Fonte:** Railway PostgreSQL  
**Operacional:** Apenas leitura. Sem efeito em geracao, Lei 15, pesos ou filtros.

---

## STRUCT_TEST_15D_001 (game_size=15D)

**STATUS: AUSENTE** — Sem dados

---

## STRUCT_TEST_16D_001  (game_size=16D)

**Status:** INCOMPLETO ⚠️  
**Evidence level:** LOCAL_DIAGNOSTIC

### Resumo quantitativo

| Metrica | Valor | Esperado |
|---|---|---|
| generation_events | 5 | 20 |
| jogos analisados | 1400 | — |
| concursos_comparados | 50 | 5 |
| generation_event_ids | [6, 7, 8, 9, 10] | — |
| reconciliation_run_ids | [47, 48, 49, 50, 51, 52, 53, 54, 55, 56]... | — |

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

### Redundancia GP

| Similaridade media | Sobreposicao maxima | Quase repetidos |
|---|---|---|
| 0.806 | 16 | 643405 |

**Dezenas mais ausentes no GP:**

| Dezena | Jogos ausente |
|---|---|
| 19 | 1344 |
| 23 | 1344 |
| 17 | 1260 |
| 07 | 1218 |
| 20 | 1176 |
| 16 | 1113 |
| 06 | 679 |
| 08 | 609 |

### Travamento em 13/14/15

| Faixa | Jogos travados |
|---|---|
| 13 hits | 21 |
| 14 hits | 2 |
| 15 hits | 0 |

#### Estrutura dos jogos travados em 13 hits

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
**Pares quase-identicos (sobreposicao >= size-2):** 71

**Amostra dos jogos (ate 10):**

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

#### Estrutura dos jogos travados em 14 hits

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

**Amostra dos jogos (ate 10):**

| ge_id | rr_id | hits | dezenas | faltantes |
|---|---|---|---|---|
| 10 | 56 | 14 | 01 02 03 05 06 09 12 13 14 15 16 17 18 21 24 25 | 04 |
| 8 | 54 | 14 | 01 02 03 04 05 06 09 12 13 14 15 16 18 21 24 25 | 17 |

#### Estrutura dos jogos travados em 15 hits

**Quantidade:** 0

_Nenhum jogo travado nesta faixa._

### Dezenas faltantes mais frequentes

**Para atingir 14 hits (a partir de jogos com 13):**
| Dezena | Frequencia |
|---|---|
| 16 | 8 |
| 06 | 6 |
| 20 | 4 |
| 08 | 4 |
| 17 | 4 |
| 04 | 3 |
| 24 | 3 |
| 10 | 2 |
| 23 | 2 |
| 02 | 2 |

**Para atingir 15 hits (a partir de jogos com 14):**
| Dezena | Frequencia |
|---|---|
| 04 | 1 |
| 17 | 1 |

### Comparacao LotoIA vs concursos oficiais

**Prefixos oficiais raros na LotoIA:**
- prefixo `01-05-06` — oficial:2 LotoIA:0
- prefixo `01-04-06` — oficial:4 LotoIA:0
- prefixo `01-03-07` — oficial:1 LotoIA:0
- prefixo `02-04-05` — oficial:1 LotoIA:0
- prefixo `02-05-06` — oficial:1 LotoIA:0

**Prefixos LotoIA excessivos:**
- prefixo `03-04-05` — LotoIA:28 oficial:0
- prefixo `01-03-06` — LotoIA:14 oficial:0
- prefixo `01-02-05` — LotoIA:49 oficial:0
- prefixo `01-04-05` — LotoIA:35 oficial:0
- prefixo `03-05-06` — LotoIA:7 oficial:0

---

## STRUCT_TEST_17D_001  (game_size=17D)

**Status:** INCOMPLETO ⚠️  
**Evidence level:** LOCAL_DIAGNOSTIC

### Resumo quantitativo

| Metrica | Valor | Esperado |
|---|---|---|
| generation_events | 4 | 20 |
| jogos analisados | 1450 | — |
| concursos_comparados | 50 | 5 |
| generation_event_ids | [11, 12, 13, 14] | — |
| reconciliation_run_ids | [82, 83, 84, 85, 86, 87, 88, 89, 90, 91]... | — |

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

### Redundancia GP

| Similaridade media | Sobreposicao maxima | Quase repetidos |
|---|---|---|
| 0.799 | 17 | 889289 |

**Dezenas mais ausentes no GP:**

| Dezena | Jogos ausente |
|---|---|
| 23 | 1254 |
| 17 | 1246 |
| 19 | 1210 |
| 20 | 1052 |
| 07 | 1027 |
| 16 | 971 |
| 02 | 605 |
| 06 | 593 |

### Travamento em 13/14/15

| Faixa | Jogos travados |
|---|---|
| 13 hits | 92 |
| 14 hits | 10 |
| 15 hits | 0 |

#### Estrutura dos jogos travados em 13 hits

**Quantidade:** 92

**generation_event_ids:** [11, 12, 13, 14]
**reconciliation_run_ids:** [86, 87, 88, 89, 90, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110]

**Dezenas mais presentes:** `18`(92x), `25`(92x), `14`(91x), `15`(90x), `01`(88x)
**Dezenas mais ausentes:** `23`(90x), `17`(89x), `19`(82x), `07`(75x), `20`(66x)
**Faltantes para 14:** `16`(41x), `08`(17x), `17`(16x), `06`(15x), `04`(14x)

**Prefixo 3 dominante:** `01,03,04` (40x) | `01,02,03` (17x) | `01,04,05` (8x)
**Prefixo 4 dominante:** `01,03,04,05` (31x) | `01,02,03,04` (16x) | `01,03,04,06` (9x)
**Sufixo 3 dominante:** `22,24,25` (67x) | `21,24,25` (12x) | `21,22,25` (10x)
**Sufixo 4 dominante:** `21,22,24,25` (62x) | `18,21,22,25` (7x) | `18,21,24,25` (6x)
**Pares quase-identicos (sobreposicao >= size-2):** 1474

**Amostra dos jogos (ate 10):**

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

#### Estrutura dos jogos travados em 14 hits

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

**Amostra dos jogos (ate 10):**

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

#### Estrutura dos jogos travados em 15 hits

**Quantidade:** 0

_Nenhum jogo travado nesta faixa._

### Dezenas faltantes mais frequentes

**Para atingir 14 hits (a partir de jogos com 13):**
| Dezena | Frequencia |
|---|---|
| 16 | 41 |
| 08 | 17 |
| 17 | 16 |
| 06 | 15 |
| 04 | 14 |
| 10 | 12 |
| 20 | 11 |
| 22 | 11 |
| 02 | 9 |
| 12 | 7 |

**Para atingir 15 hits (a partir de jogos com 14):**
| Dezena | Frequencia |
|---|---|
| 16 | 3 |
| 22 | 2 |
| 23 | 2 |
| 10 | 1 |
| 24 | 1 |
| 08 | 1 |

### Comparacao LotoIA vs concursos oficiais

**Prefixos oficiais raros na LotoIA:**
- prefixo `01-05-06` — oficial:2 LotoIA:0
- prefixo `01-04-06` — oficial:4 LotoIA:0
- prefixo `01-03-07` — oficial:1 LotoIA:0
- prefixo `02-04-05` — oficial:1 LotoIA:0
- prefixo `02-05-06` — oficial:1 LotoIA:0

**Prefixos LotoIA excessivos:**
- prefixo `03-04-05` — LotoIA:81 oficial:0
- prefixo `01-02-05` — LotoIA:43 oficial:0
- prefixo `03-05-06` — LotoIA:8 oficial:0
- prefixo `01-04-05` — LotoIA:49 oficial:0
- prefixo `01-03-06` — LotoIA:21 oficial:0

---

## STRUCT_TEST_18D_001  (game_size=18D)

**Status:** INCOMPLETO ⚠️  
**Evidence level:** LOCAL_DIAGNOSTIC

### Resumo quantitativo

| Metrica | Valor | Esperado |
|---|---|---|
| generation_events | 4 | 20 |
| jogos analisados | 1700 | — |
| concursos_comparados | 50 | 5 |
| generation_event_ids | [15, 16, 17, 18] | — |
| reconciliation_run_ids | [111, 112, 113, 114, 115, 116, 117, 118, 119, 120]... | — |

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

### Redundancia GP

| Similaridade media | Sobreposicao maxima | Quase repetidos |
|---|---|---|
| 0.8115 | 18 | 1416104 |

**Dezenas mais ausentes no GP:**

| Dezena | Jogos ausente |
|---|---|
| 23 | 1411 |
| 17 | 1361 |
| 19 | 1205 |
| 20 | 1087 |
| 07 | 997 |
| 16 | 993 |
| 06 | 679 |
| 12 | 570 |

### Travamento em 13/14/15

| Faixa | Jogos travados |
|---|---|
| 13 hits | 211 |
| 14 hits | 31 |
| 15 hits | 1 |

#### Estrutura dos jogos travados em 13 hits

**Quantidade:** 211

**generation_event_ids:** [15, 16, 17, 18]
**reconciliation_run_ids:** [112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144]

**Dezenas mais presentes:** `18`(211x), `25`(211x), `14`(207x), `01`(203x), `09`(202x)
**Dezenas mais ausentes:** `17`(200x), `23`(198x), `19`(147x), `07`(128x), `20`(123x)
**Faltantes para 14:** `16`(57x), `23`(49x), `17`(43x), `20`(36x), `06`(35x)

**Prefixo 3 dominante:** `01,02,03` (99x) | `01,03,04` (70x) | `01,02,04` (14x)
**Prefixo 4 dominante:** `01,02,03,04` (66x) | `01,03,04,05` (54x) | `01,02,03,05` (30x)
**Sufixo 3 dominante:** `22,24,25` (150x) | `21,24,25` (25x) | `21,22,25` (20x)
**Sufixo 4 dominante:** `21,22,24,25` (135x) | `19,21,24,25` (19x) | `19,21,22,25` (16x)
**Pares quase-identicos (sobreposicao >= size-2):** 6166

**Amostra dos jogos (ate 10):**

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

#### Estrutura dos jogos travados em 14 hits

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
**Pares quase-identicos (sobreposicao >= size-2):** 187

**Amostra dos jogos (ate 10):**

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

#### Estrutura dos jogos travados em 15 hits

**Quantidade:** 1

**generation_event_ids:** [15]
**reconciliation_run_ids:** [133]

**Dezenas mais presentes:** `01`(1x), `03`(1x), `04`(1x), `05`(1x), `06`(1x)
**Dezenas mais ausentes:** `02`(1x), `07`(1x), `13`(1x), `17`(1x), `19`(1x)
**Faltantes (jackpot já atingido):** —

**Prefixo 3 dominante:** `01,03,04` (1x)
**Prefixo 4 dominante:** `01,03,04,05` (1x)
**Sufixo 3 dominante:** `22,24,25` (1x)
**Sufixo 4 dominante:** `21,22,24,25` (1x)
**Pares quase-identicos (sobreposicao >= size-2):** 0

**Amostra dos jogos (ate 10):**

| ge_id | rr_id | hits | dezenas | faltantes |
|---|---|---|---|---|
| 15 | 133 | 15 | 01 03 04 05 06 08 09 10 11 12 14 15 16 18 21 22 24 25 | — |

### Dezenas faltantes mais frequentes

**Para atingir 14 hits (a partir de jogos com 13):**
| Dezena | Frequencia |
|---|---|
| 16 | 57 |
| 23 | 49 |
| 17 | 43 |
| 20 | 36 |
| 06 | 35 |
| 04 | 29 |
| 08 | 27 |
| 10 | 19 |
| 12 | 16 |
| 02 | 15 |

**Para atingir 15 hits (a partir de jogos com 14):**
| Dezena | Frequencia |
|---|---|
| 16 | 8 |
| 23 | 6 |
| 06 | 5 |
| 10 | 3 |
| 08 | 3 |
| 04 | 2 |
| 24 | 2 |
| 20 | 1 |
| 03 | 1 |

### Comparacao LotoIA vs concursos oficiais

**Prefixos oficiais raros na LotoIA:**
- prefixo `01-05-06` — oficial:2 LotoIA:0
- prefixo `01-04-06` — oficial:4 LotoIA:0
- prefixo `01-03-07` — oficial:1 LotoIA:0
- prefixo `02-04-05` — oficial:1 LotoIA:0
- prefixo `02-05-06` — oficial:1 LotoIA:0

**Prefixos LotoIA excessivos:**
- prefixo `01-02-05` — LotoIA:51 oficial:0
- prefixo `03-04-05` — LotoIA:35 oficial:0
- prefixo `01-04-05` — LotoIA:17 oficial:0

---

## STRUCT_TEST_19D_001  (game_size=19D)

**Status:** INCOMPLETO ⚠️  
**Evidence level:** LOCAL_DIAGNOSTIC

### Resumo quantitativo

| Metrica | Valor | Esperado |
|---|---|---|
| generation_events | 4 | 20 |
| jogos analisados | 700 | — |
| concursos_comparados | 50 | 5 |
| generation_event_ids | [19, 20, 21, 22] | — |
| reconciliation_run_ids | [145, 146, 147, 148, 149, 150, 151, 152, 153, 155]... | — |

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

### Redundancia GP

| Similaridade media | Sobreposicao maxima | Quase repetidos |
|---|---|---|
| 0.8212 | 19 | 244650 |

**Dezenas mais ausentes no GP:**

| Dezena | Jogos ausente |
|---|---|
| 23 | 514 |
| 17 | 456 |
| 19 | 406 |
| 20 | 390 |
| 07 | 358 |
| 16 | 341 |
| 06 | 238 |
| 08 | 219 |

### Travamento em 13/14/15

| Faixa | Jogos travados |
|---|---|
| 13 hits | 126 |
| 14 hits | 34 |
| 15 hits | 1 |

#### Estrutura dos jogos travados em 13 hits

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
**Pares quase-identicos (sobreposicao >= size-2):** 2159

**Amostra dos jogos (ate 10):**

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

#### Estrutura dos jogos travados em 14 hits

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
**Pares quase-identicos (sobreposicao >= size-2):** 178

**Amostra dos jogos (ate 10):**

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

#### Estrutura dos jogos travados em 15 hits

**Quantidade:** 1

**generation_event_ids:** [20]
**reconciliation_run_ids:** [150]

**Dezenas mais presentes:** `01`(1x), `02`(1x), `03`(1x), `04`(1x), `05`(1x)
**Dezenas mais ausentes:** `07`(1x), `08`(1x), `10`(1x), `11`(1x), `20`(1x)
**Faltantes (jackpot já atingido):** —

**Prefixo 3 dominante:** `01,02,03` (1x)
**Prefixo 4 dominante:** `01,02,03,04` (1x)
**Sufixo 3 dominante:** `23,24,25` (1x)
**Sufixo 4 dominante:** `21,23,24,25` (1x)
**Pares quase-identicos (sobreposicao >= size-2):** 0

**Amostra dos jogos (ate 10):**

| ge_id | rr_id | hits | dezenas | faltantes |
|---|---|---|---|---|
| 20 | 150 | 15 | 01 02 03 04 05 06 09 12 13 14 15 16 17 18 19 21 23 24 25 | — |

### Dezenas faltantes mais frequentes

**Para atingir 14 hits (a partir de jogos com 13):**
| Dezena | Frequencia |
|---|---|
| 17 | 50 |
| 23 | 36 |
| 06 | 25 |
| 02 | 22 |
| 16 | 21 |
| 07 | 15 |
| 04 | 13 |
| 12 | 10 |
| 20 | 9 |
| 03 | 9 |

**Para atingir 15 hits (a partir de jogos com 14):**
| Dezena | Frequencia |
|---|---|
| 23 | 13 |
| 06 | 4 |
| 05 | 4 |
| 21 | 3 |
| 07 | 2 |
| 16 | 2 |
| 09 | 2 |
| 12 | 2 |
| 13 | 2 |

### Comparacao LotoIA vs concursos oficiais

**Prefixos oficiais raros na LotoIA:**
- prefixo `01-05-06` — oficial:2 LotoIA:0
- prefixo `01-04-06` — oficial:4 LotoIA:0
- prefixo `01-03-05` — oficial:4 LotoIA:0
- prefixo `01-03-07` — oficial:1 LotoIA:0
- prefixo `02-04-05` — oficial:1 LotoIA:0

**Prefixos LotoIA excessivos:**
- prefixo `03-04-05` — LotoIA:6 oficial:0
- prefixo `01-04-05` — LotoIA:14 oficial:0
- prefixo `01-02-05` — LotoIA:5 oficial:0

---

## STRUCT_TEST_20D_001  (game_size=20D)

**Status:** INCOMPLETO ⚠️  
**Evidence level:** LOCAL_DIAGNOSTIC

### Resumo quantitativo

| Metrica | Valor | Esperado |
|---|---|---|
| generation_events | 4 | 20 |
| jogos analisados | 1200 | — |
| concursos_comparados | 50 | 5 |
| generation_event_ids | [23, 24, 25, 26] | — |
| reconciliation_run_ids | [154, 160, 161, 162, 163, 164, 165, 166, 167, 168]... | — |

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

### Redundancia GP

| Similaridade media | Sobreposicao maxima | Quase repetidos |
|---|---|---|
| 0.838 | 20 | 719400 |

**Dezenas mais ausentes no GP:**

| Dezena | Jogos ausente |
|---|---|
| 23 | 700 |
| 17 | 650 |
| 20 | 588 |
| 19 | 547 |
| 07 | 503 |
| 16 | 391 |
| 06 | 357 |
| 08 | 339 |

### Travamento em 13/14/15

| Faixa | Jogos travados |
|---|---|
| 13 hits | 366 |
| 14 hits | 137 |
| 15 hits | 19 |

#### Estrutura dos jogos travados em 13 hits

**Quantidade:** 366

**generation_event_ids:** [23, 24, 25, 26]
**reconciliation_run_ids:** [154, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182]

**Dezenas mais presentes:** `18`(366x), `25`(366x), `15`(356x), `01`(354x), `13`(353x)
**Dezenas mais ausentes:** `23`(225x), `17`(211x), `19`(193x), `20`(159x), `07`(149x)
**Faltantes para 14:** `16`(85x), `06`(80x), `17`(79x), `19`(60x), `23`(59x)

**Prefixo 3 dominante:** `01,02,03` (215x) | `01,03,04` (85x) | `01,02,04` (45x)
**Prefixo 4 dominante:** `01,02,03,04` (175x) | `01,03,04,05` (80x) | `01,02,04,05` (45x)
**Sufixo 3 dominante:** `22,24,25` (224x) | `23,24,25` (125x) | `22,23,25` (16x)
**Sufixo 4 dominante:** `21,22,24,25` (186x) | `22,23,24,25` (84x) | `21,23,24,25` (41x)
**Pares quase-identicos (sobreposicao >= size-2):** 20974

**Amostra dos jogos (ate 10):**

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

#### Estrutura dos jogos travados em 14 hits

**Quantidade:** 137

**generation_event_ids:** [23, 24, 25, 26]
**reconciliation_run_ids:** [154, 160, 161, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182]

**Dezenas mais presentes:** `18`(137x), `25`(137x), `14`(136x), `01`(135x), `15`(135x)
**Dezenas mais ausentes:** `23`(100x), `17`(92x), `19`(71x), `20`(59x), `02`(49x)
**Faltantes para 15:** `16`(35x), `06`(31x), `08`(15x), `17`(11x), `10`(7x)

**Prefixo 3 dominante:** `01,02,03` (68x) | `01,03,04` (46x) | `01,02,04` (19x)
**Prefixo 4 dominante:** `01,02,03,04` (64x) | `01,03,04,05` (42x) | `01,02,04,05` (19x)
**Sufixo 3 dominante:** `22,24,25` (99x) | `23,24,25` (33x) | `22,23,25` (4x)
**Sufixo 4 dominante:** `21,22,24,25` (88x) | `22,23,24,25` (18x) | `21,23,24,25` (15x)
**Pares quase-identicos (sobreposicao >= size-2):** 3695

**Amostra dos jogos (ate 10):**

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

#### Estrutura dos jogos travados em 15 hits

**Quantidade:** 19

**generation_event_ids:** [23, 24, 25, 26]
**reconciliation_run_ids:** [173, 176, 177, 178, 179, 180, 181, 182]

**Dezenas mais presentes:** `01`(19x), `04`(19x), `06`(19x), `08`(19x), `14`(19x)
**Dezenas mais ausentes:** `17`(18x), `23`(18x), `19`(16x), `02`(13x), `13`(6x)
**Faltantes (jackpot já atingido):** —

**Prefixo 3 dominante:** `01,03,04` (13x) | `01,02,03` (3x) | `01,02,04` (3x)
**Prefixo 4 dominante:** `01,03,04,05` (9x) | `01,03,04,06` (4x) | `01,02,03,04` (3x)
**Sufixo 3 dominante:** `22,24,25` (18x) | `23,24,25` (1x)
**Sufixo 4 dominante:** `21,22,24,25` (18x) | `21,23,24,25` (1x)
**Pares quase-identicos (sobreposicao >= size-2):** 129

**Amostra dos jogos (ate 10):**

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

**Para atingir 14 hits (a partir de jogos com 13):**
| Dezena | Frequencia |
|---|---|
| 16 | 85 |
| 06 | 80 |
| 17 | 79 |
| 19 | 60 |
| 23 | 59 |
| 12 | 52 |
| 08 | 51 |
| 10 | 46 |
| 20 | 39 |
| 04 | 37 |

**Para atingir 15 hits (a partir de jogos com 14):**
| Dezena | Frequencia |
|---|---|
| 16 | 35 |
| 06 | 31 |
| 08 | 15 |
| 17 | 11 |
| 10 | 7 |
| 12 | 6 |
| 09 | 5 |
| 19 | 5 |
| 23 | 4 |
| 04 | 4 |

### Comparacao LotoIA vs concursos oficiais

**Prefixos oficiais raros na LotoIA:**
- prefixo `01-05-06` — oficial:2 LotoIA:0
- prefixo `01-04-06` — oficial:4 LotoIA:0
- prefixo `01-03-05` — oficial:4 LotoIA:0
- prefixo `01-03-07` — oficial:1 LotoIA:0
- prefixo `02-04-05` — oficial:1 LotoIA:0

**Prefixos LotoIA excessivos:**
- prefixo `01-02-05` — LotoIA:6 oficial:0
- prefixo `01-04-05` — LotoIA:11 oficial:0
- prefixo `03-04-05` — LotoIA:5 oficial:0

---

## Comparativo entre formatos

| Lote | size | status | ge | conc | jogos | stuck_13 | stuck_14 | stuck_15 |
|---|---|---|---|---|---|---|---|---|
| STRUCT_TEST_15D_001 | 15D | AUSENTE | 0 | 0 | 0 | 0 | 0 | 0 |
| STRUCT_TEST_16D_001 | 16D | INCOMPLETO | 5 | 50 | 1400 | 21 | 2 | 0 |
| STRUCT_TEST_17D_001 | 17D | INCOMPLETO | 4 | 50 | 1450 | 92 | 10 | 0 |
| STRUCT_TEST_18D_001 | 18D | INCOMPLETO | 4 | 50 | 1700 | 211 | 31 | 1 |
| STRUCT_TEST_19D_001 | 19D | INCOMPLETO | 4 | 50 | 700 | 126 | 34 | 1 |
| STRUCT_TEST_20D_001 | 20D | INCOMPLETO | 4 | 50 | 1200 | 366 | 137 | 19 |

---

## Observacoes institucionais

- Relatorio de **somente leitura**. Nenhuma acao operacional executada.
- Lotes INCOMPLETO requerem geracao adicional antes de comparacao definitiva.
- stuck_14 alto indica jogos proximos ao jackpot que nao o atingiram.
- stuck_15 = jackpots (15 acertos) dentro do lote analisado.
- Comparacao completa LotoIA vs oficiais disponivel no painel Cobertura Estrutural.
- Lei 15, Lei 15A, pesos e filtros nao foram alterados.