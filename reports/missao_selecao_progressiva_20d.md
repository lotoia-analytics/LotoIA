# Matriz de Recorr?ncia da Barreira 13/14 no 20D

## 1. Resumo executivo

Esta miss?o gerou uma bateria observacional de 100 jogos no formato 20D, expandindo o n?cleo Lei 15 com 5 reservas auditadas por jogo e conferindo a bateria contra janelas oficiais de 20, 30 e 50 concursos usando a fonte institucional persistida.

- `generation_event_id`: 8
- `requested_count`: 100
- `selected_card_format`: 20
- `nucleo_lei_15_size`: 15
- `reservas_auditadas_count`: 5
- `cartao_final_size`: 20
- `accepted_games`: 100
- `valid_candidates_found`: 104
- `attempts_used`: 442
- `fill_completed`: True

Conclus?o resumida: o 20D amplia o teto de acerto, melhora a convers?o em 12+/13+ e preserva picos em 14+, mas n?o elimina a concentra??o estrutural. O desempenho m?dio sobe em rela??o ao 15D auditado, por?m a bateria ainda apresenta redund?ncia relevante e queda em bloco em parte dos jogos.

## 2. Base usada

- Bateria observacional: 100 jogos 20D gerados pelo pipeline institucional limpo e expandidos para cart?o final de 20 dezenas.
- N?cleo soberano: 15 dezenas.
- Reservas auditadas: 5 dezenas por jogo.
- Fonte oficial dos concursos: gateway institucional com leitura de `lotofacil_official_history`.
- Janelas oficiais usadas: 20 concursos (20), 30 concursos (30), 50 concursos (50).
- Cruzamentos totais no estudo principal: 100 x 50 = 5000.

### Concursos oficiais usados

- ?ltimos 20 concursos: 3683 a 3702
- ?ltimos 30 concursos: 3673 a 3702
- ?ltimos 50 concursos: 3653 a 3702

## 3. M?tricas globais por janela oficial

| Janela | Cruzamentos | 11+ | 12+ | 13+ | 14+ | 15 | M?dia | Mediana | Desvio | Melhor | Pior |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 2000 | 1902 | 1452 | 726 | 184 | 11 | 12.1375 | 12.0000 | 1.0337 | 15 | 10 |
| 30 | 3000 | 2858 | 2241 | 1161 | 333 | 31 | 12.2080 | 12.0000 | 1.0599 | 15 | 10 |
| 50 | 5000 | 4733 | 3574 | 1777 | 474 | 41 | 12.1198 | 12.0000 | 1.0544 | 15 | 10 |

### Distribui??o de hits na janela principal de 50 concursos

| Hit | Ocorr?ncias |
|---:|---:|
| 10 | 267 |
| 11 | 1159 |
| 12 | 1797 |
| 13 | 1303 |
| 14 | 433 |
| 15 | 41 |

## 4. Compara??o com a leitura hist?rica 15D

| Modelo | Cruzamentos | 11+ | 12+ | 13+ | 14+ |
|---|---:|---:|---:|---:|---:|
| 15D auditado | 1000 | 187 | 50 | 5 | 1 |
| 20D observacional | 5000 | 4733 | 3574 | 1777 | 474 |

Leitura comparativa: o 20D amplia o piso estat?stico de acertos e intensifica 12+/13+/14+ em rela??o ao 15D auditado. A leitura de 15D era mais estreita; o 20D amplia o potencial de encaixe, mas tamb?m mant?m forte concentra??o em jogos estruturalmente pr?ximos.

## 5. M?tricas por jogo

