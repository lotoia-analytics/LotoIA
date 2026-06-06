# Correção definitiva do KeyError `contest_number` na conferência

## Erro encontrado

A página `Conferir Resultados` podia quebrar quando o objeto `contest` não continha a chave `contest_number`.

## Função afetada

- `_compare_games_against_contest(...)`

## Linha aproximada

- trecho de leitura do concurso oficial antes da comparação dos jogos

## Schema real recebido em `contest`

O objeto pode expor o número do concurso por diferentes nomes:

- `contest_number`
- `contest_id`
- `id`
- `numero`
- `concurso`
- `draw_number`

As dezenas oficiais também podem variar:

- `numbers`
- `dezenas`
- `drawn_numbers`
- `matched_numbers`
- `resultado`

## Substituição do acesso direto

- removido qualquer uso direto de `contest["contest_number"]`
- a comparação agora depende de `_extract_contest_number(contest)`
- as dezenas oficiais agora dependem de `_extract_contest_numbers(contest)`

## Helper aplicado

- `_extract_contest_number(contest)`
- `_extract_contest_numbers(contest)`

## Confirmação de grep sem acesso direto

- `grep -n 'contest\["contest_number"\]' dashboard/institutional_app.py` não retorna ocorrências

## Confirmações institucionais

- Lei 15 não foi alterada
- Lei 16 não foi alterada
- nenhuma lógica de conferência foi alterada
- nenhuma persistência foi alterada

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
