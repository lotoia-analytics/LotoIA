# Auditoria Estratégica 15D - Inventário e conversão 11/12 para 13/14

## 1. Resumo executivo

Foram encontrados 387 registros brutos 15D nas fontes internas analisadas. Após deduplicação por assinatura ordenada de dezenas, a base auditável `base_15d_auditada` ficou com 144 jogos únicos 15D.

Do total deduplicado, 43 linhas jogo-concurso possuem resultado oficial associado para cálculo de hits e 101 permanecem sem conferência auditável. A distribuição real de hits observada foi: 7=1, 8=8, 9=16, 10=9, 11=5, 12=3, 15=1.

Conclusão objetiva: há evidência parcial de vazamento lateral por herança alta do concurso anterior e sobras herdadas recorrentes. Não há evidência forte de cegueira lateral na amostra conferida atual. A hipótese mais compatível é troca fina observacional entre sobra recorrente e faltante viva, mantendo tudo em auditoria retrospectiva.

## 2. Inventário completo dos jogos 15D

- Total bruto de registros 15D encontrados: 387
- Total após deduplicação: 144
- Quantidade de jogos conferidos: 43
- Quantidade de jogos sem conferência: 101
- Gerações cobertas: 1, 2, 3, 4, 5, 383
- Concursos cobertos: 3690, 3700, 3702
- Distribuição de hits: 7=1, 8=8, 9=16, 10=9, 11=5, 12=3, 13=0, 14=0, 15=1
- Jogos com 11: 5
- Jogos com 12: 3
- Jogos com 13: 0

### Totais por generation_event_id

- 1: 52
- 2: 50
- 3: 10
- 4: 20
- 5: 10
- 383: 1
- sem_generation_event_id: 1

### Totais por fonte

- `db:data/lotoia.db:generated_games`: 140
- `db:data/lotoia.db:generation_events.generated_games`: 140
- `db:data/lotoia.db:reconciliation_games`: 45
- `db:tmp_lotoia_test.db:generated_games`: 2
- `db:tmp_lotoia_test.db:generation_events.generated_games`: 2
- `json:reports/snapshots/*generation_snapshot*.json`: 58

### Totais por concurso conferido

- Concurso 3690: 2
- Concurso 3700: 30
- Concurso 3702: 11

### Fontes consultadas

- `data/lotoia.db`
- `lotoia.db`
- `tmp_lotoia_test.db`
- `data/shared_backend_validation.db`
- `data/user_panel_expansion.db`
- `audit/runs_dump.json`
- `audit_full/runs_dump.json`
- `reports/snapshots/*generation_snapshot*.json`

Observação de integridade: arquivos em `data/**/corrupted/*.db` foram identificados como fontes arquivadas/corrompidas e não foram misturados à base auditável.

## 3. Base auditável de trabalho

A base `base_15d_auditada` foi montada somente com jogos 15D válidos, deduplicados por assinatura das 15 dezenas. Cada registro consolidou:

- `game_id`
- `generation_event_id`
- `contest_id`
- `previous_contest_id`
- `dezenas_15d`
- `resultado_oficial`
- `resultado_anterior`
- `hits`
- `matched_numbers`
- `faltantes`
- `sobrando`
- `previous_overlap_count`
- `previous_overlap_numbers`
- `new_vs_previous_count`
- `new_vs_previous_numbers`
- fontes e ocorrências originais

## 4. Herança do concurso anterior

- Faixa média de herança do 15D: 9,63 dezenas
- Faixa mais comum: 10 dezenas herdadas
- Distribuição geral: 8=10, 9=9, 10=14, 11=7, 12=3
- Faixa nos jogos de 11: média 9,20; moda 10; distribuição 8=1, 9=2, 10=2
- Faixa nos jogos de 12: média 9,00; moda 10; distribuição 8=1, 9=1, 10=1
- Faixa nos jogos de 13: sem amostra conferida

Resposta institucional:

- Existe herança excessiva: parcialmente sim, porque a média 9,63 e moda 10 são altas e não se traduziram em 13/14.
- Existe renovação insuficiente: parcialmente, sobretudo quando a nova camada não compensa as sobras herdadas.
- Existe renovação errada: parcialmente, porque faltantes vivas aparecem fora do núcleo enquanto sobras herdadas permanecem.

## 5. Auditoria dos jogos de 11

- Top sobras dos jogos de 11: 10(5), 24(4), 07(3), 08(3), 01(1), 04(1), 03(1), 11(1), 23(1)
- Top faltantes dos jogos de 11: 17(4), 21(3), 14(3), 25(3), 15(1), 23(1), 22(1), 20(1), 05(1), 09(1)
- Faltantes que estavam no concurso anterior: 14
- Faltantes ausentes do concurso anterior: 6
- Sobras que vieram do concurso anterior: 20 de 20
- A LotoIA repete dezenas que deveriam morrer: sinal parcial, pois todas as sobras dos jogos de 11 vieram do concurso anterior.
- A LotoIA ignora dezenas que costumam voltar: sinal parcial, pois 14 faltantes dos jogos de 11 estavam no concurso anterior.