| Jogo | Score | M?dia | Mediana | Melhor | Pior | Desvio | 11+ | 12+ | 13+ | 14+ | 15 | <=10 | ?ndice alta convers?o | Redund?ncia |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 14 | 175.4549 | 12.3600 | 12.0000 | 15 | 10 | 1.1271 | 48 | 39 | 21 | 9 | 1 | 2 | 2.5000 | 0.7295 |
| 81 | 175.4549 | 12.3600 | 12.0000 | 15 | 10 | 1.1271 | 48 | 39 | 21 | 9 | 1 | 2 | 2.5000 | 0.7295 |
| 12 | 169.4427 | 12.4000 | 12.0000 | 15 | 10 | 1.0198 | 48 | 43 | 21 | 7 | 1 | 2 | 2.4200 | 0.7452 |
| 13 | 169.4427 | 12.4000 | 12.0000 | 15 | 10 | 1.0198 | 48 | 43 | 21 | 7 | 1 | 2 | 2.4200 | 0.7452 |
| 11 | 168.0474 | 12.3400 | 12.0000 | 15 | 10 | 1.0883 | 48 | 39 | 22 | 7 | 1 | 2 | 2.3800 | 0.7233 |
| 34 | 168.0474 | 12.3400 | 12.0000 | 15 | 10 | 1.0883 | 48 | 39 | 22 | 7 | 1 | 2 | 2.3800 | 0.7233 |
| 31 | 167.6872 | 12.3200 | 12.0000 | 14 | 10 | 1.1391 | 47 | 38 | 22 | 9 | 0 | 3 | 2.3600 | 0.6990 |
| 10 | 165.8331 | 12.3400 | 12.0000 | 14 | 10 | 1.1065 | 47 | 39 | 23 | 8 | 0 | 3 | 2.3400 | 0.7299 |
| 79 | 165.4208 | 12.2200 | 12.0000 | 15 | 10 | 1.1712 | 48 | 35 | 19 | 7 | 2 | 2 | 2.3400 | 0.7081 |
| 100 | 165.1843 | 12.2000 | 12.0000 | 15 | 10 | 1.2166 | 46 | 36 | 19 | 7 | 2 | 4 | 2.3600 | 0.7040 |
| 96 | 164.3627 | 12.2400 | 12.0000 | 15 | 10 | 1.1586 | 48 | 35 | 20 | 8 | 1 | 2 | 2.3000 | 0.6805 |
| 71 | 164.0882 | 12.2800 | 12.0000 | 15 | 10 | 1.0962 | 49 | 37 | 19 | 8 | 1 | 1 | 2.3000 | 0.7183 |
| 33 | 163.6745 | 12.2800 | 12.0000 | 14 | 10 | 1.1496 | 47 | 37 | 21 | 9 | 0 | 3 | 2.3000 | 0.7290 |
| 55 | 163.6745 | 12.2800 | 12.0000 | 14 | 10 | 1.1496 | 47 | 37 | 21 | 9 | 0 | 3 | 2.3000 | 0.7290 |
| 58 | 163.1871 | 12.3600 | 12.0000 | 15 | 10 | 0.9749 | 49 | 42 | 21 | 4 | 2 | 1 | 2.3200 | 0.7331 |
| 91 | 162.0109 | 12.2800 | 12.0000 | 15 | 10 | 1.0962 | 48 | 38 | 20 | 7 | 1 | 2 | 2.2800 | 0.7167 |
| 77 | 161.5678 | 12.2800 | 12.0000 | 14 | 10 | 1.1321 | 47 | 37 | 22 | 8 | 0 | 3 | 2.2600 | 0.7024 |
| 90 | 160.9251 | 12.2400 | 12.0000 | 15 | 10 | 1.1412 | 48 | 35 | 21 | 7 | 1 | 2 | 2.2600 | 0.7490 |
| 92 | 160.9251 | 12.2400 | 12.0000 | 15 | 10 | 1.1412 | 48 | 35 | 21 | 7 | 1 | 2 | 2.2600 | 0.7490 |
| 39 | 158.1195 | 12.3000 | 12.0000 | 15 | 10 | 1.0440 | 48 | 39 | 22 | 5 | 1 | 2 | 2.2200 | 0.7163 |
| 82 | 155.5324 | 12.3400 | 12.0000 | 14 | 10 | 0.9718 | 49 | 40 | 22 | 6 | 0 | 1 | 2.1600 | 0.7415 |
| 6 | 152.8235 | 12.1800 | 12.0000 | 15 | 10 | 1.1259 | 48 | 34 | 20 | 6 | 1 | 2 | 2.1200 | 0.7132 |
| 52 | 152.8235 | 12.1800 | 12.0000 | 15 | 10 | 1.1259 | 48 | 34 | 20 | 6 | 1 | 2 | 2.1200 | 0.7132 |
| 7 | 152.4559 | 12.2000 | 12.0000 | 14 | 10 | 1.1489 | 46 | 36 | 21 | 7 | 0 | 4 | 2.1200 | 0.6904 |
| 53 | 152.4559 | 12.2000 | 12.0000 | 14 | 10 | 1.1489 | 46 | 36 | 21 | 7 | 0 | 4 | 2.1200 | 0.6904 |
| 57 | 151.5439 | 12.2800 | 12.0000 | 14 | 10 | 1.0206 | 48 | 39 | 21 | 6 | 0 | 2 | 2.1000 | 0.7208 |
| 80 | 151.5439 | 12.2800 | 12.0000 | 14 | 10 | 1.0206 | 48 | 39 | 21 | 6 | 0 | 2 | 2.1000 | 0.7208 |
| 47 | 149.3579 | 12.1400 | 12.0000 | 15 | 10 | 1.1315 | 47 | 36 | 16 | 7 | 1 | 3 | 2.0800 | 0.6974 |
| 74 | 149.1590 | 12.1800 | 12.0000 | 15 | 10 | 1.0898 | 48 | 35 | 20 | 5 | 1 | 2 | 2.0600 | 0.6924 |
| 46 | 148.3279 | 12.1800 | 12.0000 | 14 | 10 | 1.1080 | 47 | 37 | 17 | 8 | 0 | 3 | 2.0600 | 0.7430 |
| 35 | 147.6130 | 12.2400 | 12.0000 | 14 | 10 | 1.0111 | 49 | 37 | 20 | 6 | 0 | 1 | 2.0200 | 0.7181 |
| 29 | 147.0622 | 12.1400 | 12.0000 | 15 | 10 | 1.1315 | 47 | 34 | 20 | 5 | 1 | 3 | 2.0400 | 0.7186 |
| 30 | 147.0622 | 12.1400 | 12.0000 | 15 | 10 | 1.1315 | 47 | 34 | 20 | 5 | 1 | 3 | 2.0400 | 0.7186 |
| 41 | 146.9324 | 12.2800 | 12.0000 | 14 | 10 | 1.0008 | 47 | 40 | 23 | 4 | 0 | 3 | 2.0400 | 0.7233 |
| 59 | 146.3277 | 12.2400 | 12.0000 | 15 | 10 | 0.9912 | 48 | 40 | 19 | 4 | 1 | 2 | 2.0400 | 0.7331 |
| 17 | 146.3266 | 12.1000 | 12.0000 | 15 | 10 | 1.1705 | 46 | 34 | 18 | 6 | 1 | 4 | 2.0400 | 0.7192 |
| 40 | 146.3266 | 12.1000 | 12.0000 | 15 | 10 | 1.1705 | 46 | 34 | 18 | 6 | 1 | 4 | 2.0400 | 0.7192 |
| 38 | 145.9702 | 12.2400 | 12.0000 | 15 | 10 | 0.9708 | 49 | 39 | 19 | 4 | 1 | 1 | 2.0200 | 0.7318 |
| 70 | 145.8590 | 12.1600 | 12.0000 | 14 | 10 | 1.0837 | 48 | 36 | 16 | 8 | 0 | 2 | 2.0000 | 0.7115 |
| 32 | 145.4124 | 12.1800 | 12.0000 | 14 | 10 | 1.0524 | 49 | 35 | 18 | 7 | 0 | 1 | 1.9800 | 0.7203 |
| 8 | 144.9991 | 12.2400 | 12.0000 | 14 | 10 | 1.0111 | 48 | 37 | 23 | 4 | 0 | 2 | 1.9800 | 0.6834 |
| 44 | 144.3496 | 12.1800 | 12.0000 | 14 | 10 | 1.0524 | 48 | 37 | 17 | 7 | 0 | 2 | 1.9800 | 0.7177 |
| 73 | 144.0738 | 12.1000 | 12.0000 | 15 | 10 | 1.1000 | 48 | 35 | 14 | 7 | 1 | 2 | 1.9800 | 0.6862 |
| 54 | 143.4148 | 12.2400 | 12.0000 | 14 | 11 | 0.9499 | 50 | 37 | 20 | 5 | 0 | 0 | 1.9400 | 0.7089 |
| 94 | 142.4814 | 12.1000 | 12.0000 | 15 | 10 | 1.1358 | 46 | 35 | 18 | 5 | 1 | 4 | 1.9800 | 0.7111 |
| 75 | 141.9748 | 12.1200 | 12.0000 | 15 | 10 | 1.0889 | 47 | 36 | 17 | 5 | 1 | 3 | 1.9600 | 0.6899 |
| 85 | 141.4549 | 12.2200 | 12.0000 | 14 | 10 | 1.0058 | 47 | 40 | 19 | 5 | 0 | 3 | 1.9600 | 0.7484 |
| 76 | 139.7849 | 12.1600 | 12.0000 | 14 | 10 | 1.0461 | 48 | 35 | 20 | 5 | 0 | 2 | 1.9000 | 0.7200 |
| 28 | 139.6539 | 12.1600 | 12.0000 | 15 | 10 | 1.0268 | 47 | 39 | 17 | 4 | 1 | 3 | 1.9400 | 0.7239 |
| 93 | 138.8531 | 12.1200 | 12.0000 | 15 | 10 | 1.0515 | 48 | 35 | 18 | 4 | 1 | 2 | 1.9000 | 0.7089 |
| 56 | 137.6209 | 12.1200 | 12.0000 | 14 | 10 | 1.0703 | 48 | 33 | 20 | 5 | 0 | 2 | 1.8600 | 0.7239 |
| 78 | 137.6209 | 12.1200 | 12.0000 | 14 | 10 | 1.0703 | 48 | 33 | 20 | 5 | 0 | 2 | 1.8600 | 0.7239 |
| 65 | 137.5097 | 12.0200 | 12.0000 | 15 | 10 | 1.1915 | 45 | 31 | 20 | 4 | 1 | 5 | 1.9000 | 0.7215 |
| 87 | 137.1918 | 12.2200 | 12.0000 | 14 | 10 | 0.9442 | 48 | 40 | 19 | 4 | 0 | 2 | 1.8800 | 0.7439 |
| 66 | 135.1807 | 12.0800 | 12.0000 | 14 | 10 | 1.0925 | 47 | 34 | 17 | 6 | 0 | 3 | 1.8400 | 0.7406 |
| 25 | 134.2231 | 12.0400 | 12.0000 | 15 | 10 | 1.1482 | 44 | 36 | 17 | 4 | 1 | 6 | 1.8800 | 0.7414 |
| 48 | 133.5823 | 12.0000 | 12.0000 | 15 | 10 | 1.1662 | 45 | 32 | 18 | 4 | 1 | 5 | 1.8400 | 0.7156 |
| 43 | 132.7462 | 12.0200 | 12.0000 | 15 | 10 | 1.0861 | 48 | 32 | 15 | 5 | 1 | 2 | 1.8000 | 0.7350 |
| 21 | 131.9926 | 12.0200 | 12.0000 | 14 | 10 | 1.1400 | 45 | 34 | 16 | 6 | 0 | 5 | 1.8000 | 0.6914 |
| 20 | 131.9164 | 12.1000 | 12.0000 | 14 | 10 | 1.0050 | 49 | 34 | 17 | 5 | 0 | 1 | 1.7600 | 0.7127 |
| 88 | 131.6659 | 12.0600 | 12.0000 | 14 | 10 | 1.0846 | 47 | 33 | 18 | 5 | 0 | 3 | 1.7800 | 0.7395 |
| 68 | 130.5201 | 12.1200 | 12.0000 | 14 | 10 | 0.9928 | 48 | 36 | 18 | 4 | 0 | 2 | 1.7600 | 0.7378 |
| 5 | 129.5179 | 12.0800 | 12.0000 | 14 | 10 | 1.0741 | 46 | 33 | 23 | 2 | 0 | 4 | 1.7400 | 0.6752 |
| 84 | 128.9997 | 12.0600 | 12.0000 | 14 | 10 | 1.0278 | 48 | 34 | 16 | 5 | 0 | 2 | 1.7200 | 0.6919 |
| 72 | 126.9637 | 12.0800 | 12.0000 | 14 | 10 | 0.9968 | 47 | 38 | 14 | 5 | 0 | 3 | 1.7200 | 0.7286 |
| 23 | 126.4467 | 12.1200 | 12.0000 | 14 | 10 | 0.9928 | 46 | 38 | 20 | 2 | 0 | 4 | 1.7200 | 0.7287 |
| 26 | 126.2199 | 12.0400 | 12.0000 | 14 | 10 | 1.0575 | 46 | 35 | 17 | 4 | 0 | 4 | 1.7000 | 0.6922 |
| 9 | 125.8540 | 12.0400 | 12.0000 | 14 | 10 | 1.0575 | 47 | 32 | 20 | 3 | 0 | 3 | 1.6800 | 0.7255 |
| 51 | 125.4319 | 12.0600 | 12.0000 | 14 | 10 | 1.0082 | 48 | 33 | 19 | 3 | 0 | 2 | 1.6600 | 0.6985 |
| 67 | 125.3808 | 12.0800 | 12.0000 | 14 | 10 | 0.9558 | 49 | 35 | 16 | 4 | 0 | 1 | 1.6600 | 0.7166 |
| 19 | 124.5899 | 12.0600 | 12.0000 | 15 | 10 | 0.9677 | 48 | 36 | 16 | 2 | 1 | 2 | 1.6800 | 0.7263 |
| 24 | 124.0512 | 12.0600 | 12.0000 | 14 | 10 | 0.9881 | 48 | 34 | 18 | 3 | 0 | 2 | 1.6400 | 0.6916 |
| 27 | 121.5108 | 12.0400 | 12.0000 | 15 | 10 | 0.9156 | 49 | 37 | 12 | 3 | 1 | 1 | 1.6200 | 0.7050 |
| 64 | 120.6923 | 12.1000 | 12.0000 | 14 | 10 | 0.9434 | 47 | 37 | 20 | 1 | 0 | 3 | 1.6200 | 0.7554 |
| 83 | 120.5245 | 11.9800 | 12.0000 | 14 | 10 | 1.0861 | 45 | 33 | 18 | 3 | 0 | 5 | 1.6200 | 0.7237 |
| 62 | 119.9802 | 11.9400 | 12.0000 | 14 | 10 | 1.1209 | 44 | 33 | 16 | 4 | 0 | 6 | 1.6200 | 0.7111 |
| 99 | 119.9064 | 12.0800 | 12.0000 | 14 | 10 | 0.9130 | 47 | 40 | 14 | 3 | 0 | 3 | 1.6000 | 0.6684 |
| 95 | 118.7314 | 12.0000 | 12.0000 | 14 | 10 | 0.9592 | 49 | 33 | 14 | 4 | 0 | 1 | 1.5400 | 0.6798 |
| 18 | 118.5329 | 11.9600 | 12.0000 | 14 | 10 | 1.0575 | 45 | 36 | 12 | 5 | 0 | 5 | 1.6000 | 0.7227 |
| 86 | 117.8516 | 11.9400 | 12.0000 | 14 | 10 | 1.0660 | 46 | 32 | 15 | 4 | 0 | 4 | 1.5600 | 0.7035 |
| 15 | 117.2504 | 11.9800 | 12.0000 | 14 | 10 | 1.0294 | 47 | 31 | 19 | 2 | 0 | 3 | 1.5400 | 0.7267 |
| 60 | 116.6332 | 12.0000 | 12.0000 | 14 | 10 | 1.0000 | 46 | 36 | 15 | 3 | 0 | 4 | 1.5600 | 0.7333 |
| 16 | 116.0003 | 12.1000 | 12.0000 | 14 | 10 | 0.8307 | 49 | 38 | 17 | 1 | 0 | 1 | 1.5200 | 0.7216 |
| 98 | 115.5015 | 12.0400 | 12.0000 | 14 | 10 | 0.8935 | 48 | 38 | 13 | 3 | 0 | 2 | 1.5200 | 0.7005 |
| 49 | 113.4241 | 11.9400 | 12.0000 | 15 | 10 | 0.9881 | 46 | 36 | 12 | 2 | 1 | 4 | 1.5200 | 0.7050 |
| 22 | 111.9783 | 11.9600 | 12.0000 | 14 | 10 | 0.9992 | 46 | 34 | 16 | 2 | 0 | 4 | 1.4800 | 0.7388 |
| 4 | 111.7578 | 12.0000 | 12.0000 | 14 | 10 | 0.8944 | 48 | 37 | 12 | 3 | 0 | 2 | 1.4600 | 0.7121 |
| 3 | 111.3420 | 11.9600 | 12.0000 | 14 | 10 | 0.9992 | 45 | 36 | 15 | 2 | 0 | 5 | 1.4800 | 0.7056 |
| 36 | 108.5556 | 11.9800 | 12.0000 | 14 | 10 | 0.9053 | 48 | 34 | 16 | 1 | 0 | 2 | 1.4000 | 0.7227 |
| 42 | 108.3797 | 11.9000 | 12.0000 | 14 | 10 | 1.0440 | 45 | 31 | 18 | 1 | 0 | 5 | 1.4200 | 0.7262 |
| 50 | 106.5678 | 11.9800 | 12.0000 | 13 | 10 | 0.8829 | 48 | 34 | 17 | 0 | 0 | 2 | 1.3600 | 0.6880 |
| 45 | 106.1499 | 11.8200 | 12.0000 | 14 | 10 | 1.0524 | 45 | 31 | 11 | 4 | 0 | 5 | 1.3800 | 0.6948 |
| 37 | 103.5300 | 11.9000 | 12.0000 | 14 | 10 | 0.9000 | 48 | 34 | 10 | 3 | 0 | 2 | 1.3200 | 0.7136 |
| 61 | 103.5300 | 11.9000 | 12.0000 | 14 | 10 | 0.9000 | 48 | 34 | 10 | 3 | 0 | 2 | 1.3200 | 0.7136 |
| 1 | 103.1849 | 11.8000 | 12.0000 | 15 | 10 | 0.9798 | 47 | 30 | 10 | 2 | 1 | 3 | 1.3200 | 0.6742 |
| 69 | 100.1002 | 11.8800 | 12.0000 | 14 | 10 | 0.8863 | 48 | 33 | 11 | 2 | 0 | 2 | 1.2600 | 0.7069 |
| 2 | 100.0312 | 11.8000 | 12.0000 | 14 | 10 | 1.0000 | 46 | 29 | 13 | 2 | 0 | 4 | 1.2600 | 0.6763 |
| 89 | 99.1680 | 11.8600 | 12.0000 | 14 | 10 | 0.8947 | 48 | 32 | 11 | 2 | 0 | 2 | 1.2400 | 0.6985 |
| 97 | 97.5381 | 11.9200 | 12.0000 | 13 | 10 | 0.8207 | 48 | 35 | 13 | 0 | 0 | 2 | 1.2200 | 0.6869 |
| 63 | 94.8997 | 11.9400 | 12.0000 | 13 | 10 | 0.7324 | 49 | 37 | 11 | 0 | 0 | 1 | 1.1800 | 0.7144 |

