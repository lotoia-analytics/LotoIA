# Institucionalização visual da Cobertura Estrutural

## Função/bloco alterado

- `dashboard/institutional_app.py`
- Bloco `_render_cobertura_estrutural_page(snapshot)`

## Labels técnicos substituídos

- `GAMES` → `Jogos analisados`
- `AVERAGE_OVERLAP` → `Média de sobreposição`
- `AVERAGE_UNIQUE_NUMBERS` → `Média de dezenas únicas`
- `DOMINANT_NUMBERS` → `Dezenas dominantes`

## Nova estrutura visual aplicada

1. Título: `Cobertura Estrutural`
2. Subtítulo institucional
3. Aviso observacional
4. Cards principais em português
5. `Dezenas dominantes da bateria`
6. Explicação das dezenas dominantes
7. Tabela com `Dezena`, `Frequência nos jogos` e `Percentual`
8. `Interpretação observacional`
9. `Detalhes técnicos avançados`

## Tabela de dezenas dominantes

- A tabela visual usa `Dezena`, `Frequência nos jogos` e `Percentual`.
- O dataframe original foi preservado para os cálculos.

## Confirmação institucional

- A página foi declarada como analítica e observacional.
- Nenhuma lógica funcional foi alterada.
- Lei 15 permaneceu intocada.

## Testes executados

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

Resultado:

- `26 passed`

## Observação

- Os nomes técnicos permanecem apenas como referência interna e técnica.
