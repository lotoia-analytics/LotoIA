# Auditoria de robustez dos 50 jogos 15D contra últimos 10/20 concursos

## Resumo executivo

Auditoria observacional executada sobre a bateria de 50 jogos 15D informada na missão como exportação `2026-06-07T11-41_export.csv`. O arquivo CSV não foi localizado no workspace; por isso, a bateria usada foi exatamente a lista de 50 jogos colada na solicitação.

Foram usados os concursos oficiais disponíveis em `lotofacil_official_history`, a base institucional persistida. A janela de 20 concursos vai de 3683 a 3702. A janela de 10 concursos vai de 3693 a 3702.

Conclusão objetiva: o resultado "50 jogos com 10 acertos" não parece ser regra estrutural permanente; foi um caso de janela/concurso específico. A bateria não fica presa apenas em 10, mas concentra muito em 9/10. Contra os últimos 20 concursos houve 187 ocorrências de 11+, 50 ocorrências de 12+ e 5 ocorrências de 13+. A robustez é classificada como **Suspeito**: há capacidade de 11/12 e alguns 13/14, mas a diversidade estrutural é limitada porque os jogos se movem em bloco e possuem dezenas hiperconcentradas.

## Tarefa 1 - Carga dos 50 jogos

- Total de jogos carregados: 50
- Todos com 15 dezenas válidas: sim
- Duplicados exatos: 0
- Assinatura/hash usado: dezenas ordenadas em formato `NN NN ... NN`

### Frequência das dezenas na bateria

| Dezena | Frequência |
|---:|---:|
| 01 | 36 |
| 02 | 49 |
| 03 | 43 |
| 04 | 1 |
| 05 | 44 |
| 06 | 0 |
| 07 | 34 |
| 08 | 32 |
| 09 | 44 |
| 10 | 37 |
| 11 | 13 |
| 12 | 0 |
| 13 | 50 |
| 14 | 28 |
| 15 | 32 |
| 16 | 37 |
| 17 | 21 |
| 18 | 50 |
| 19 | 0 |
| 20 | 50 |
| 21 | 22 |
| 22 | 35 |
| 23 | 29 |
| 24 | 31 |
| 25 | 32 |

Leitura de diversidade: 13, 18 e 20 aparecem em todos os 50 jogos; 02 aparece em 49. As dezenas 06, 12 e 19 não aparecem. Isso indica forte concentração estrutural.

## Tarefa 2 - Concursos oficiais usados

Últimos 10 concursos oficiais: 3693, 3694, 3695, 3696, 3697, 3698, 3699, 3700, 3701, 3702.

Últimos 20 concursos oficiais: 3683, 3684, 3685, 3686, 3687, 3688, 3689, 3690, 3691, 3692, 3693, 3694, 3695, 3696, 3697, 3698, 3699, 3700, 3701, 3702.

Fonte: `lotofacil_official_history`.

## Tarefa 3 - Matriz resumida de hits

Matriz dos últimos 10 concursos. Colunas: 3693, 3694, 3695, 3696, 3697, 3698, 3699, 3700, 3701, 3702.

