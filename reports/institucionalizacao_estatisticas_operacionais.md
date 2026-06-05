# Institucionalização das Estatísticas Operacionais

## Página alterada

- `Estatísticas Operacionais`

## Função/bloco alterado

- `_render_estatisticas_operacionais_page`

## Labels técnicos encontrados

- `generation_events`
- `generated_games`
- `reconciliation_runs`
- `session_keys`
- `last_ui_event`
- `latest_generation_event_id`
- `latest_reconciliation_id`

## Labels substituídos

- `generation_events` -> `Eventos de geração`
- `generated_games` -> `Jogos gerados`
- `reconciliation_runs` -> `Conferências realizadas`
- `session_keys` -> `Chaves de sessão`
- `last_ui_event` -> `Último evento de interface`
- `latest_generation_event_id` -> `Última geração registrada`
- `latest_reconciliation_id` -> `Última conferência registrada`

## Aviso institucional adicionado

- `Esta página é operacional e observacional. Não gera jogos, não recalibra a Lei 15, não altera a Lei 16 e não modifica histórico.`

## Separação entre persistência e sessão

- os três primeiros indicadores refletem registros operacionais persistidos
- o indicador de chaves de sessão reflete apenas o estado temporário da interface atual

## Últimos registros operacionalizados em português

- Último evento de interface
- Última geração registrada
- Última conferência registrada

## Interpretação operacional adicionada

- a seção explica que os indicadores servem para auditoria do funcionamento do ADM
- a leitura de sessão é temporária e não deve ser interpretada como histórico oficial

## Detalhes técnicos movidos para expander

- o dicionário cru `raw_operational_stats` ficou em `Detalhes técnicos avançados`

## Confirmações institucionais

- Lei 15 não foi alterada
- Lei 16 não foi alterada
- nenhuma lógica operacional foi alterada

## Testes executados

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`
- `python -m pytest tests/test_global_batch_deduplication.py -q`

## Resultado dos testes

- compilação: OK
- pytest núcleo: OK
- pytest deduplicação global: OK

## Print final da página

- não capturado nesta execução

## Commit gerado

- a ser preenchido após publicação
