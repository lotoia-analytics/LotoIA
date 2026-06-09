# Correção da Conferência dos Formatos Expandidos 16D a 23D

## Causa encontrada

A conferência do ADM estava usando a coluna de `dezenas`/`número do núcleo` como base de comparação, o que fazia uma geração expandida ser avaliada como se tivesse apenas 15 dezenas.

Isso reduzia indevidamente um cartão expandido para o núcleo Lei 15 e impedia a leitura correta do `cartão_final`.

## Campo antigo usado pela conferência

- `numbers`
- `núcleo_lei_15`
- campos equivalentes de 15 dezenas

## Campo correto usado agora

- `final_card_numbers`
- `cartao_final`
- `cartão_final`

Quando o formato é 16D a 23D, a conferência passa a usar o `cartão_final` completo.  
Quando o formato é 15D, a conferência continua usando o núcleo de 15 dezenas.

## Validação formato por formato

Foram validados os formatos:

- 15D
- 16D
- 17D
- 18D
- 19D
- 20D
- 21D
- 22D
- 23D

Resultado institucional:

- `formato_cartao` preservado
- `origem_dezenas_conferencia` correta
- `dezenas_conferidas_count` igual ao formato
- acertos calculados sobre o `cartão_final`
- `generation_event_id` preservado

## Payload exemplo

Exemplo validado na conferência:

- `generation_event_id=383`
- `formato_cartao=23`
- `dezenas_conferidas_count=23`
- `origem_dezenas_conferencia=cartao_final`
- `expected_card_size=23`
- `actual_card_size=23`

## Testes executados

- `python -m py_compile dashboard/institutional_app.py src/lotoia/governance/structural_rfe.py`
- `python -m pytest tests/test_protocol_structural_pipeline.py -q`
- `python -m pytest tests/test_clean_app_formats.py tests/test_structural_rfe.py tests/test_protocol_structural_pipeline.py -q`
- `python -m pytest tests/test_global_batch_deduplication.py -q`

## Resultado dos testes

- `17 passed`
- `36 passed`
- `2 passed`

## Confirmações institucionais

- Lei 15 não foi alterada.
- Lei 16 não foi alterada.
- `batch_id` / `clean-law15-*` não voltou à operação visual.
- A conferência continua por `generation_event_id`.

## Conclusão institucional

A conferência dos formatos expandidos 16D a 23D agora avalia o `cartão_final` completo, preservando o núcleo Lei 15 como base soberana apenas no formato 15D.