| Jogo | 3693 | 3694 | 3695 | 3696 | 3697 | 3698 | 3699 | 3700 | 3701 | 3702 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 8 | 10 | 10 | 8 | 8 | 10 | 11 | 10 | 9 | 13 |
| 2 | 9 | 10 | 10 | 10 | 10 | 10 | 11 | 8 | 8 | 12 |
| 3 | 7 | 11 | 12 | 10 | 9 | 10 | 10 | 9 | 9 | 12 |
| 4 | 9 | 10 | 11 | 9 | 10 | 11 | 9 | 9 | 9 | 12 |
| 5 | 8 | 10 | 9 | 9 | 9 | 11 | 9 | 10 | 9 | 12 |
| 6 | 10 | 10 | 9 | 9 | 9 | 12 | 10 | 10 | 9 | 12 |
| 7 | 8 | 10 | 9 | 9 | 10 | 9 | 11 | 9 | 9 | 10 |
| 8 | 8 | 10 | 11 | 10 | 9 | 11 | 11 | 9 | 8 | 12 |
| 9 | 10 | 11 | 9 | 10 | 9 | 11 | 9 | 10 | 9 | 13 |
| 10 | 9 | 10 | 10 | 9 | 11 | 9 | 10 | 8 | 9 | 11 |
| 11 | 9 | 9 | 9 | 7 | 9 | 9 | 12 | 10 | 9 | 11 |
| 12 | 8 | 10 | 10 | 11 | 10 | 12 | 9 | 9 | 8 | 11 |
| 13 | 10 | 10 | 10 | 9 | 11 | 10 | 8 | 9 | 9 | 10 |
| 14 | 8 | 10 | 12 | 10 | 9 | 11 | 10 | 9 | 9 | 11 |
| 15 | 11 | 9 | 8 | 8 | 10 | 11 | 11 | 10 | 9 | 12 |
| 16 | 9 | 9 | 10 | 10 | 11 | 11 | 9 | 9 | 8 | 10 |
| 17 | 8 | 10 | 11 | 11 | 10 | 11 | 9 | 9 | 8 | 12 |
| 18 | 8 | 10 | 9 | 10 | 10 | 11 | 9 | 10 | 9 | 11 |
| 19 | 9 | 9 | 10 | 10 | 10 | 11 | 10 | 9 | 8 | 12 |
| 20 | 9 | 10 | 10 | 8 | 10 | 9 | 10 | 10 | 11 | 9 |
| 21 | 10 | 10 | 10 | 10 | 12 | 10 | 9 | 8 | 9 | 11 |
| 22 | 9 | 9 | 10 | 8 | 9 | 8 | 11 | 10 | 10 | 11 |
| 23 | 10 | 8 | 9 | 8 | 10 | 11 | 11 | 10 | 8 | 12 |
| 24 | 9 | 10 | 8 | 8 | 9 | 10 | 11 | 11 | 10 | 9 |
| 25 | 10 | 9 | 9 | 8 | 10 | 7 | 10 | 10 | 10 | 10 |
| 26 | 8 | 11 | 10 | 9 | 9 | 11 | 11 | 10 | 10 | 11 |
| 27 | 10 | 10 | 8 | 9 | 10 | 10 | 12 | 10 | 9 | 10 |
| 28 | 7 | 11 | 11 | 10 | 9 | 11 | 10 | 9 | 9 | 11 |
| 29 | 9 | 11 | 8 | 8 | 9 | 9 | 10 | 10 | 10 | 11 |
| 30 | 10 | 10 | 8 | 9 | 10 | 11 | 10 | 11 | 10 | 11 |
| 31 | 9 | 9 | 10 | 8 | 10 | 10 | 10 | 10 | 9 | 12 |
| 32 | 9 | 10 | 10 | 11 | 11 | 10 | 9 | 8 | 8 | 12 |
| 33 | 10 | 9 | 9 | 8 | 10 | 9 | 13 | 9 | 9 | 11 |
| 34 | 9 | 10 | 9 | 8 | 9 | 10 | 12 | 11 | 10 | 10 |
| 35 | 11 | 9 | 10 | 8 | 10 | 11 | 10 | 11 | 10 | 11 |
| 36 | 9 | 11 | 8 | 9 | 9 | 10 | 11 | 11 | 10 | 10 |
| 37 | 10 | 9 | 8 | 8 | 10 | 10 | 10 | 10 | 9 | 12 |
| 38 | 9 | 9 | 9 | 8 | 9 | 10 | 9 | 11 | 9 | 12 |
| 39 | 10 | 12 | 9 | 9 | 10 | 9 | 10 | 10 | 11 | 12 |
| 40 | 10 | 8 | 9 | 8 | 10 | 10 | 11 | 9 | 8 | 13 |
| 41 | 8 | 10 | 10 | 9 | 10 | 10 | 11 | 9 | 9 | 11 |
| 42 | 8 | 11 | 10 | 11 | 10 | 11 | 8 | 10 | 9 | 11 |
| 43 | 9 | 10 | 9 | 10 | 10 | 10 | 8 | 10 | 9 | 11 |
| 44 | 9 | 10 | 9 | 8 | 9 | 9 | 12 | 10 | 10 | 11 |
| 45 | 9 | 9 | 9 | 9 | 10 | 11 | 10 | 9 | 8 | 12 |
| 46 | 11 | 11 | 8 | 7 | 10 | 9 | 11 | 11 | 11 | 10 |
| 47 | 9 | 11 | 10 | 10 | 9 | 12 | 9 | 10 | 9 | 12 |
| 48 | 10 | 11 | 9 | 9 | 10 | 9 | 11 | 10 | 10 | 12 |
| 49 | 10 | 11 | 10 | 8 | 8 | 10 | 10 | 12 | 11 | 12 |
| 50 | 9 | 11 | 10 | 9 | 8 | 10 | 11 | 10 | 9 | 14 |

