# Auditoria de Unificação da Fonte Oficial de Concursos

## Fontes encontradas

Foram identificados múltiplos caminhos de leitura de concursos persistidos no ADM:

- `imported_contests` via `_load_imported_contest()`
- `lotofacil_official_history` via `_load_official_history_contest()`
- `official_lotofacil_history` via diagnósticos oficiais
- `session_state` como apoio operacional temporário
- fallbacks de tela e de geração limpa

## Fonte oficial escolhida

A fonte institucional única consolidada foi o gateway de concursos oficiais persistidos:

- `get_latest_official_contest()`
- `get_official_contest(contest_id)`
- `get_previous_official_contest(target_contest)`

Essa camada passa a servir tanto a Conferência quanto a RFE / página limpa da Lei 15.

## Caminhos removidos ou isolados

- leitura silenciosa por `imported_contests` na página limpa
- fallback implícito para `_load_imported_contest()` no fluxo da RFE
- uso direto de fonte paralela para definir o último concurso no fluxo limpo

Os caminhos antigos permanecem apenas como apoio diagnóstico e histórico, não como fonte primária da seleção institucional.

## Arquivos alterados

- `dashboard/institutional_app.py`
- `tests/test_protocol_structural_pipeline.py`
- `reports/auditoria_fonte_oficial_conferencia_vs_rfe.md`

## Payload antes

### Página limpa / RFE

- `rfe_previous_contest_found=False`
- `rfe_previous_contest_id=None`
- `rfe_previous_contest_numbers=-`
- `rfe_previous_contest_source=indisponivel`
- `rfe_previous_contest_message=Concurso anterior não encontrado na base oficial persistida.`
- `rfe_status=BLOQUEADO`
- `attempts_used=0`
- `rejected_by_output_commander=0`

### Conferência

- conferência encontrava o concurso pela base oficial persistida, mas a geração limpa ainda podia cair em fallback paralelo.

## Payload depois

### Página limpa / RFE

- `official_contest_source=official_lotofacil_history`
- `official_contest_id=3703`
- `official_contest_numbers=01 03 05 07 08 09 10 14 15 17 21 22 23 24 25`
- `rfe_previous_contest_found=True`
- `rfe_previous_contest_id=3703`
- `rfe_previous_contest_numbers=01 03 05 07 08 09 10 14 15 17 21 22 23 24 25`
- `rfe_previous_contest_source=official_lotofacil_history`
- `rfe_status=APROVADO` no cenário de referência válida
- `attempts_used>0`

### Conferência

- passa a ler o último concurso oficial persistido pelo mesmo gateway
- usa `official_lotofacil_history` como referência compartilhada

## Testes executados

- `python -m py_compile dashboard/institutional_app.py src/lotoia/governance/structural_rfe.py`
- `python -m pytest tests/test_structural_rfe.py tests/test_protocol_structural_pipeline.py -q`
- `python -m pytest tests/test_global_batch_deduplication.py -q`

## Resultado dos testes

- `15 passed`
- `2 passed`

## Conclusão institucional

A LotoIA passa a ter um único gateway institucional de leitura de concursos oficiais persistidos para conferência, geração limpa e RFE.

Isso reduz divergência entre telas e fluxo operacional, preserva a Lei 15, preserva a Lei 16 e mantém os fallbacks apenas como diagnóstico explícito.