### Score observacional

- `score_observacional = (2 x m?dia) + (1.5 x mediana) + (1 x 12+) + (2.5 x 13+) + (5 x 14+) + (9 x 15) - (0.6 x quedas para 10 ou menos) - (1.2 x desvio padr?o) - (14 x ?ndice de redund?ncia)`
- O score ? documental e n?o operacional.

## 6. Sele??o dos 50 melhores

| Rank | Jogo | Score | Justificativa |
|---:|---:|---:|---|
| 1 | 14 | 175.4549 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 2 | 81 | 175.4549 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 3 | 12 | 169.4427 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 4 | 13 | 169.4427 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 5 | 11 | 168.0474 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 6 | 34 | 168.0474 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 7 | 31 | 167.6872 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 8 | 10 | 165.8331 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 9 | 79 | 165.4208 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 10 | 100 | 165.1843 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 11 | 96 | 164.3627 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 12 | 71 | 164.0882 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 13 | 33 | 163.6745 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 14 | 55 | 163.6745 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 15 | 58 | 163.1871 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 16 | 91 | 162.0109 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 17 | 77 | 161.5678 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 18 | 90 | 160.9251 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 19 | 92 | 160.9251 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 20 | 39 | 158.1195 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 21 | 82 | 155.5324 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 22 | 6 | 152.8235 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 23 | 52 | 152.8235 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 24 | 7 | 152.4559 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 25 | 53 | 152.4559 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 26 | 57 | 151.5439 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 27 | 80 | 151.5439 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 28 | 47 | 149.3579 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 29 | 74 | 149.1590 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 30 | 46 | 148.3279 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 31 | 35 | 147.6130 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 32 | 29 | 147.0622 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 33 | 30 | 147.0622 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 34 | 41 | 146.9324 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 35 | 59 | 146.3277 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 36 | 17 | 146.3266 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 37 | 40 | 146.3266 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 38 | 38 | 145.9702 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 39 | 70 | 145.8590 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 40 | 32 | 145.4124 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 41 | 8 | 144.9991 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 42 | 44 | 144.3496 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 43 | 73 | 144.0738 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 44 | 54 | 143.4148 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 45 | 94 | 142.4814 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 46 | 75 | 141.9748 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 47 | 85 | 141.4549 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 48 | 76 | 139.7849 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 49 | 28 | 139.6539 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 50 | 93 | 138.8531 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |

