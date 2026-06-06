# Diagnóstico de calibração - 15 dezenas

## Escopo

- Foco exclusivo em `game_size = 15`
- Sem tocar em 17/18
- Sem gerar nova bateria
- Fonte analisada em modo leitura: `data/data/corrupted/lotoia_20260602T131721.db`

## Régua válida

- `validation_threshold = 11`
- `target_band = 11_to_15`

## 1. Memória principal e memória condicional

### Principal

- `scientific_batch_reconciliation`
- `batch_id = calibration-20260602105229-26a52ff8`
- `memory_id = 34`
- Leitura institucional:
  - `best_hit = 11`
  - `count_11_plus = 11`
  - `count_12_plus = 0`
  - `count_13_plus = 0`
  - `count_14_plus = 0`
  - `count_15 = 0`
  - `scientific_classification = NEAR_MISS_GLOBAL`
  - `recommended_action = recalibrate_from_near_miss_towards_15`

### Condicional

- `scientific_reconciliation` da mesma linha de calibração 15, especialmente o registro com:
  - `best_hit = 11`
  - `count_11_plus = 3`
  - `recommended_action = preserve_and_push_towards_12_plus`
- Este é o melhor candidato para guiar a expansão controlada em direção a `12+`

## 2. Batches que entram como evidência

- `calibration-20260602105229-26a52ff8`
  - bateria consolidada atual
  - `total_games_checked = 90`
  - `generation_event_ids = [28, 27, 29, 32, 30, 25, 33, 31, 26]`
- `calibration-20260602003007-665ca6b4`
  - batch anterior usado como base na cadeia de política
  - aparece em `based_on_batch_id` da memória de batch anterior
- Evidência interna mais forte para a leitura atual:
  - os 9 eventos de geração do batch atual
  - os 90 jogos da `near_miss_generation_ranking`

## 3. `cross_validation_summary` usado

- O resumo efetivo é o da memória de `scientific_batch_reconciliation` do batch atual
- Campos centrais:
  - `scientific_score = 94.7971`
  - `confidence_level = LOW_TO_MEDIUM`
  - `requires_cross_validation = true`
  - `contest_scope = BATCH_CONSOLIDATED`
  - `scientific_score_components.count_11_plus = 11`
  - `scientific_score_components.total_games_checked = 90`

## 4. Dezenas mais fortes nos jogos de 11

Frequência de presença nos 11 jogos que bateram `11`:

- `1` -> 11
- `10` -> 11
- `18` -> 11
- `20` -> 11
- `9` -> 10
- `11` -> 10
- `6` -> 9
- `21` -> 9
- `13` -> 8
- `4` -> 7
- `25` -> 7

Leitura:

- O núcleo de sustentação do 11 está em `1, 10, 18, 20`
- O segundo anel mais estável está em `9, 11, 6, 21`
- `13`, `4` e `25` entram como reforço útil, mas não são tão estáveis quanto o núcleo

## 5. Dezenas que faltaram nos jogos de 11

Frequência de ausência nos jogos de `11`:

- `16` -> 8
- `17` -> 8
- `14` -> 6
- `7` -> 5
- `25` -> 4
- `4` -> 4
- `13` -> 3
- `6` -> 2
- `21` -> 2
- `11` -> 1
- `9` -> 1

Leitura:

- O principal buraco recorrente está em `16` e `17`
- Depois vêm `14` e `7`
- Isso sugere que o 11 está sendo produzido sem completar a camada final de cobertura desses números

## 6. Extras que mais atrapalham

Frequência de extras nos jogos de `11`:

- `24` -> 9
- `2` -> 8
- `15` -> 7
- `8` -> 6
- `3` -> 5
- `5` -> 4
- `23` -> 2
- `22` -> 2
- `12` -> 1

Leitura:

- `24` é o extra mais persistente
- `2`, `15` e `8` também aparecem como diluição recorrente
- O bloco `3/5/23/22` aparece como ruído secundário

## 7. Padrões que diferenciam os jogos de 11 dos abaixo da zona

### Estrutura média

- Jogos de `11`
  - odd médio: `7.4545`
  - even médio: `7.5455`
  - low (1-12) médio: `8.0`
  - high (13-25) médio: `7.0`
  - score médio: `94.3645`
- Jogos abaixo de `11`
  - odd médio: `7.6709`
  - even médio: `7.3291`
  - low (1-12) médio: `8.1519`
  - high (13-25) médio: `6.8481`
  - score médio: `97.9324`

### Leitura prática

- Os jogos de `11` ficam mais equilibrados em paridade do que a massa abaixo de `11`
- A massa abaixo de `11` tende a concentrar mais casos com `8` ímpares
- Os jogos de `11` preservam melhor a presença de `high` sem exagerar em cobertura baixa
- O erro mais comum abaixo da zona é excesso de ruído estrutural com perda do núcleo `1/10/18/20`

### Perfil dos 11 reais

Os 11 reais do batch atual são:

- `28/10`
- `27/06`
- `27/07`
- `29/09`
- `32/07`
- `30/05`
- `30/09`
- `25/05`
- `33/01`
- `33/03`
- `33/07`

Quase todos mantêm o mesmo esqueleto:

- núcleo forte em `1, 9, 10, 11, 18, 20`
- extras repetidos em `24, 2, 15, 8`
- buracos recorrentes em `14, 16, 17, 7`

## 8. Ajuste proposto para mover de 11 para 12+

### Preservar

- `1, 10, 18, 20` como núcleo não negociável
- o segundo anel `9, 11, 6, 21`
- a linha de segurança de `repeat_min = 7` e `repeat_max = 10`
- `sequence_max = 6`
- `coverage_min >= 0.78`
- `entropy_min >= 0.78`
- `max_frequency_ratio <= 0.50`
- `min_frequency_ratio >= 0.29`

### Reduzir

- a insistência em `24`
- a repetição de `2`, `15`, `8`, `3` e `5`
- o ruído que empurra o jogo para fora de `12+` sem ganhar cobertura extra

### Expandir com controle

- manter a porta aberta para `12+` sem soltar o núcleo
- favorecer candidaturas que recuperem pelo menos um dos buracos recorrentes:
  - `16`
  - `17`
  - `14`
  - `7`
- só expandir diversidade quando o núcleo `11` continuar estável

## 9. Restrições que não devem ser relaxadas

- `validation_threshold = 11`
- `target_band = 11_to_15`
- `repeat_min`
- `repeat_max`
- `sequence_max`
- `max_frequency_ratio`
- `min_frequency_ratio`
- a proteção contra comemorar `10` como régua principal
- a proteção contra tratar `11` em `17/18` como validação
- a proteção contra `11/12` em `18` como validação

## 10. Restrições que podem ter expansão controlada

- `coverage_min`, se a expansão servir para recuperar cobertura sem soltar o núcleo
- `entropy_min`, se a expansão melhorar diversidade sem diluir o bloco forte
- a camada de seleção de extras, desde que `24/2/15/8` perca prioridade
- a camada de ajuste fino sobre paridade, apenas se mantiver o núcleo e a faixa 11

## Conclusão operacional

- A régua científica de 15 está correta em `11_to_15`
- O batch atual provou validação prospectiva mínima em `11`
- Ainda não há `12+`
- O próximo passo científico não é buscar mais `10`
- O próximo passo é preservar o núcleo que gerou `11` e mover a política para `12+` com expansão controlada

