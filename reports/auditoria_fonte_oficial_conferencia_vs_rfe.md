# Auditoria de Fonte Oficial: Conferência vs RFE

## 1. Fonte usada pela conferência

A aba **Conferir Resultados** usa a camada de diagnóstico oficial persistida:

- `_load_official_history_diagnostics()`
- `_load_official_history_contest(selected_contest)`

O roteamento da página seleciona o concurso oficial máximo a partir de `contest_number_max` e, em seguida, carrega os dados oficiais daquele concurso pela tabela oficial persistida.

## 2. Fonte usada pela RFE

A geração limpa da Lei 15 foi ajustada para usar a **mesma fonte oficial persistida** da conferência:

- `_load_official_history_diagnostics()`
- `_load_official_history_contest(latest_contest_number)`
- `_load_previous_contest_numbers_for_rfe(target_contest)`

Quando não há `target_contest` explícito, o fluxo usa o último concurso oficial persistido como referência anterior. Quando há `target_contest`, a referência passa a ser `target_contest - 1`.

## 3. Divergência encontrada antes da correção

Antes do ajuste, a página limpa podia cair em um caminho de fallback diferente da conferência, usando dados auxiliares como base do último concurso em vez da trilha oficial persistida. Isso fazia a RFE registrar:

- `rfe_previous_contest_found=False`
- `rfe_previous_contest_id=None`
- `rfe_previous_contest_source=indisponivel`
- `rfe_status=BLOQUEADO`
- `insufficient_reason=RFE_PREVIOUS_CONTEST_NOT_FOUND`

Enquanto isso, a aba de conferência já enxergava o concurso oficial persistido.

## 4. Payload antes/depois

### Antes

- `rfe_previous_contest_found=False`
- `rfe_previous_contest_id=None`
- `rfe_previous_contest_numbers=-`
- `rfe_previous_contest_source=indisponivel`
- `rfe_previous_contest_message=Concurso anterior não encontrado na base oficial persistida.`
- `rfe_status=BLOQUEADO`
- `attempts_used=0`
- `rejected_by_output_commander=0`
- `insufficient_reason=RFE_PREVIOUS_CONTEST_NOT_FOUND`

### Depois

Com a fonte oficial alinhada, o fluxo passou a reutilizar a mesma leitura oficial da conferência. Nos testes focalizados, a referência oficial mockada de `3703` foi reconhecida corretamente:

- `rfe_previous_contest_found=True`
- `rfe_previous_contest_id=3703`
- `rfe_previous_contest_numbers=01 03 05 07 08 09 10 14 15 17 21 22 23 24 25`
- `rfe_previous_contest_source=official_lotofacil_history`
- `rfe_status=APROVADO`
- `attempts_used>0`

## 5. Testes executados

- `python -m py_compile dashboard/institutional_app.py src/lotoia/governance/structural_rfe.py`
- `python -m pytest tests/test_structural_rfe.py tests/test_protocol_structural_pipeline.py -q`
- `python -m pytest tests/test_global_batch_deduplication.py -q`

## 6. Resultado dos testes

- `tests/test_structural_rfe.py` + `tests/test_protocol_structural_pipeline.py`: `14 passed`
- `tests/test_global_batch_deduplication.py`: `2 passed`
- `py_compile`: ok

## 7. Conclusão institucional

A página limpa da geração Lei 15 e a aba **Conferir Resultados** passam a compartilhar a mesma trilha oficial persistida para leitura do concurso anterior e do último concurso disponível.

Isso resolve a divergência de integração entre conferência e RFE sem alterar:

- Lei 15
- Lei 16
- RFE estrutural
- OutputCommander
- geração base
- schema
- persistência
- sincronização externa