## Tarefa 4 - Métricas por concurso

### Últimos 20 concursos

| Concurso | Data | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | Melhor | Média | Mediana | Desvio | 11+ | 12+ | 13+ |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3683 | 12/05/2026 | 1 | 5 | 22 | 15 | 5 | 2 | 0 | 0 | 0 | 12 | 9.48 | 9.0 | 1.00 | 7 | 2 | 0 |
| 3684 | 13/05/2026 | 2 | 16 | 23 | 9 | 0 | 0 | 0 | 0 | 0 | 10 | 8.78 | 9.0 | 0.78 | 0 | 0 | 0 |
| 3685 | 14/05/2026 | 14 | 15 | 15 | 6 | 0 | 0 | 0 | 0 | 0 | 10 | 8.26 | 8.0 | 1.00 | 0 | 0 | 0 |
| 3686 | 15/05/2026 | 1 | 10 | 13 | 23 | 3 | 0 | 0 | 0 | 0 | 11 | 9.34 | 10.0 | 0.93 | 3 | 0 | 0 |
| 3687 | 16/05/2026 | 3 | 12 | 25 | 9 | 1 | 0 | 0 | 0 | 0 | 11 | 8.86 | 9.0 | 0.85 | 1 | 0 | 0 |
| 3688 | 18/05/2026 | 25 | 15 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 7.26 | 7.0 | 0.82 | 0 | 0 | 0 |
| 3689 | 19/05/2026 | 0 | 6 | 18 | 17 | 9 | 0 | 0 | 0 | 0 | 11 | 9.58 | 10.0 | 0.92 | 9 | 0 | 0 |
| 3690 | 20/05/2026 | 2 | 11 | 21 | 12 | 4 | 0 | 0 | 0 | 0 | 11 | 9.10 | 9.0 | 0.96 | 4 | 0 | 0 |
| 3691 | 21/05/2026 | 0 | 1 | 8 | 17 | 15 | 9 | 0 | 0 | 0 | 12 | 10.46 | 10.0 | 1.02 | 24 | 9 | 0 |
| 3692 | 22/05/2026 | 0 | 3 | 10 | 21 | 13 | 3 | 0 | 0 | 0 | 12 | 10.06 | 10.0 | 0.97 | 16 | 3 | 0 |
| 3693 | 23/05/2026 | 2 | 11 | 20 | 14 | 3 | 0 | 0 | 0 | 0 | 11 | 9.10 | 9.0 | 0.94 | 3 | 0 | 0 |
| 3694 | 25/05/2026 | 0 | 2 | 12 | 23 | 12 | 1 | 0 | 0 | 0 | 12 | 9.96 | 10.0 | 0.85 | 13 | 1 | 0 |
| 3695 | 26/05/2026 | 0 | 8 | 17 | 19 | 4 | 2 | 0 | 0 | 0 | 12 | 9.50 | 9.5 | 0.98 | 6 | 2 | 0 |
| 3696 | 27/05/2026 | 2 | 17 | 15 | 12 | 4 | 0 | 0 | 0 | 0 | 11 | 8.98 | 9.0 | 1.03 | 4 | 0 | 0 |
| 3697 | 28/05/2026 | 0 | 3 | 17 | 25 | 4 | 1 | 0 | 0 | 0 | 12 | 9.66 | 10.0 | 0.79 | 5 | 1 | 0 |
| 3698 | 29/05/2026 | 1 | 1 | 10 | 18 | 17 | 3 | 0 | 0 | 0 | 12 | 10.16 | 10.0 | 1.01 | 20 | 3 | 0 |
| 3699 | 30/05/2026 | 0 | 3 | 11 | 16 | 15 | 4 | 1 | 0 | 0 | 13 | 10.18 | 10.0 | 1.11 | 20 | 5 | 1 |
| 3700 | 01/06/2026 | 0 | 4 | 15 | 23 | 7 | 1 | 0 | 0 | 0 | 12 | 9.72 | 10.0 | 0.87 | 8 | 1 | 0 |
| 3701 | 02/06/2026 | 0 | 10 | 25 | 11 | 4 | 0 | 0 | 0 | 0 | 11 | 9.18 | 9.0 | 0.84 | 4 | 0 | 0 |
| 3702 | 03/06/2026 | 0 | 0 | 2 | 8 | 17 | 19 | 3 | 1 | 0 | 14 | 11.32 | 11.0 | 1.01 | 40 | 23 | 4 |

