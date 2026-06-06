# Correção de schema do concurso oficial na conferência

## Erro encontrado

A página `Conferir Resultados` podia quebrar ao comparar jogos quando o objeto `contest` não expunha a chave `contest_number`.

## Função afetada

- `_compare_games_against_contest(...)`

## Linha aproximada

- bloco de acesso ao número do concurso e às dezenas oficiais

## Causa raiz

- acesso direto a `contest["contest_number"]`
- suposição de que as dezenas oficiais estariam sempre em `contest["dezenas"]` ou `contest["numbers"]`

## Schema recebido do objeto `contest`

Foram aceitas variações como:

- `contest_number`
- `contest_id`
- `id`
- `numero`
- `concurso`
- `draw_number`

E para dezenas:

- `numbers`
- `dezenas`
- `drawn_numbers`
- `matched_numbers`
- `resultado`

## Fallbacks implementados

- `_extract_contest_number(contest)`
- `_extract_contest_numbers(contest)`
- retorno controlado com mensagem institucional quando o número do concurso ou as dezenas oficiais não puderem ser identificados

## Confirmações institucionais

- `contest_id` agora é extraído com segurança
- as dezenas oficiais agora são extraídas com segurança
- Lei 15 não foi alterada
- Lei 16 não foi alterada

## Testes executados

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`
- `python -m pytest tests/test_global_batch_deduplication.py -q`

## Resultado dos testes

- compilação: OK
- pytest núcleo: OK
- pytest deduplicação global: OK

## Print da conferência sem erro

- não capturado nesta execução

## Commit

- a ser preenchido após publicação