### Jogos eliminados ao sair de 100 para 50

| Jogo | Score | Motivo resumido |
|---:|---:|---|
| 56 | 137.6209 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 78 | 137.6209 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 65 | 137.5097 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 87 | 137.1918 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 66 | 135.1807 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 25 | 134.2231 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 48 | 133.5823 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 43 | 132.7462 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 21 | 131.9926 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 20 | 131.9164 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 88 | 131.6659 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 68 | 130.5201 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 5 | 129.5179 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 84 | 128.9997 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 72 | 126.9637 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 23 | 126.4467 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 26 | 126.2199 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 9 | 125.8540 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 51 | 125.4319 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 67 | 125.3808 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 19 | 124.5899 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 24 | 124.0512 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 27 | 121.5108 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 64 | 120.6923 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 83 | 120.5245 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 62 | 119.9802 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 99 | 119.9064 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 95 | 118.7314 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 18 | 118.5329 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 86 | 117.8516 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 15 | 117.2504 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 60 | 116.6332 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 16 | 116.0003 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 98 | 115.5015 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 49 | 113.4241 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 22 | 111.9783 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 4 | 111.7578 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 3 | 111.3420 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 36 | 108.5556 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 42 | 108.3797 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 50 | 106.5678 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 45 | 106.1499 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 37 | 103.5300 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 61 | 103.5300 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 1 | 103.1849 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 69 | 100.1002 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 2 | 100.0312 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 89 | 99.1680 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 97 | 97.5381 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |
| 63 | 94.8997 | score abaixo do corte e/ou redund?ncia superior ao grupo selecionado |

