# Diagnóstico de origem do bloqueio no Painel ADM

## Objetivo

Comparar o payload bruto gerado ao clicar em **Gerar com Lei 15** na página limpa com os campos exibidos visualmente no Painel ADM, para determinar se o bloqueio vem da RFE-01 ou do `OutputCommander`.

## Comandos executados

```bash
python -m pytest tests/test_structural_rfe.py tests/test_protocol_structural_pipeline.py -q
python -m pytest tests/test_global_batch_deduplication.py tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q
```

## Evidência do payload bruto

Execução headless da geração limpa com `requested_count=10`:

```text
PAYLOAD
rfe_previous_contest_found=False
rfe_previous_contest_id=None
rfe_previous_contest_numbers=-
rfe_previous_contest_source=indisponivel
rfe_previous_contest_message=None
rfe_status=BLOQUEADO
candidate_pool_generated=0
valid_candidates_found=0
accepted_games=0
rejected_by_output_commander=10
attempts_used=0
fill_completed=False
insufficient_reason=INSUFFICIENT_VALID_CANDIDATES
RESULT
rejected_by_output_commander=10
attempts_used=0
fill_completed=False
insufficient_reason=INSUFFICIENT_VALID_CANDIDATES
status_comandante_saida=BLOQUEADO
total_jogos_unicos=0
total_jogos_rejeitados=10
```

## Campos exibidos na tela limpa

O bloco de diagnóstico da página limpa exibe apenas:
- `requested_count`
- `candidate_pool_generated`
- `valid_candidates_found`
- `accepted_games`
- `rejected_by_internal_duplicate`
- `rejected_by_invalid_size`
- `rejected_by_repeated_pattern`
- `rejected_by_output_commander`
- `attempts_used`
- `fill_completed`
- `insufficient_reason`

Os campos `rfe_*` não aparecem nesse bloco visual.

## Divergências encontradas

1. O payload bruto já vem misturado:
   - `attempts_used=0`
   - `candidate_pool_generated=0`
   - `valid_candidates_found=0`
   - `rfe_status=BLOQUEADO`
   - mas `rejected_by_output_commander=10`
   - e `insufficient_reason=INSUFFICIENT_VALID_CANDIDATES`

2. O `OutputCommander` não deveria ser o motivo real quando não houve tentativa nem candidato.

3. A página limpa oculta os campos `rfe_*`, então o diagnóstico visual fica incompleto para esse caso.

## Origem provável da divergência

O problema principal está na montagem do payload da página limpa, em:
- [`dashboard/institutional_app.py`](../dashboard/institutional_app.py)
- função `_run_clean_law15_generation(...)`

Ali, após a geração, o código:
- chama `output_commander_validate_games(...)` mesmo quando a RFE já bloqueou antes;
- sobrescreve `insufficient_reason` com `INSUFFICIENT_VALID_CANDIDATES` quando o total não fecha;
- preenche `rejected_by_output_commander` com o valor do `commander_report`, o que faz aparecer `10` mesmo sem tentativa/candidato.

## Ordem de execução confirmada

1. A RFE executa primeiro na geração direta.
2. Se a referência anterior faltar, o fluxo para cedo com `attempts_used=0`.
3. O `OutputCommander` só deveria ser auditoria posterior quando há jogos gerados.
4. Na página limpa, a camada de pós-processamento ainda injeta motivo genérico no payload.

## Recomendações

- **Corrigir o payload** da página limpa para preservar o motivo institucional da RFE quando `attempts_used=0` e `rfe_status=BLOQUEADO`.
- **Expor os campos `rfe_*` na tela limpa**, ou ao menos no bloco de diagnóstico avançado, para evitar leitura incompleta.
- **Não atribuir `rejected_by_output_commander=10` como causa principal** quando a RFE já bloqueou antes do loop.

## Critério de aceite

Quando `attempts_used=0` e `rfe_status=BLOQUEADO`:
- `rejected_by_output_commander` deve ser `0`
- `insufficient_reason` deve ser um motivo específico da RFE
- a tela deve mostrar os campos `rfe_*`

Motivos protegidos:
- `RFE_PREVIOUS_CONTEST_NOT_FOUND`
- `RFE_PREVIOUS_CONTEST_INVALID_NUMBERS`
- `INSUFFICIENT_RFE_APPROVED_CANDIDATES`

## Conclusão

**Classificação: Suspeito visual/diagnóstico.**

O bloqueio observado na página limpa não está consistente com a cadeia institucional documentada. A divergência nasce no payload/pós-processamento da página limpa e não na Lei 15 em si.
