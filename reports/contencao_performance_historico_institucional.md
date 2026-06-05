# Contenção de Performance do Histórico Institucional

## Causa provável do peso

- O Histórico Institucional montava, no primeiro render, tabelas completas, payloads técnicos extensos e memória científica legada em blocos visuais grandes.
- A visualização inicial incluía a tabela oficial completa, memória consolidada, near miss e payloads históricos antes de qualquer ação explícita do usuário.

## Funções revisadas

- `_render_history_institutional_page`
- `_render_scientific_policy_panel`
- `_load_official_history_rows`
- blocos de memória consolidada e near miss do Histórico Institucional

## Blocos movidos para carregamento sob demanda

- Histórico oficial Lotofácil
- Memória consolidada da bateria conferida
- Melhores near miss
- Memória científica legada — quarentena documental
- Detalhes técnicos avançados / payloads históricos legados

## Limites aplicados

- Histórico oficial inicial: 10 linhas
- Histórico oficial sob demanda: até 25 linhas por padrão, com ajuste manual até 50
- Near miss: detalhes fechados por padrão
- Memória consolidada: detalhes fechados por padrão
- Memória científica legada: payload carregado somente após ação explícita

## Validação visual

- A página agora abre com cabeçalho, infraestrutura, rastreabilidade e resumos.
- A tabela completa do histórico oficial não é montada por padrão.
- Os blocos pesados exigem checkbox/ação explícita para carregar dados completos.
- A rolagem fica mais leve e os dados extensos não travam o primeiro render.

## Testes executados

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

Resultado:

- `26 passed`
- 1 warning de cache do pytest no ambiente

## Confirmação institucional

- Nenhuma lógica funcional foi alterada.
- Nenhum dado foi apagado.
- Lei 15, Lei 17 e Lei 18 permaneceram intactas.
- Banco, endpoints, geração, conferência e simulação permaneceram intactos.

## Riscos residuais

- A página continua extensa por natureza institucional, mas o primeiro render ficou leve e os blocos pesados agora são sob demanda.
- O carregamento completo depende de ação explícita do usuário, o que é desejado para preservar performance.
