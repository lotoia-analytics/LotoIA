# Politica Cientifica Aplicada 15 vNext

## Escopo

- Somente `15 dezenas`
- Sem nova bateria
- Sem mexer em `17/18`
- Sem alterar memorias anteriores

## Taxonomia oficial

- `requested_games`: quantidade solicitada
- `generated_candidates` / `valid_individual_games`: quantidade candidata observada
- `natural_approvable_candidate = true`: jogos individuais validos, mas pacote final incompleto
- `candidate_reason = valid_individual_games_but_incomplete_requested_package`
- `blocked_reason = nao_atingiu_quantidade_solicitada`
- `approved_total < requested_total`: pacote bloqueado por nao atingir o pedido oficial
- quantidade natural aprovada: so existe quando `requested_games = generated/persisted_games` e o `OutputCommander` aprova o conjunto

## Base valida

- Batch principal: `calibration-20260602105229-26a52ff8`
- Regra: `validation_threshold = 11`
- Faixa: `target_band = 11_to_15`
- Direcao da proxima calibracao:
  - referencia principal: jogos `12+`
  - refinamento: jogos `13+`
  - piso de estabilidade: jogos `11`

## Janelas cruzadas

### Ultimos 10 concursos

- `total_games_checked = 900`
- `average_best_hits = 11.6`
- `max_best_hits = 13`
- `count_11_exact = 151`
- `count_12_exact = 32`
- `count_13_exact = 4`
- `count_14_exact = 0`
- `count_15_exact = 0`
- `count_11_plus = 187`
- `count_12_plus = 36`
- `count_13_plus = 4`
- `count_14_plus = 0`
- `count_15 = 0`
- `contests_with_11_plus = 9`
- `contests_with_12_plus = 6`
- `contests_with_13_plus = 1`

### Ultimos 30 concursos

- `total_games_checked = 2700`
- `average_best_hits = 11.7333`
- `max_best_hits = 13`
- `count_11_exact = 408`
- `count_12_exact = 110`
- `count_13_exact = 17`
- `count_14_exact = 0`
- `count_15_exact = 0`
- `count_11_plus = 535`
- `count_12_plus = 127`
- `count_13_plus = 17`
- `count_14_plus = 0`
- `count_15 = 0`
- `contests_with_11_plus = 29`
- `contests_with_12_plus = 18`
- `contests_with_13_plus = 5`

### Ultimos 60 concursos

- `total_games_checked = 5400`
- `average_best_hits = 11.55`
- `max_best_hits = 13`
- `count_11_exact = 688`
- `count_12_exact = 150`
- `count_13_exact = 23`
- `count_14_exact = 0`
- `count_15_exact = 0`
- `count_11_plus = 861`
- `count_12_plus = 173`
- `count_13_plus = 23`
- `count_14_plus = 0`
- `count_15 = 0`
- `contests_with_11_plus = 58`
- `contests_with_12_plus = 29`
- `contests_with_13_plus = 6`

## Jogos 12+ encontrados

### Ultimos 10 concursos

- `3687` -> `12`
- `3690` -> `12`
- `3691` -> `12`
- `3692` -> `12`
- `3695` -> `12`
- `3697` -> `13`

### Ultimos 30 concursos

- `3668`, `3670`, `3673`, `3674`, `3676`, `3678`, `3679`, `3680`, `3681`, `3682`, `3685`, `3686`, `3687`, `3690`, `3691`, `3692`, `3695`, `3697`

### Ultimos 60 concursos

- `3638`, `3640`, `3645`, `3646`, `3648`, `3649`, `3653`, `3656`, `3659`, `3661`, `3663`, `3668`, `3670`, `3673`, `3674`, `3676`, `3678`, `3679`, `3680`, `3681`, `3682`, `3685`, `3686`, `3687`, `3690`, `3691`, `3692`, `3695`, `3697`

## Jogos 13+ encontrados

### Ultimos 10 concursos

- `3697` -> `13`

### Ultimos 30 concursos

- `3668`, `3674`, `3678`, `3686`, `3697`

### Ultimos 60 concursos

- `3638`, `3668`, `3674`, `3678`, `3686`, `3697`

## Frequencia das dezenas nos jogos 12+

Top frequencias no cruzamento de `12+`:

- `10` -> 23
- `15` -> 22
- `24` -> 22
- `8` -> 21
- `18` -> 20
- `2` -> 18
- `3` -> 18
- `6` -> 18
- `11` -> 18
- `1` -> 17
- `25` -> 17
- `19` -> 16
- `21` -> 16
- `5` -> 16
- `20` -> 15

## Frequencia das dezenas nos jogos 13+

Top frequencias no cruzamento de `13+`:

- `10` -> 6
- `24` -> 6
- `2` -> 5
- `6` -> 5
- `8` -> 5
- `18` -> 5
- `15` -> 4
- `19` -> 4
- `20` -> 4
- `25` -> 4
- `1` -> 4
- `5` -> 4
- `3` -> 3
- `7` -> 3
- `11` -> 3