Simulação retrospectiva:

- Jogos de 11 que virariam 12 com uma troca ideal: 5
- Jogos de 11 que virariam 13 com duas trocas ideais: 5
- Jogos de 11 que poderiam virar 14 com três trocas ideais: 5

Trocas mais recorrentes nos jogos de 11:

- 10 -> 17: 4
- 24 -> 17: 4
- 10 -> 21: 3
- 07 -> 14: 3
- 07 -> 17: 3
- 07 -> 25: 3
- 08 -> 14: 3
- 08 -> 17: 3
- 08 -> 25: 3
- 10 -> 14: 3
- 10 -> 25: 3
- 24 -> 14: 3

## 6. Auditoria dos jogos de 12

- Top sobras dos jogos de 12: 08(3), 10(3), 24(3)
- Top faltantes dos jogos de 12: 20(2), 14(2), 25(2), 16(1), 17(1), 23(1)
- Faltantes que estavam no concurso anterior: 6
- Faltantes ausentes do concurso anterior: 3
- Sobras que vieram do concurso anterior: 9 de 9
- Assinatura comum dos jogos de 12: erro residual pequeno, com três sobras recorrentes fortes e faltantes concentradas.

Simulação retrospectiva:

- Uma troca teria convertido jogos de 12 em 13: 3
- Duas trocas teriam convertido jogos de 12 em 14: 3

Trocas ideais recorrentes nos jogos de 12:

- 08 -> 20: 2
- 10 -> 20: 2
- 24 -> 20: 2
- 08 -> 14: 2
- 08 -> 25: 2
- 10 -> 14: 2
- 10 -> 25: 2
- 24 -> 14: 2
- 24 -> 25: 2
- 08 -> 16: 1
- 08 -> 17: 1
- 10 -> 16: 1

Existe padrão claro de sobra morta versus faltante viva: sim, de forma parcial e retrospectiva. As sobras 08, 10 e 24 aparecem em todos os jogos de 12, enquanto 20, 14 e 25 concentram faltantes.

## 7. Comparação dos jogos de 13 contra jogos de 11/12

Não houve jogos de 13 na base conferida atual. Portanto:

- Assinatura estrutural dos jogos de 13: inconclusiva.
- Dezenas herdadas dos jogos de 13: sem amostra.
- Dezenas novas dos jogos de 13: sem amostra.
- Sobras dos 13: sem amostra.
- Faltantes dos 13: sem amostra.
- O 13 nasceu por melhor herança, renovação ou equilíbrio: não mensurável nesta base.
- Existe assinatura replicável: não, por ausência de amostra conferida com 13.

A comparação possível é indireta: os jogos de 11/12 indicam que pequenas trocas retrospectivas seriam suficientes para 13/14, mas isso usa conhecimento do resultado oficial e não pode virar regra operacional sem validação temporal.

## 8. Vazamento lateral e cegueira lateral

Indício de vazamento lateral: parcial.

Sinais:

- Média de herança de 9,63 dezenas.
- Moda de 10 dezenas herdadas.
- Todas as sobras dos jogos de 11 vieram do concurso anterior.
- Todas as sobras dos jogos de 12 vieram do concurso anterior.

Indício de cegueira lateral: não forte.

Sinais:

- Faltantes dos jogos de 11 presentes no concurso anterior: 14.
- Faltantes dos jogos de 11 ausentes do concurso anterior: 6.
- Faltantes dos jogos de 12 presentes no concurso anterior: 6.
- Faltantes dos jogos de 12 ausentes do concurso anterior: 3.

Classificação dos sinais:

- Herança alta sem ganho proporcional: Suspeito.
- Sobras herdadas recorrentes: Suspeito.
- Faltantes ausentes do concurso anterior: Compatível, mas não dominante.
- Núcleo usando concurso anterior como muleta: Suspeito.
- Cegueira lateral por ignorar dezenas novas: Conflitante na amostra atual, porque a maioria das faltantes estava no concurso anterior.

## 9. Simulação retrospectiva de estratégias, sem aplicar

