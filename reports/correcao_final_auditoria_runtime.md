# Correção final da Auditoria do Runtime

## Função/bloco alterado

- `dashboard/institutional_app.py`
- Bloco `_render_runtime_audit_page(snapshot)`

## Ordem final das seções

1. `Estado Atual do Runtime`
2. `SELECT COUNT(*) no runtime`
3. `Diferenças entre módulos`
4. `Auditoria Operacional Ativa`
5. `Auditoria de integridade`
6. `Tabelas Institucionais`
7. `Timeline secundária`
8. `Memória Científica Observacional / Legada`
9. `Papel do session_state`
10. `Detalhes técnicos avançados` quando aplicável

## Fonte da leitura de runtime ativo

- `_runtime_audit_payload(snapshot)`
- `_database_snapshot()`
- `_load_official_history_diagnostics()`

## Fonte da geração operacional ativa

- `generation_events`
- `generated_games`
- `reconciliation_runs`
- `reconciliation_games`
- `institutional_output_signatures`
- `latest_generation = _load_generation_history_light(limit=1)`
- `latest_reconciliation = _load_latest_reconciliation_summary()`

## Fonte da memória científica observacional

- `_load_latest_scientific_memory(limit=20)`
- `scientific_reconciliation`
- `scientific_batch_reconciliation`
- `scientific_strong_near_miss`

## Tratamento aplicado ao near miss / `recalibrate_from_*`

- O valor bruto permanece apenas como registro técnico legado dentro da memória observacional.
- Na área principal da Auditoria do Runtime ele foi reclassificado como `Registro técnico legado`.
- O texto operacional não apresenta `Ação` nem `recalibrate_from_*` como comando visual principal.

## Tratamento aplicado ao `session_state`

- `session_state` foi mantido como diagnóstico temporário de interface.
- O texto explícito informa que ele não é fonte persistente nem origem de conferência.

## Strings de acentuação corrigidas

- `Memória`
- `Científica`
- `pós-conferência`
- `geração`
- `reconciliação`
- `Lotofácil`
- `histórico`

## Confirmação institucional

- Nenhuma lógica funcional foi alterada
- Nenhum dado persistido foi modificado
- Nenhuma recalibração foi executada
- Nenhuma geração foi disparada
- Lei 15, Lei 17 e Lei 18 permaneceram intactas

## Testes executados

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

Resultado:

- `26 passed`

## Observação

- A validação visual do topo, do bloco operacional e da memória observacional deve ser feita na página `Auditoria do Runtime`.
