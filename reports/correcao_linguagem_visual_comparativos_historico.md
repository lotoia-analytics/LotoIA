# Linguagem visual institucional do Comparativos Histórico

## Função/bloco alterado

- `dashboard/institutional_app.py`
- Bloco `_render_comparative_history_page(snapshot)`

## Labels técnicos substituídos

- `generated_games` → `Jogos gerados`
- `reconciliation_runs` → `Conferências realizadas`
- `imported_contests` → `Concursos oficiais importados`
- `average_overlap` → `Média de sobreposição`

## Estrutura visual final

1. Cabeçalho institucional
2. Resumo da comparação
3. Leitura da geração analisada
4. Leitura do concurso oficial
5. Indicadores de sobreposição
6. Números dominantes
7. Interpretação observacional
8. Detalhes técnicos avançados

## JSON bruto

- O JSON bruto foi removido da área principal.
- Agora aparece apenas em `Detalhes técnicos avançados`.

## Confirmação observacional

- A página declara explicitamente que é analítica e observacional.
- Não há comando de recalibração na área principal.
- Não há alteração de Lei 15.

## Testes executados

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

Resultado:

- `26 passed`

## Observação

- A leitura de números dominantes foi traduzida para `Dezena`, `Frequência nos jogos` e `Percentual`.
- Os dados brutos permanecem acessíveis somente em modo técnico avançado.