### Distribuição global dos 1000 cruzamentos da janela 20

| Hits | Ocorrências |
|---:|---:|
| 5 | 1 |
| 6 | 6 |
| 7 | 53 |
| 8 | 153 |
| 9 | 302 |
| 10 | 298 |
| 11 | 137 |
| 12 | 45 |
| 13 | 4 |
| 14 | 1 |
| 15 | 0 |

Totais globais:

- 11+: 187
- 12+: 50
- 13+: 5

## Tarefa 5 - Métricas por jogo

| Jogo | Média 10 | Média 20 | Melhor | Pior | 11+ | 12+ | 13+ | Estabilidade | Classe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 9.70 | 9.35 | 13 | 6 | 3 | 1 | 1 | 1.46 | forte |
| 2 | 9.80 | 9.30 | 12 | 7 | 2 | 1 | 0 | 1.19 | fraco |
| 3 | 9.90 | 9.30 | 12 | 7 | 3 | 2 | 0 | 1.35 | forte |
| 4 | 9.90 | 9.25 | 12 | 6 | 3 | 1 | 0 | 1.34 | médio |
| 5 | 9.60 | 9.45 | 12 | 6 | 5 | 1 | 0 | 1.43 | médio |
| 6 | 10.00 | 9.40 | 12 | 7 | 2 | 2 | 0 | 1.28 | forte |
| 7 | 9.40 | 9.55 | 11 | 7 | 5 | 0 | 0 | 1.16 | médio |
| 8 | 9.90 | 9.65 | 12 | 7 | 5 | 2 | 0 | 1.28 | forte |
| 9 | 10.10 | 9.35 | 13 | 7 | 3 | 1 | 1 | 1.46 | forte |
| 10 | 9.60 | 9.05 | 11 | 7 | 3 | 0 | 0 | 1.16 | médio |
| 11 | 9.40 | 9.45 | 12 | 6 | 4 | 1 | 0 | 1.32 | médio |
| 12 | 9.80 | 9.75 | 12 | 7 | 6 | 2 | 0 | 1.34 | forte |
| 13 | 9.60 | 9.00 | 11 | 7 | 1 | 0 | 0 | 0.95 | fraco |
| 14 | 9.90 | 9.25 | 12 | 7 | 3 | 1 | 0 | 1.22 | médio |
| 15 | 9.90 | 9.40 | 12 | 7 | 4 | 1 | 0 | 1.24 | médio |
| 16 | 9.60 | 9.40 | 11 | 8 | 2 | 0 | 0 | 0.73 | fraco |
| 17 | 9.90 | 9.65 | 12 | 7 | 5 | 2 | 0 | 1.31 | forte |
| 18 | 9.70 | 9.80 | 12 | 7 | 7 | 2 | 0 | 1.36 | forte |
| 19 | 9.80 | 9.65 | 12 | 7 | 4 | 2 | 0 | 1.24 | forte |
| 20 | 9.60 | 9.40 | 11 | 6 | 2 | 0 | 0 | 1.11 | fraco |
| 21 | 9.90 | 9.25 | 12 | 8 | 2 | 1 | 0 | 1.09 | fraco |
| 22 | 9.50 | 9.35 | 11 | 6 | 4 | 0 | 0 | 1.24 | médio |
| 23 | 9.70 | 9.65 | 12 | 7 | 4 | 2 | 0 | 1.28 | forte |
| 24 | 9.50 | 9.70 | 11 | 8 | 6 | 0 | 0 | 1.10 | médio |
| 25 | 9.30 | 9.05 | 10 | 7 | 0 | 0 | 0 | 0.92 | fraco |
| 26 | 10.00 | 9.50 | 11 | 7 | 4 | 0 | 0 | 1.16 | médio |
| 27 | 9.80 | 9.90 | 12 | 8 | 4 | 3 | 0 | 1.14 | forte |
| 28 | 9.80 | 9.40 | 11 | 7 | 4 | 0 | 0 | 1.28 | médio |
| 29 | 9.50 | 9.50 | 11 | 5 | 5 | 0 | 0 | 1.43 | médio |
| 30 | 10.00 | 9.80 | 12 | 8 | 6 | 1 | 0 | 1.17 | médio |
| 31 | 9.70 | 9.30 | 12 | 7 | 1 | 1 | 0 | 1.00 | fraco |
| 32 | 9.80 | 9.30 | 12 | 7 | 3 | 1 | 0 | 1.23 | médio |
| 33 | 9.70 | 9.50 | 13 | 8 | 3 | 1 | 1 | 1.16 | forte |
| 34 | 9.80 | 9.90 | 12 | 7 | 6 | 2 | 0 | 1.26 | forte |
| 35 | 10.10 | 9.25 | 11 | 8 | 4 | 0 | 0 | 1.13 | médio |
| 36 | 9.80 | 9.95 | 12 | 7 | 7 | 3 | 0 | 1.32 | forte |
| 37 | 9.60 | 9.35 | 12 | 7 | 2 | 1 | 0 | 1.24 | fraco |
| 38 | 9.50 | 9.40 | 12 | 7 | 4 | 1 | 0 | 1.24 | médio |
| 39 | 10.20 | 9.35 | 12 | 7 | 3 | 2 | 0 | 1.28 | forte |
| 40 | 9.60 | 9.30 | 13 | 7 | 3 | 1 | 1 | 1.31 | forte |
| 41 | 9.60 | 9.40 | 11 | 7 | 3 | 0 | 0 | 1.16 | médio |
| 42 | 9.90 | 9.70 | 11 | 7 | 7 | 0 | 0 | 1.23 | médio |
| 43 | 9.60 | 9.40 | 11 | 7 | 3 | 0 | 0 | 1.02 | médio |
| 44 | 9.70 | 9.55 | 12 | 7 | 4 | 1 | 0 | 1.16 | médio |
| 45 | 9.60 | 9.40 | 12 | 7 | 4 | 1 | 0 | 1.28 | médio |
| 46 | 9.90 | 9.45 | 11 | 7 | 5 | 0 | 0 | 1.20 | médio |
| 47 | 10.10 | 9.40 | 12 | 7 | 3 | 2 | 0 | 1.32 | forte |
| 48 | 10.10 | 9.35 | 12 | 7 | 3 | 1 | 0 | 1.19 | médio |
| 49 | 10.20 | 9.25 | 12 | 7 | 4 | 2 | 0 | 1.41 | forte |
| 50 | 10.10 | 9.35 | 14 | 7 | 4 | 1 | 1 | 1.56 | forte |

