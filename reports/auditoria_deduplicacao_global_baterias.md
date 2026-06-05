# Auditoria de Deduplicação Global entre Grupos

## Contexto

Foi auditada a geração de baterias compostas por múltiplos grupos para garantir que não houvesse reaproveitamento de jogos entre grupos distintos da mesma bateria.

## Onde a duplicação foi encontrada

A trava existente estava concentrada na deduplicação local do grupo gerado em cada execução. Isso permitia que jogos únicos dentro de um grupo reaparecessem em grupos posteriores da mesma bateria se a assinatura global não fosse compartilhada entre as execuções.

## Tipo de duplicação

- deduplicação intra-grupo: já existia
- deduplicação entre grupos da mesma bateria: precisava de trava global explícita

## Correção aplicada

- adicionei uma trava global por bateria com `seen_signatures`
- a geração agora compartilha as assinaturas aceitas entre todos os grupos da mesma bateria
- a deduplicação passa a valer para:
  - grupo 1
  - grupo 2
  - grupo 3
  - grupo 4
- a detecção continua respeitando a assinatura normalizada do jogo

## Quantidades esperadas

- total de jogos solicitados: 200
- total de jogos gerados: 200
- total de jogos únicos: 200
- duplicados globais: 0

## Persistência e assinatura

- `institutional_output_signatures` continua sendo a tabela oficial de assinatura persistida
- a assinatura continua baseada nas dezenas normalizadas e ordenadas
- a trava global evita que o mesmo jogo apareça em mais de um grupo da mesma bateria

## Testes executados

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`
- `python -m pytest tests/test_global_batch_deduplication.py -q`

## Confirmação institucional

- Lei 15 não foi alterada
- Lei 17/18 não foram alteradas
- a correção é operacional e de deduplicação global da bateria