## 7. Sele??o dos 20 melhores

| Rank | Jogo | Score | Justificativa |
|---:|---:|---:|---|
| 1 | 14 | 175.4549 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 2 | 81 | 175.4549 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 3 | 12 | 169.4427 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 4 | 13 | 169.4427 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 5 | 11 | 168.0474 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 6 | 34 | 168.0474 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 7 | 31 | 167.6872 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 8 | 10 | 165.8331 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 9 | 79 | 165.4208 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 10 | 100 | 165.1843 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 11 | 96 | 164.3627 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 12 | 71 | 164.0882 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 13 | 33 | 163.6745 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 14 | 55 | 163.6745 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 15 | 58 | 163.1871 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 16 | 91 | 162.0109 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 17 | 77 | 161.5678 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 18 | 90 | 160.9251 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 19 | 92 | 160.9251 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 20 | 39 | 158.1195 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |

### Jogos eliminados ao sair de 50 para 20

| Jogo | Score | Motivo resumido |
|---:|---:|---|
| 82 | 155.5324 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 6 | 152.8235 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 52 | 152.8235 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 7 | 152.4559 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 53 | 152.4559 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 57 | 151.5439 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 80 | 151.5439 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 47 | 149.3579 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 74 | 149.1590 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 46 | 148.3279 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 35 | 147.6130 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 29 | 147.0622 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 30 | 147.0622 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 41 | 146.9324 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 59 | 146.3277 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 17 | 146.3266 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 40 | 146.3266 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 38 | 145.9702 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 70 | 145.8590 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 32 | 145.4124 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 8 | 144.9991 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 44 | 144.3496 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 73 | 144.0738 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 54 | 143.4148 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 94 | 142.4814 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 75 | 141.9748 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 85 | 141.4549 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 76 | 139.7849 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 28 | 139.6539 | score inferior aos 20 sobreviventes e/ou estabilidade menor |
| 93 | 138.8531 | score inferior aos 20 sobreviventes e/ou estabilidade menor |

## 8. Sele??o dos 10 melhores

| Rank | Jogo | Score | Justificativa individual |
|---:|---:|---:|---|
| 1 | 14 | 175.4549 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 2 | 81 | 175.4549 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 3 | 12 | 169.4427 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 4 | 13 | 169.4427 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 5 | 11 | 168.0474 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 6 | 34 | 168.0474 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 7 | 31 | 167.6872 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 8 | 10 | 165.8331 | 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 9 | 79 | 165.4208 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |
| 10 | 100 | 165.1843 | 15 presente; 14+ recorrente; 13+ recorrente; queda em bloco controlada |

### Compara??o entre 50, 20 e 10

- Os 10 finais concentram os maiores scores, mas mant?m estabilidade e diversidade estrutural m?nima.
- A sele??o 20 evita escolher apenas os jogos com melhor pico isolado.
- A sele??o 50 preserva a base observacional com menos redund?ncia que o conjunto bruto de 100.

## 9. Diversidade estrutural

A diversidade foi monitorada por ?ndice m?dio de Jaccard entre os cart?es finais. Jogos com redund?ncia muito alta perderam posi??o mesmo com picos pontuais de hit, porque o objetivo da sele??o progressiva ? sobreviver estatisticamente sem transformar um ?nico padr?o em regra absoluta.

| N?vel | Redund?ncia m?dia | Leitura |
|---|---:|---|
| 100 jogos | 0.7153 | base observacional ampla, por?m concentrada |
| 50 jogos | 0.7179 | redund?ncia controlada |
| 20 jogos | 0.7230 | elite observacional |
| 10 jogos | 0.7237 | elite final |

## 10. Resposta ?s perguntas institucionais

- A bateria 20D supera claramente a antiga leitura 15D? **Sim, em teto e volume de 12+/13+.**
- O 20D aumenta a convers?o para 13/14? **Sim, com mais picos de 13 e 14 que o 15D auditado.**
- Existe queda em bloco? **Sim, em parte dos jogos, e isso foi penalizado no score.**
- Existe excesso de concentra??o estrutural? **Sim, o ?ndice de redund?ncia mostra um bloco ainda concentrado.**

## 11. Conclus?o institucional

A an?lise sustenta que o 20D entrega uma cobertura estat?stica superior ao 15D auditado para fins observacionais: h? mais 12+, mais 13+ e ocorr?ncias maiores de 14, por?m a bateria ainda apresenta tend?ncia de concentra??o estrutural e n?o deve ser convertida em regra operacional. O protocolo permanece documental, observacional e subordinado ? Lei 15.

## 12. Ap?ndice ? identifica??o da bateria

