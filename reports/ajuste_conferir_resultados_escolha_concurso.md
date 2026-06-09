# Ajuste do Campo `Escolha o Concurso` em `Conferir Resultados`

## Objetivo

Substituir o rótulo visual de `Último Concurso` por um campo operacional editável, `Escolha o Concurso`, para que a conferência use explicitamente um concurso oficial carregado da base local.

## O que foi ajustado

- O campo exibido na tela `Conferir Resultados` passou a ser `Escolha o Concurso`.
- O concurso selecionado é resolvido a partir da base oficial local antes da conferência.
- Se o concurso não existir na base oficial, a tela exibe aviso e bloqueia a ação principal.
- A conferência continua sem consulta de API no clique do botão.
- Para compatibilidade com a memória científica e testes existentes, a conferência em lote preserva `batch_id` e demais campos esperados no resultado consolidado.

## Compatibilidade preservada

- `institutional_batch_conference_result` continua expondo `batch_id`.
- A conferência em lote continua materializando a memória científica global.
- O fluxo permanece compatível com os testes de conferência científica já existentes.

## Validação executada

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

Resultado:

- `26 passed`

## Confirmação

Esta entrega altera apenas a seleção operacional do concurso na tela de conferência e a compatibilidade do resultado consolidado em lote.
Nenhuma lógica de geração, Lei 15, conferência científica ou persistência estrutural foi alterada.
