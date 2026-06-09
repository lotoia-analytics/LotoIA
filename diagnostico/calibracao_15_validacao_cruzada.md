# Validacao cruzada da calibracao 15 dezenas

## Escopo

- Batch analisado: `calibration-20260602105229-26a52ff8`
- Regra usada: `validation_threshold = 11`
- Faixa valida: `11_to_15`
- Fonte dos concursos: historico oficial local em `data/raw/historico_lotofacil.csv`
- Fonte dos jogos: memoria consolidada do batch em `data/data/corrupted/lotoia_20260602T131721.db`
- Sem gerar nova bateria
- Sem alterar banco
- Sem alterar memorias

## Resumo executivo

O padr�o de 15 dezenas se sustenta em mais de uma janela hist�rica.

- Ha `12+` nos ultimos `10`, `30` e `60` concursos oficiais.
- O batch ja produziu:
  - `12+` em `6` dos ultimos `10` concursos
  - `12+` em `18` dos ultimos `30` concursos
  - `12+` em `29` dos ultimos `60` concursos
- Ha `13+` tambem nas tres janelas, embora com menor densidade.

Conclusao operacional:

- A base principal da proxima calibracao deve sair dos jogos `12+` e, em segundo plano, dos jogos `13+`.
- Os jogos de `11` continuam relevantes, mas agora como piso de referencia, nao como destino final.

## Janelas historicas

| Janela | total_games_checked | average_best_hits | max_best_hits | count_11_exact | count_12_exact | count_13_exact | count_14_exact | count_15_exact | count_11_plus | count_12_plus | count_13_plus | count_14_plus | count_15 | contests_with_11_plus | contests_with_12_plus | contests_with_13_plus |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Ultimos 10 | 900 | 11.6 | 13 | 151 | 32 | 4 | 0 | 0 | 187 | 36 | 4 | 0 | 0 | 9 | 6 | 1 |
| Ultimos 30 | 2700 | 11.7333 | 13 | 408 | 110 | 17 | 0 | 0 | 535 | 127 | 17 | 0 | 0 | 29 | 18 | 5 |
| Ultimos 60 | 5400 | 11.55 | 13 | 688 | 150 | 23 | 0 | 0 | 861 | 173 | 23 | 0 | 0 | 58 | 29 | 6 |

## Respostas objetivas

### 1. Esses nucleos aparecem tambem nos melhores jogos contra outros concursos?

Sim.

Nos jogos de melhor desempenho em `11+` e `12+`, o nucleo continua aparecendo com forca:

- `10`
- `18`
- `1`
- `6`
- `11`
- `21`
- `9`
- `20`

Leitura curta:

- `10`, `18`, `1` e `6` aparecem com muita estabilidade.
- `11`, `21` e `9` continuam presentes, mas com mais variacao.
- `20` aparece como apoio forte, embora oscile mais nas janelas.

### 2. Os buracos 16/17/14/7 continuam sendo recorrentes?

Sim.

Na janela de `60`, entre os melhores jogos `11+`, os buracos continuam presentes como ausencias recorrentes:

- `16` -> 22 ausencias
- `17` -> 14 ausencias
- `14` -> 10 ausencias
- `7` -> 11 ausencias

Nos melhores jogos `12+`, eles ainda aparecem, mas com menor peso:

- `16` -> 6 ausencias
- `17` -> 4 ausencias
- `14` -> 5 ausencias
- `7` -> 8 ausencias

Leitura:

- Eles continuam relevantes.
- Mas nos jogos `12+` a pressao desses buracos cai.
- Nos jogos `13+`, quase todos ficam resolvidos.

### 3. Os extras 24/2/15/8 continuam atrapalhando?

Sim, mas com nuance.

Nos melhores jogos `11+` da janela de `60`, esses extras aparecem com frequencia alta como ruido de composicao:

- `24` -> 17 vezes
- `15` -> 18 vezes
- `8` -> 17 vezes
- `2` -> 12 vezes

Porem, nos jogos `12+` eles nao sao simplesmente ruins:

- `24` continua muito presente como componente de jogo forte
- `15` e `8` tambem aparecem tanto como apoio quanto como excesso
- `2` aparece com freciencia moderada e pode ser mantido com controle

Conclusao:

- O problema nao e banir esses numeros.
- O problema e nao deixa-los dominar a estrutura.
- Eles precisam perder prioridade quando competem com a recuperacao dos buracos.

### 4. Existe algum concurso da janela em que esse batch ja bate 12+?