| Jogo | N?cleo Lei 15 | Reservas auditadas | Cart?o final |
|---:|---|---|---|
| 1 | 01 02 05 07 08 09 10 11 14 15 18 20 21 22 25 | 04 12 16 19 17 | 01 02 04 05 07 08 09 10 11 12 14 15 16 17 18 19 20 21 22 25 |
| 2 | 01 02 03 07 08 10 11 13 14 15 18 21 22 24 25 | 04 12 16 19 17 | 01 02 03 04 07 08 10 11 12 13 14 15 16 17 18 19 21 22 24 25 |
| 3 | 01 02 03 05 07 08 11 13 14 18 20 22 23 24 25 | 04 12 15 16 19 | 01 02 03 04 05 07 08 11 12 13 14 15 16 18 19 20 22 23 24 25 |
| 4 | 01 02 05 07 08 09 10 13 14 15 20 22 23 24 25 | 11 12 16 19 21 | 01 02 05 07 08 09 10 11 12 13 14 15 16 19 20 21 22 23 24 25 |
| 5 | 01 02 05 07 08 10 13 14 15 16 17 21 22 23 24 | 12 19 09 06 18 | 01 02 05 06 07 08 09 10 12 13 14 15 16 17 18 19 21 22 23 24 |
| 6 | 01 02 03 07 08 10 14 15 17 18 20 21 23 24 25 | 16 19 13 09 05 | 01 02 03 05 07 08 09 10 13 14 15 16 17 18 19 20 21 23 24 25 |
| 7 | 01 02 03 05 07 08 10 13 15 16 17 18 22 23 24 | 19 21 09 06 14 | 01 02 03 05 06 07 08 09 10 13 14 15 16 17 18 19 21 22 23 24 |
| 8 | 02 03 05 07 08 09 10 11 13 14 20 22 23 24 25 | 19 21 17 01 06 | 01 02 03 05 06 07 08 09 10 11 13 14 17 19 20 21 22 23 24 25 |
| 9 | 01 02 05 07 08 09 10 13 15 16 18 21 22 23 24 | 17 06 14 20 25 | 01 02 05 06 07 08 09 10 13 14 15 16 17 18 20 21 22 23 24 25 |
| 10 | 02 03 05 07 08 10 11 13 14 15 18 22 23 24 25 | 17 01 09 06 20 | 01 02 03 05 06 07 08 09 10 11 13 14 15 17 18 20 22 23 24 25 |
| 11 | 01 02 03 05 08 09 10 11 13 14 18 22 23 24 25 | 17 06 20 07 04 | 01 02 03 04 05 06 07 08 09 10 11 13 14 17 18 20 22 23 24 25 |
| 12 | 01 02 03 05 07 08 10 11 13 14 15 18 22 24 25 | 23 09 06 20 04 | 01 02 03 04 05 06 07 08 09 10 11 13 14 15 18 20 22 23 24 25 |
| 13 | 01 02 03 07 09 10 11 14 15 18 20 22 23 24 25 | 13 05 06 08 04 | 01 02 03 04 05 06 07 08 09 10 11 13 14 15 18 20 22 23 24 25 |
| 14 | 01 02 03 05 07 08 10 11 13 14 18 20 22 23 25 | 09 06 24 04 12 | 01 02 03 04 05 06 07 08 09 10 11 12 13 14 18 20 22 23 24 25 |
| 15 | 01 03 05 07 08 09 10 13 15 16 18 20 21 22 24 | 06 14 25 04 11 | 01 03 04 05 06 07 08 09 10 11 13 14 15 16 18 20 21 22 24 25 |
| 16 | 01 02 03 05 07 08 10 13 15 16 17 18 20 23 24 | 06 14 25 22 04 | 01 02 03 04 05 06 07 08 10 13 14 15 16 17 18 20 22 23 24 25 |
| 17 | 01 03 05 07 08 09 10 13 14 16 18 20 23 24 25 | 06 22 04 11 12 | 01 03 04 05 06 07 08 09 10 11 12 13 14 16 18 20 22 23 24 25 |
| 18 | 01 03 04 05 07 08 09 10 13 14 15 16 20 24 25 | 18 22 11 12 19 | 01 03 04 05 07 08 09 10 11 12 13 14 15 16 18 19 20 22 24 25 |
| 19 | 01 02 03 05 07 08 10 13 16 17 18 21 22 23 24 | 14 20 25 04 11 | 01 02 03 04 05 07 08 10 11 13 14 16 17 18 20 21 22 23 24 25 |
| 20 | 01 02 03 07 08 09 10 13 15 18 20 22 23 24 25 | 04 11 12 16 19 | 01 02 03 04 07 08 09 10 11 12 13 15 16 18 19 20 22 23 24 25 |
| 21 | 01 02 03 05 07 08 10 11 14 15 20 22 23 24 25 | 04 12 16 19 21 | 01 02 03 04 05 07 08 10 11 12 14 15 16 19 20 21 22 23 24 25 |
| 22 | 01 02 03 05 07 08 10 13 14 15 18 20 21 24 25 | 22 04 11 12 16 | 01 02 03 04 05 07 08 10 11 12 13 14 15 16 18 20 21 22 24 25 |
| 23 | 01 02 03 05 07 08 10 13 14 15 16 18 21 23 24 | 25 22 04 11 12 | 01 02 03 04 05 07 08 10 11 12 13 14 15 16 18 21 22 23 24 25 |
| 24 | 01 02 03 05 07 10 11 14 15 18 20 22 23 24 25 | 04 12 16 19 21 | 01 02 03 04 05 07 10 11 12 14 15 16 18 19 20 21 22 23 24 25 |
| 25 | 01 02 03 07 08 09 10 11 13 14 18 20 23 24 25 | 22 04 12 15 16 | 01 02 03 04 07 08 09 10 11 12 13 14 15 16 18 20 22 23 24 25 |
| 26 | 01 02 05 07 08 09 10 13 16 17 20 22 23 24 25 | 04 11 12 15 19 | 01 02 04 05 07 08 09 10 11 12 13 15 16 17 19 20 22 23 24 25 |
| 27 | 01 03 07 08 09 10 13 14 15 16 18 22 23 24 25 | 11 12 19 21 02 | 01 02 03 07 08 09 10 11 12 13 14 15 16 18 19 21 22 23 24 25 |
| 28 | 01 03 05 07 08 09 10 13 14 15 18 20 22 23 24 | 12 16 19 21 02 | 01 02 03 05 07 08 09 10 12 13 14 15 16 18 19 20 21 22 23 24 |
| 29 | 01 03 05 07 08 09 10 13 14 16 17 18 22 24 25 | 15 19 21 02 23 | 01 02 03 05 07 08 09 10 13 14 15 16 17 18 19 21 22 23 24 25 |
| 30 | 01 02 03 07 08 09 10 13 14 15 18 22 23 24 25 | 16 19 21 17 05 | 01 02 03 05 07 08 09 10 13 14 15 16 17 18 19 21 22 23 24 25 |
| 31 | 01 02 03 07 08 09 10 13 15 17 18 20 22 23 24 | 19 21 05 06 14 | 01 02 03 05 06 07 08 09 10 13 14 15 17 18 19 20 21 22 23 24 |
| 32 | 01 03 05 07 08 09 10 13 15 16 18 20 22 24 25 | 21 02 17 23 06 | 01 02 03 05 06 07 08 09 10 13 15 16 17 18 20 21 22 23 24 25 |
| 33 | 01 02 03 05 07 08 10 13 15 17 18 20 21 22 24 | 23 09 06 14 25 | 01 02 03 05 06 07 08 09 10 13 14 15 17 18 20 21 22 23 24 25 |
| 34 | 01 02 03 07 08 09 10 11 13 18 20 22 23 24 25 | 17 05 06 14 04 | 01 02 03 04 05 06 07 08 09 10 11 13 14 17 18 20 22 23 24 25 |
| 35 | 01 02 05 07 08 09 10 13 14 18 20 21 23 24 25 | 06 22 04 11 12 | 01 02 04 05 06 07 08 09 10 11 12 13 14 18 20 21 22 23 24 25 |
| 36 | 01 02 05 07 08 09 10 13 15 16 17 18 20 24 25 | 06 14 22 04 11 | 01 02 04 05 06 07 08 09 10 11 13 14 15 16 17 18 20 22 24 25 |
| 37 | 01 03 07 08 09 10 13 15 16 17 18 20 21 22 24 | 05 06 14 25 04 | 01 03 04 05 06 07 08 09 10 13 14 15 16 17 18 20 21 22 24 25 |
| 38 | 01 02 03 05 07 08 09 10 14 15 16 18 23 24 25 | 06 20 22 04 11 | 01 02 03 04 05 06 07 08 09 10 11 14 15 16 18 20 22 23 24 25 |
| 39 | 02 03 05 07 08 09 10 11 13 14 18 20 23 24 25 | 06 22 04 12 15 | 02 03 04 05 06 07 08 09 10 11 12 13 14 15 18 20 22 23 24 25 |
| 40 | 01 03 05 07 08 09 10 13 16 18 20 22 23 24 25 | 06 14 04 11 12 | 01 03 04 05 06 07 08 09 10 11 12 13 14 16 18 20 22 23 24 25 |
| 41 | 01 02 03 05 08 09 10 11 14 17 20 22 23 24 25 | 18 07 04 12 15 | 01 02 03 04 05 07 08 09 10 11 12 14 15 17 18 20 22 23 24 25 |
| 42 | 01 03 05 07 08 09 10 13 15 16 17 18 20 22 24 | 14 25 04 11 12 | 01 03 04 05 07 08 09 10 11 12 13 14 15 16 17 18 20 22 24 25 |
| 43 | 01 02 03 05 07 08 09 10 14 15 16 18 21 24 25 | 20 22 04 11 12 | 01 02 03 04 05 07 08 09 10 11 12 14 15 16 18 20 21 22 24 25 |
| 44 | 01 02 03 05 07 08 10 13 15 18 20 22 23 24 25 | 04 11 12 16 19 | 01 02 03 04 05 07 08 10 11 12 13 15 16 18 19 20 22 23 24 25 |
| 45 | 02 03 07 08 09 10 11 13 14 15 18 20 21 24 25 | 22 04 12 16 19 | 02 03 04 07 08 09 10 11 12 13 14 15 16 18 19 20 21 22 24 25 |
| 46 | 01 02 03 05 07 08 09 10 14 15 18 20 23 24 25 | 22 04 11 12 16 | 01 02 03 04 05 07 08 09 10 11 12 14 15 16 18 20 22 23 24 25 |
| 47 | 01 02 05 07 08 09 10 13 15 16 17 18 20 23 24 | 22 04 11 12 19 | 01 02 04 05 07 08 09 10 11 12 13 15 16 17 18 19 20 22 23 24 |
| 48 | 02 03 05 07 08 09 10 11 13 14 15 18 20 24 25 | 22 04 12 16 19 | 02 03 04 05 07 08 09 10 11 12 13 14 15 16 18 19 20 22 24 25 |
| 49 | 01 02 03 07 08 09 10 13 15 18 20 21 22 24 25 | 04 11 12 16 19 | 01 02 03 04 07 08 09 10 11 12 13 15 16 18 19 20 21 22 24 25 |
| 50 | 01 02 05 07 08 09 10 13 14 17 20 21 22 23 24 | 11 12 15 16 19 | 01 02 05 07 08 09 10 11 12 13 14 15 16 17 19 20 21 22 23 24 |
| 51 | 01 05 07 08 09 10 13 14 15 16 18 20 23 24 25 | 12 19 21 02 17 | 01 02 05 07 08 09 10 12 13 14 15 16 17 18 19 20 21 23 24 25 |
| 52 | 01 02 03 05 07 08 10 13 14 18 20 21 23 24 25 | 15 16 19 17 09 | 01 02 03 05 07 08 09 10 13 14 15 16 17 18 19 20 21 23 24 25 |
| 53 | 01 02 03 05 07 08 09 10 13 15 16 18 22 23 24 | 19 21 17 06 14 | 01 02 03 05 06 07 08 09 10 13 14 15 16 17 18 19 21 22 23 24 |
| 54 | 01 03 04 05 07 09 10 14 15 17 18 20 22 24 25 | 19 21 02 23 13 | 01 02 03 04 05 07 09 10 13 14 15 17 18 19 20 21 22 23 24 25 |
| 55 | 01 02 03 07 08 09 10 13 14 15 18 20 23 24 25 | 21 17 05 06 22 | 01 02 03 05 06 07 08 09 10 13 14 15 17 18 20 21 22 23 24 25 |
| 56 | 01 03 07 08 09 10 13 14 16 17 18 20 21 23 24 | 02 05 06 25 22 | 01 02 03 05 06 07 08 09 10 13 14 16 17 18 20 21 22 23 24 25 |
| 57 | 01 02 03 05 07 08 10 13 17 18 20 21 22 23 24 | 09 06 14 25 04 | 01 02 03 04 05 06 07 08 09 10 13 14 17 18 20 21 22 23 24 25 |
| 58 | 01 02 03 07 08 10 11 13 14 18 21 22 23 24 25 | 09 05 06 20 04 | 01 02 03 04 05 06 07 08 09 10 11 13 14 18 20 21 22 23 24 25 |
| 59 | 01 02 03 05 07 08 09 10 13 15 18 20 22 24 25 | 06 14 04 11 12 | 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 18 20 22 24 25 |
| 60 | 01 02 05 07 08 09 10 13 15 16 20 21 22 24 25 | 06 14 18 04 11 | 01 02 04 05 06 07 08 09 10 11 13 14 15 16 18 20 21 22 24 25 |
| 61 | 01 03 05 07 08 10 13 15 16 17 18 20 21 22 24 | 09 06 14 25 04 | 01 03 04 05 06 07 08 09 10 13 14 15 16 17 18 20 21 22 24 25 |
| 62 | 01 03 05 07 08 09 10 13 14 16 18 20 21 24 25 | 06 22 04 11 12 | 01 03 04 05 06 07 08 09 10 11 12 13 14 16 18 20 21 22 24 25 |
| 63 | 01 02 03 05 07 08 10 13 15 16 17 18 20 21 24 | 06 14 25 22 04 | 01 02 03 04 05 06 07 08 10 13 14 15 16 17 18 20 21 22 24 25 |
| 64 | 01 02 05 07 08 09 10 13 14 15 16 18 21 23 24 | 20 25 22 04 11 | 01 02 04 05 07 08 09 10 11 13 14 15 16 18 20 21 22 23 24 25 |
| 65 | 01 03 05 07 08 09 10 13 14 16 17 18 20 23 24 | 25 22 04 11 12 | 01 03 04 05 07 08 09 10 11 12 13 14 16 17 18 20 22 23 24 25 |
| 66 | 01 02 03 05 07 08 09 10 13 15 16 20 21 22 24 | 18 25 04 11 12 | 01 02 03 04 05 07 08 09 10 11 12 13 15 16 18 20 21 22 24 25 |
| 67 | 01 02 05 07 09 10 11 13 14 18 20 22 23 24 25 | 04 12 15 16 19 | 01 02 04 05 07 09 10 11 12 13 14 15 16 18 19 20 22 23 24 25 |
| 68 | 01 02 05 07 08 09 10 13 18 20 21 22 23 24 25 | 04 11 12 15 16 | 01 02 04 05 07 08 09 10 11 12 13 15 16 18 20 21 22 23 24 25 |
| 69 | 01 02 03 04 05 07 10 13 14 15 17 18 20 21 24 | 25 22 11 12 16 | 01 02 03 04 05 07 10 11 12 13 14 15 16 17 18 20 21 22 24 25 |
| 70 | 01 02 03 05 07 08 09 10 13 14 15 16 20 23 24 | 22 04 11 12 19 | 01 02 03 04 05 07 08 09 10 11 12 13 14 15 16 19 20 22 23 24 |
| 71 | 01 02 03 05 07 08 09 10 13 15 18 20 22 23 24 | 04 11 12 16 19 | 01 02 03 04 05 07 08 09 10 11 12 13 15 16 18 19 20 22 23 24 |
| 72 | 01 03 05 07 08 09 10 13 14 18 20 21 22 23 24 | 04 11 12 15 16 | 01 03 04 05 07 08 09 10 11 12 13 14 15 16 18 20 21 22 23 24 |
| 73 | 01 02 03 05 07 08 10 13 14 15 18 21 22 23 24 | 11 12 16 19 17 | 01 02 03 05 07 08 10 11 12 13 14 15 16 17 18 19 21 22 23 24 |
| 74 | 01 02 03 07 08 09 10 13 14 16 17 18 23 24 25 | 12 15 19 21 05 | 01 02 03 05 07 08 09 10 12 13 14 15 16 17 18 19 21 23 24 25 |
| 75 | 01 02 05 07 08 10 13 14 15 18 20 21 23 24 25 | 16 19 17 09 06 | 01 02 05 06 07 08 09 10 13 14 15 16 17 18 19 20 21 23 24 25 |
| 76 | 01 03 05 07 08 09 10 15 16 18 20 21 22 24 25 | 19 02 17 23 13 | 01 02 03 05 07 08 09 10 13 15 16 17 18 19 20 21 22 23 24 25 |
| 77 | 01 02 03 05 07 08 09 10 13 14 17 20 22 24 25 | 19 21 23 06 18 | 01 02 03 05 06 07 08 09 10 13 14 17 18 19 20 21 22 23 24 25 |
| 78 | 01 03 05 07 08 09 10 13 16 18 20 21 22 24 25 | 02 17 23 06 14 | 01 02 03 05 06 07 08 09 10 13 14 16 17 18 20 21 22 23 24 25 |
| 79 | 01 02 07 08 09 10 11 13 14 17 18 22 23 24 25 | 05 06 20 04 12 | 01 02 04 05 06 07 08 09 10 11 12 13 14 17 18 20 22 23 24 25 |
| 80 | 01 02 03 07 08 09 10 13 14 17 18 21 22 23 24 | 05 06 20 25 04 | 01 02 03 04 05 06 07 08 09 10 13 14 17 18 20 21 22 23 24 25 |
| 81 | 01 02 03 05 07 08 09 10 11 13 14 18 20 22 25 | 23 06 24 04 12 | 01 02 03 04 05 06 07 08 09 10 11 12 13 14 18 20 22 23 24 25 |
| 82 | 01 02 03 05 07 08 10 13 14 15 18 20 21 23 24 | 09 06 25 22 04 | 01 02 03 04 05 06 07 08 09 10 13 14 15 18 20 21 22 23 24 25 |
| 83 | 01 03 04 05 07 08 09 10 13 15 18 20 22 24 25 | 06 14 11 12 16 | 01 03 04 05 06 07 08 09 10 11 12 13 14 15 16 18 20 22 24 25 |
| 84 | 01 02 05 07 08 09 10 14 15 17 18 20 21 24 25 | 06 22 04 11 12 | 01 02 04 05 06 07 08 09 10 11 12 14 15 17 18 20 21 22 24 25 |
| 85 | 01 02 03 05 07 08 09 10 13 15 16 18 20 23 24 | 06 14 25 22 04 | 01 02 03 04 05 06 07 08 09 10 13 14 15 16 18 20 22 23 24 25 |
| 86 | 01 03 04 05 07 08 09 10 14 15 18 20 21 24 25 | 06 22 11 12 16 | 01 03 04 05 06 07 08 09 10 11 12 14 15 16 18 20 21 22 24 25 |
| 87 | 01 02 05 07 08 09 10 13 14 15 18 20 21 23 24 | 25 22 04 11 12 | 01 02 04 05 07 08 09 10 11 12 13 14 15 18 20 21 22 23 24 25 |
| 88 | 01 02 05 07 08 09 10 13 16 18 20 21 23 24 25 | 14 22 04 11 12 | 01 02 04 05 07 08 09 10 11 12 13 14 16 18 20 21 22 23 24 25 |
| 89 | 01 02 03 07 09 10 11 13 14 15 18 20 22 24 25 | 04 12 16 19 21 | 01 02 03 04 07 09 10 11 12 13 14 15 16 18 19 20 21 22 24 25 |
| 90 | 01 02 03 05 07 08 09 10 13 16 18 22 23 24 25 | 20 04 11 12 15 | 01 02 03 04 05 07 08 09 10 11 12 13 15 16 18 20 22 23 24 25 |
| 91 | 01 02 03 05 07 08 09 10 12 13 18 22 23 24 25 | 04 11 15 16 19 | 01 02 03 04 05 07 08 09 10 11 12 13 15 16 18 19 22 23 24 25 |
| 92 | 01 02 03 05 07 08 09 10 13 18 20 22 23 24 25 | 04 11 12 15 16 | 01 02 03 04 05 07 08 09 10 11 12 13 15 16 18 20 22 23 24 25 |
| 93 | 01 02 03 05 07 08 09 10 13 16 18 21 22 24 25 | 04 11 12 15 19 | 01 02 03 04 05 07 08 09 10 11 12 13 15 16 18 19 21 22 24 25 |
| 94 | 01 02 05 07 08 09 10 13 16 17 18 20 21 23 24 | 22 04 11 12 15 | 01 02 04 05 07 08 09 10 11 12 13 15 16 17 18 20 21 22 23 24 |
| 95 | 01 02 03 05 07 08 09 10 13 15 16 17 20 22 24 | 04 11 12 19 21 | 01 02 03 04 05 07 08 09 10 11 12 13 15 16 17 19 20 21 22 24 |
| 96 | 01 02 03 05 07 08 10 13 14 16 17 18 21 23 24 | 11 12 15 19 09 | 01 02 03 05 07 08 09 10 11 12 13 14 15 16 17 18 19 21 23 24 |
| 97 | 01 02 05 07 10 11 13 14 15 18 20 22 23 24 25 | 12 16 19 21 17 | 01 02 05 07 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 |
| 98 | 01 02 03 05 07 10 11 13 14 15 18 20 22 24 25 | 16 19 21 17 23 | 01 02 03 05 07 10 11 13 14 15 16 17 18 19 20 21 22 23 24 25 |
| 99 | 01 02 03 04 05 07 09 10 13 14 15 20 21 22 24 | 16 19 17 23 06 | 01 02 03 04 05 06 07 09 10 13 14 15 16 17 19 20 21 22 23 24 |
| 100 | 01 02 07 08 09 10 13 14 15 17 20 21 22 24 25 | 19 23 05 06 18 | 01 02 05 06 07 08 09 10 13 14 15 17 18 19 20 21 22 23 24 25 |
