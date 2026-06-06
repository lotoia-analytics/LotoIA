# Correção do diagnóstico da página limpa ADM

## Objetivo

Preservar o bloqueio institucional da RFE-01 no pós-processamento da página limpa, sem sobrescrever a causa real com o motivo genérico do `OutputCommander`.

## Arquivos alterados

- [`dashboard/institutional_app.py`](../dashboard/institutional_app.py)
- [`tests/test_protocol_structural_pipeline.py`](../tests/test_protocol_structural_pipeline.py)

## Payload antes

Na página limpa, o diagnóstico era exibido com a seguinte mistura:

```text
attempts_used=0
candidate_pool_generated=0
valid_candidates_found=0
accepted_games=0
rejected_by_output_commander=10
fill_completed=False
insufficient_reason=INSUFFICIENT_VALID_CANDIDATES
```

Além disso, os campos `rfe_*` não apareciam no bloco visual de diagnóstico.

## Payload depois

Após a correção do pós-processamento:

```text
attempts_used=0
candidate_pool_generated=0
valid_candidates_found=0
accepted_games=0
rejected_by_output_commander=0
fill_completed=False
insufficient_reason=RFE_PREVIOUS_CONTEST_NOT_FOUND
rfe_status=BLOQUEADO
rfe_previous_contest_found=False
rfe_previous_contest_id=None
rfe_previous_contest_numbers=-
rfe_previous_contest_source=indisponivel
rfe_previous_contest_message=
```

## O que foi corrigido

1. Se `attempts_used=0` e `rfe_status=BLOQUEADO`, o motivo específico da RFE é preservado.
2. `rejected_by_output_commander` deixa de ser usado como causa principal nesse cenário e passa a `0`.
3. O diagnóstico visual da página limpa passa a exibir os campos:
   - `rfe_previous_contest_found`
   - `rfe_previous_contest_id`
   - `rfe_previous_contest_numbers`
   - `rfe_previous_contest_source`
   - `rfe_previous_contest_message`
   - `rfe_status`

## Testes executados

- `python -m pytest tests/test_structural_rfe.py tests/test_protocol_structural_pipeline.py -q`
- `python -m pytest tests/test_global_batch_deduplication.py -q`

## Resultado dos testes

- `13 passed`
- `2 passed`

## Conclusão institucional

O diagnóstico da página limpa ADM agora preserva a causa institucional da RFE-01 quando o bloqueio ocorre antes das tentativas. O `OutputCommander` permanece como auditor posterior e não sobrescreve o motivo mais específico.