Sim. Em todas as janelas.

#### Ultimos 10 concursos

Concursos com melhor jogo `12+`:

- `3687` -> `12`
- `3690` -> `12`
- `3691` -> `12`
- `3692` -> `12`
- `3695` -> `12`
- `3697` -> `13`

#### Ultimos 30 concursos

Concursos com melhor jogo `12+`:

- `3668`, `3670`, `3673`, `3674`, `3676`, `3678`, `3679`, `3680`, `3681`, `3682`, `3685`, `3686`, `3687`, `3690`, `3691`, `3692`, `3695`, `3697`

#### Ultimos 60 concursos

Concursos com melhor jogo `12+`:

- `3638`, `3640`, `3645`, `3646`, `3648`, `3649`, `3653`, `3656`, `3659`, `3661`, `3663`, `3668`, `3670`, `3673`, `3674`, `3676`, `3678`, `3679`, `3680`, `3681`, `3682`, `3685`, `3686`, `3687`, `3690`, `3691`, `3692`, `3695`, `3697`

### 5. Se sim, quais jogos, quais numeros e quais padroes geraram 12+?

Padrao dominante dos jogos `12+` na janela de `60`:

- manter o nucleo forte `10 / 18 / 6 / 11 / 1 / 9`
- manter apoio de `24 / 15 / 8 / 2 / 3 / 5`
- aceitar `7` e `14` como recuperacoes pontuais
- evitar concentrar demais `20` e `24` ao mesmo tempo sem cobertura dos buracos

Exemplos recorrentes de composicao vencedora:

- `1, 3, 6, 7, 8, 10, 11, 15, 18, 19, 20, 24, 25`
- `1, 2, 4, 5, 6, 9, 10, 11, 13, 14, 15, 18, 19, 20, 24`
- `2, 3, 5, 6, 8, 9, 10, 11, 13, 15, 18, 19, 20, 24, 25`
- `1, 2, 3, 5, 6, 8, 9, 10, 13, 15, 17, 18, 20, 21, 24`
- `1, 2, 5, 6, 8, 9, 10, 13, 15, 17, 18, 19, 20, 24, 25`

Para `13+`, o padrao fica mais seletivo:

- `10` e `24` seguem fortes
- `18` e `6` continuam relevantes
- `17` aparece quando a grade resolve melhor os buracos
- o excesso de ruido cai

### 6. Se nao mostrar 12+, qual ajuste e mais provavel para empurrar de 11 para 12?

Mas mostrou `12+`, entao a resposta correta e:

- o ajuste nao deve abandonar os jogos `11`
- deve dar prioridade aos jogos `12+` como referencia principal
- deve usar os `11` como piso de estabilidade

Mesmo assim, o ajuste mais provavel para subir de `11` para `12` e:

- preservar `10, 18, 1, 6` como nucleo duro
- manter `11, 21, 9, 20` como anel de sustentacao
- reduzir a dependencia excessiva de `24`, `15`, `8`, `2`, `3`, `5`
- forcar a reconstrucao de pelo menos um dos buracos:
  - `16`
  - `17`
  - `14`
  - `7`

## Leitura de sustentacao

### Nucleo forte

Na janela de `60`, entre os melhores jogos `11+`, o nucleo segue forte:

- `10` -> 46 presencas
- `18` -> 35 presencas
- `6` -> 37 presencas
- `11` -> 34 presencas
- `1` -> 33 presencas
- `20` -> 33 presencas
- `21` -> 31 presencas
- `9` -> 20 presencas

Nos `12+`, o nucleo segue presente e com boa aderencia.

### Buracos recorrentes

- `16`, `17`, `14` e `7` continuam aparecendo, mas o aumento de qualidade para `12+` reduz a pressao desses buracos.

### Extras que diluem

- `24`, `15`, `8`, `2`, `3` e `5` continuam aparecendo como excesso de composicao.
- Eles nao devem ser proibidos.
- Devem perder prioridade quando competem com a recuperacao dos buracos.

## Conclusao operacional

O batch `calibration-20260602105229-26a52ff8` nao esta preso em `11`.
Ele ja valida `12+` em tres janelas historicas e produz `13+` de forma ocasional.

Portanto, a proxima calibracao deve:

- usar os jogos `12+` como referencia principal
- usar os jogos `13+` como referencia de refinamento
- manter os jogos `11` como piso de estabilidade
- reduzir ruido estrutural sem desmontar o nucleo