Melhor jogo da bateria: jogo 36, média 20 = 9.95, melhor hit = 12, 11+ em 7 concursos, 12+ em 3 concursos.

Pior jogo da bateria: jogo 13, média 20 = 9.00, melhor hit = 11, 11+ em 1 concurso, 12+ em 0 concursos.

Jogos estruturalmente fracos isoláveis nesta janela: 2, 13, 16, 20, 21, 25, 31, 37.

## Tarefa 6 - Diagnóstico de robustez

1. O resultado "50 jogos com 10 acertos" foi caso isolado?
   Sim. Na janela de 20 concursos, os 1000 cruzamentos produziram ampla distribuição: 5 a 14 hits. O concurso 3700 concentrou muitos 10, mas 3702 produziu 40 jogos com 11+.

2. Esses 50 jogos costumam ficar presos em 10?
   Parcialmente. Há concentração forte em 9/10: 302 ocorrências de 9 e 298 de 10. Ainda assim, houve 187 ocorrências de 11+.

3. A bateria gera 11/12 com frequência em outros concursos?
   Sim, mas irregularmente. Houve 137 ocorrências de 11 e 45 de 12 na janela de 20 concursos.

4. Aparece algum 13 contra os últimos 10/20 concursos?
   Sim. Houve 4 ocorrências de 13 e 1 ocorrência de 14 na janela de 20 concursos. Nos últimos 10, o concurso 3699 gerou 1 jogo com 13 e o concurso 3702 gerou 3 jogos com 13 e 1 jogo com 14.