| Estratégia | Melhorou | Piorou | Preservou | Destruiria/excluiria | Classificação | Risco institucional |
|---|---:|---:|---:|---:|---|---|
| A - limite máximo de herdadas | 0 | 0 | 33 | 10 | Suspeito | Alto se virar regra automática; aceitável como auditoria |
| B - limite mínimo de herdadas | 0 | 0 | 24 | 19 | Suspeito | Alto se virar regra automática; aceitável como auditoria |
| C - equilíbrio herdadas/novas | 0 | 0 | 30 | 13 | Compatível | Médio; depende de walk-forward |
| D - remoção de sobrando recorrente | 37 | 1 | 5 | 0 | Suspeito | Alto; usa resultado retrospectivo |
| E - inclusão de faltante recorrente | 41 | 1 | 1 | 0 | Suspeito | Alto; usa resultado retrospectivo |
| F - troca fina recorrente | 37 | 1 | 5 | 0 | Compatível | Médio/alto; só como hipótese auditada |
| G - preservação da assinatura dos jogos de 13 | 0 | 0 | 0 | 0 | Obsoleto | Sem amostra de 13 |
| H - controle de repetição estrutural interna | 0 | 0 | 43 | 0 | Compatível | Baixo como observação; não comanda geração |

Conversões medidas por troca ideal:

- 11 -> 12 com uma troca: 5
- 11 -> 13 com duas trocas: 5
- 12 -> 13 com uma troca: 3
- 12 -> 14 com duas trocas: 3
- 13 preservados por assinatura: 0

## 10. Pergunta soberana da auditoria

O 15D está preso em 11/12 porque:

- A) Herda demais do concurso anterior: parcialmente sim.
- B) Herda as dezenas erradas: sim, sinal suspeito.
- C) Renova pouco: parcialmente.
- D) Renova errado: parcialmente.
- E) Descarta dezenas vivas cedo demais: suspeito, porque várias faltantes estavam no concurso anterior.
- F) Mantém dezenas mortas tempo demais: sim, sinal suspeito nas sobras herdadas.
- G) Repete estrutura interna demais: não mensurado como causa principal nesta base.
- H) Falta uma troca fina observacional: sim, hipótese mais compatível.
- I) Não há evidência suficiente: há evidência parcial, mas ainda insuficiente para regra.

Resposta objetiva: o 15D mostra trava em 11/12 por combinação de herança alta, herança errada e ausência de troca fina observacional. A evidência é suficiente para auditoria futura, não para comando de geração.

## 11. Ranking das trocas ideais mais recorrentes

- Remover 10 -> incluir 17: 5 ocorrências retrospectivas
- Remover 24 -> incluir 17: 5 ocorrências retrospectivas
- Remover 08 -> incluir 14: 5 ocorrências retrospectivas
- Remover 08 -> incluir 25: 5 ocorrências retrospectivas
- Remover 10 -> incluir 14: 5 ocorrências retrospectivas
- Remover 10 -> incluir 25: 5 ocorrências retrospectivas
- Remover 24 -> incluir 14: 5 ocorrências retrospectivas
- Remover 24 -> incluir 25: 5 ocorrências retrospectivas
- Remover 08 -> incluir 17: 4 ocorrências retrospectivas
- Remover 10 -> incluir 21: 3 ocorrências retrospectivas
- Remover 07 -> incluir 14: 3 ocorrências retrospectivas
- Remover 07 -> incluir 17: 3 ocorrências retrospectivas
- Remover 07 -> incluir 25: 3 ocorrências retrospectivas
- Remover 08 -> incluir 20: 3 ocorrências retrospectivas
- Remover 10 -> incluir 20: 3 ocorrências retrospectivas
- Remover 24 -> incluir 20: 3 ocorrências retrospectivas
- Remover 10 -> incluir 23: 2 ocorrências retrospectivas
- Remover 24 -> incluir 21: 2 ocorrências retrospectivas
- Remover 24 -> incluir 23: 2 ocorrências retrospectivas
- Remover 01 -> incluir 15: 1 ocorrência retrospectiva

## 12. Regra candidata, riscos e recomendação

Regra candidata, apenas para auditoria futura:

- observar sobras herdadas recorrentes;
- observar faltantes recorrentes que estavam no concurso anterior;
- simular troca fina entre sobra herdada recorrente e faltante viva;
- validar somente por walk-forward temporal e benchmark científico.

Riscos institucionais:

- As trocas são retrospectivas e usam conhecimento do resultado oficial.
- A amostra conferida tem 43 linhas jogo-concurso, com 5 jogos de 11, 3 jogos de 12 e nenhum jogo de 13.
- Qualquer uso operacional sem walk-forward criaria risco de ajuste ex-post.
- Lei 15, Lei 16, RFE, OutputCommander, geração, conferência operacional, reservas auditadas, gateway oficial, schema, painel gerador e painel de conferência não foram alterados.

Classificação final: Suspeito.

Recomendação: manter observacional; liberar como regra candidata para auditoria futura somente se houver validação temporal e benchmark. Não aplicar em geração, não recalibrar Lei 15 e não alterar histórico.

