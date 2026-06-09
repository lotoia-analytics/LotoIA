# Padronização de `cartão_final` 16D a 23D em todas as esferas

## Causa encontrada

A conferência e as telas observacionais ainda podiam interpretar o jogo expandido como se fosse apenas o núcleo Lei 15 de 15 dezenas, usando `dezenas`/núcleo como fonte ambígua.

## Correção aplicada

- Foi criada/centralizada a função `_select_conference_numbers`.
- O `cartão_final` passou a ser priorizado na conferência para formatos `16D` a `23D`.
- O cálculo de `hits` e `matched_numbers` passou a usar as dezenas conferidas completas.
- As telas de conferência, histórico analítico e auditoria observacional passaram a exibir `formato_cartao`, `núcleo_lei_15`, `reservas_auditadas`, `cartão_final`, `dezenas_conferidas_count` e `origem_dezenas_conferencia`.

## Validação formato por formato

Foram validados os formatos:

- `15D`
- `16D`
- `17D`
- `18D`
- `19D`
- `20D`
- `21D`
- `22D`
- `23D`

Resultado:

- `15D` confere 15 dezenas
- `16D` confere 16 dezenas
- `17D` confere 17 dezenas
- `18D` confere 18 dezenas
- `19D` confere 19 dezenas
- `20D` confere 20 dezenas
- `21D` confere 21 dezenas
- `22D` confere 22 dezenas
- `23D` confere 23 dezenas

## Exemplo 19D

No cenário controlado de 19D:

- `nucleo_lei_15`: 15 dezenas
- `reservas_auditadas`: 4 dezenas
- `cartao_final`: 19 dezenas
- `dezenas_conferidas_count`: 19
- `origem_dezenas_conferencia`: `cartao_final`
- `hits`: 15

## Exemplo 23D

O painel passa a registrar:

- `formato_cartao=23`
- `cartao_final_size=23`
- `dezenas_conferidas_count=23`
- `origem_dezenas_conferencia=cartao_final`

## Testes executados

- `python -m py_compile dashboard/institutional_app.py src/lotoia/governance/structural_rfe.py`
- `python -m pytest tests/test_conferencia_formatos_expandidos.py -q`
- `python -m pytest tests/test_clean_app_formats.py tests/test_structural_rfe.py tests/test_protocol_structural_pipeline.py -q`
- `python -m pytest tests/test_global_batch_deduplication.py -q`

## Resultado dos testes

- `10 passed`
- `36 passed`
- `2 passed`

## Confirmações institucionais

- Lei 15 não foi alterada.
- Lei 16 não foi alterada.
- RFE não foi alterada.
- OutputCommander não foi alterado.
- A geração 16D a 23D não foi alterada.
- A conferência continua por `generation_event_id`.
- `batch_id` / `clean-law15-*` não voltou.

## Conclusão institucional

Todas as esferas passam a usar `cartão_final` como objeto operacional e conferível nos formatos `16D` a `23D`, preservando o núcleo Lei 15 como referência soberana apenas no formato 15D.