5. Existem jogos consistentemente melhores dentro da bateria?
   Sim. O jogo 36 foi o melhor por média de 20 concursos. Também se destacam 27, 34, 18, 30 e 12 por média e presença em 11+/12+.

6. Existem jogos estruturalmente fracos que deveriam ser isolados?
   Sim, em modo observacional: 2, 13, 16, 20, 21, 25, 31 e 37.

7. A bateria tem diversidade real ou os jogos caem juntos?
   A diversidade é limitada. A média dos desvios por concurso ficou em 0.93, indicando que os jogos se movem próximos uns dos outros. A frequência fixa de 13, 18 e 20 em 100% dos jogos reforça concentração estrutural.

8. A concentração estrutural observada prejudica a cobertura?
   Sim, parcialmente. Ela ajuda estabilidade em certos concursos, mas aumenta queda conjunta quando o concurso se afasta da assinatura dominante, como no concurso 3688.

9. O núcleo 15D está robusto, suspeito ou fraco nessa janela?
   Suspeito. Não é fraco, pois gera 11/12 e alguns 13/14. Também não é plenamente robusto, pois concentra demais e oscila em bloco.

## Conclusão institucional

A bateria 15D não deve ser reprovada como obsoleta, mas também não deve ser tomada como robusta. O resultado de todos com 10 acertos foi um caso isolado/concurso-específico. A janela de 20 concursos prova que a bateria tem capacidade de produzir 11+, 12+ e 13+, inclusive um 14, mas a concentração estrutural reduz a cobertura lateral e cria risco de queda coletiva.

Classificação final: **Suspeito**.

Recomendação: manter observacional. Não alterar geração, Lei 15, RFE, OutputCommander, conferência operacional, gateway oficial, schema ou histórico. Qualquer evolução deve permanecer como auditoria futura, com validação temporal e benchmarking.

