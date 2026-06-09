# Extinção operacional de `batch_id` / `clean-law15-*` no ADM

## Pontos removidos da interface

- seletor visual de `batch_id` na aba **Conferir Resultados**
- texto operacional `Selecionar bateria para conferência`
- rótulo visual `Bateria ativa`
- exibição de `clean-law15-*` como identidade operacional
- exibição de `batch_id` como comando principal na conferência

## Pontos substituídos por `generation_event_id`

- seletor principal passou a ser `Selecionar geração para conferência`
- conferência passou a operar por `generation_event_id`
- a geração selecionada é usada para carregar os jogos persistidos
- a geração selecionada é associada à reconciliação
- histórico analítico passou a mostrar `Geração ativa`

## Confirmação de extinção visual

- `batch_id` e `clean-law15-*` não aparecem mais como operação principal na interface
- identificadores antigos permanecem apenas como dados técnicos internos
- a operação visível do ADM agora é centrada em `Geração` / `generation_event_id`

## Preservação de dados antigos

- nenhum dado foi apagado do banco
- os identificadores legados permanecem preservados em memória e payloads técnicos
- a mudança foi somente operacional/visual

## Lei 15, Lei 16, RFE e OutputCommander

- Lei 15 inalterada
- Lei 16 inalterada
- RFE inalterada
- OutputCommander inalterado

## Testes executados

- `python -m py_compile dashboard/institutional_app.py src/lotoia/governance/structural_rfe.py`
- `python -m pytest tests/test_structural_rfe.py tests/test_protocol_structural_pipeline.py -q`
- `python -m pytest tests/test_global_batch_deduplication.py -q`

## Resultado final

- `15 passed`
- `2 passed`
- compilação OK

## Commit publicado

- `fix: extingue batch_id da operacao ADM`

