# Correção de TypeError em Cobertura Estrutural

## Contexto

A tela `Cobertura Estrutural` estava suscetível a `TypeError` ao calcular percentuais de dezenas dominantes, porque a variável de jogos podia chegar como lista em vez de contagem numérica.

## Arquivo alterado

- `dashboard/institutional_app.py`

## Causa raiz

O cálculo de percentual usava `float(games)` diretamente na renderização da página. Em cenários em que `games` era uma lista de jogos, a conversão falhava.

## Correção aplicada

- Reaproveitei a contagem segura local `_safe_count_games(value: object) -> int`.
- Passei a calcular `games_count = _safe_count_games(games)` antes da renderização dos cards.
- O card `Jogos analisados` agora usa `games_count`.
- O percentual da tabela de dezenas dominantes agora usa `games_count` como denominador.
- Quando não há contagem válida, o campo `Percentual` mostra `-`.

## O que não mudou

- lógica de geração
- lógica de conferência
- lógica de simulação
- Lei 15
- Lei 17
- Lei 18
- memória científica
- banco de dados
- endpoints

## Validação

Executar:

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

## Resultado esperado

- a página `Cobertura Estrutural` abre sem TypeError
- `Jogos analisados` não quebra quando a origem vier como lista
- o percentual das dezenas dominantes continua informativo e seguro
- quando não houver base numérica suficiente, a interface exibe `-`