## Comparacao com o nucleo anterior de 11

Nucleo anterior:

- `1, 10, 18, 20, 9, 11, 6, 21`

Leitura cruzada:

- `10`, `18`, `6`, `11`, `1`, `20`, `21` continuam muito fortes
- `9` continua presente, mas nao e o eixo mais forte da subida para `12+`
- `24` nao era nucleo anterior, mas e um apoio forte e recorrente em `12+/13+`
- `15`, `8`, `2`, `3` e `5` sobem bastante em `12+` e `13+`

## Classificacao objetiva

### core_numbers_to_preserve

- `1`
- `6`
- `9`
- `10`
- `11`
- `18`
- `20`
- `21`

### numbers_to_promote

- `24`
- `15`
- `8`
- `2`
- `3`
- `5`
- `13`
- `14`
- `17`
- `7`
- `19`
- `25`

### neutral_numbers

- `4`
- `12`
- `16`
- `22`
- `23`

### noisy_numbers_to_reduce

- `2`
- `3`
- `5`
- `8`

### forbidden_numbers

- nenhum

## Reavaliacao dos buracos

### `16`

- Continua sendo o buraco mais duro.
- Aparece pouco nos jogos fortes.
- Nao deve ser promovido como correcao principal.
- Deve ser monitorado como ausente recorrente.

### `17`

- Aparece com mais consistencia nos jogos `12+` e `13+`.
- Pode ser promovido de forma controlada.

### `14`

- Tambem aparece em jogos fortes.
- Deve ser promovido com controle.

### `7`

- Continua sendo buraco real em parte dos jogos, mas aparece em `12+` e `13+`.
- Deve ser promovido com controle, nao vetado.

## Reavaliacao dos extras e ruidos

### `24`

- Muito frequente em `12+` e `13+`.
- Nao deve ser vetado.
- Deve sair de "extra ruinoso" para "apoio forte controlado".

### `15`

- Tambem aparece com forca nas janelas cruzadas.
- Nao deve ser vetado.
- Deve ser controlado para nao dominar o jogo sozinho.

### `8`

- Forte em `12+` e `13+`, mas ainda pode virar excesso.
- Deve ser peso de apoio, nao centro da politica.

### `2`, `3`, `5`

- Entram muito nos jogos fortes, mas tambem aparecem como diluicao.
- Devem ter prioridade reduzida quando competem com a recuperacao dos buracos.

## Politica Cientifica Aplicada 15 vNext

- `validation_threshold = 11`
- `target_band = 11_to_15`
- `current_target = 12_plus`
- `secondary_target = 13_plus`
- `memory_role = strong_support`
- `dominant_memory = conditional`
- `policy_mode = hybrid_15_towards_12_plus`

## O que sobe de peso

- `10`, `18`, `6`, `11`, `1`, `20`, `21`
- `24`
- `15`
- `8`
- `2`, `3`, `5`
- `17`, `14`, `7`

## O que cai de peso

- excesso de `24` quando vier desacompanhado do nucleo
- excesso de `15` quando virar concentracao
- excesso de `8`, `2`, `3`, `5` quando nao houver recuperacao dos buracos
- a ideia de usar `11` como alvo final

## O que fica fixo

- a regua `11_to_15`
- o piso de validacao em `11`
- o nucleo `1, 10, 18, 20, 9, 11, 6, 21`
- a separacao entre validacao minima, forte, muito forte e maximo

## O que deve ser monitorado

- `16`
- `17`
- `14`
- `7`
- o equilibrio entre `24/15/8` e o nucleo
- a transicao de `11` para `12+`

## Restricoes intocaveis

- nao voltar para `11+` generico como regra universal
- nao relaxar a faixa de validacao por tamanho de jogo
- nao tratar `10` como validacao principal em `15`
- nao mexer em `17/18`
- nao gerar nova bateria agora

## Expansao controlada permitida

- reforcar `12+` sem desmontar `11`
- promover `17`, `14` e `7` se ajudarem a subir a faixa
- manter `24` e `15` como apoio forte, nao como veto
- reduzir `2`, `3`, `5`, `8` apenas quando estiverem competindo com o nucleo

## Efeito esperado

- manter a estabilidade minima em `11`
- aumentar a incidencia de `12+`
- preservar caminho para `13+`
- evitar que o batch fique preso numa comemoracao de baixo valor para 15 dezenas

## Riscos

- hiperajuste ao padrao dos ultimos concursos
- excesso de peso em `24` e `15`
- perda de cobertura dos buracos reais se o nucleo for solto demais
- reducao exagerada de `2/3/5/8` que pode cortar bons caminhos

## Prontidao

- `readiness_to_generate_next_15_batch: true`
- `policy_validation_status = VALIDATED_15_POLICY_LEVEL_3`
- `official_15_search_standard = true`
- `policy_mode = hybrid_15_towards_12_plus`
- `highest_validated_hit = 13`
