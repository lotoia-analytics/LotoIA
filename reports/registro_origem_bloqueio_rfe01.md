# Registro de origem do bloqueio RFE-01

## Objetivo

Documentar que bloqueios com `attempts_used=0` e `rfe_status=BLOQUEADO` pertencem à RFE-01, e não ao `OutputCommander`.

## Contexto verificado

O fluxo da geração institucional confirma que:
- a RFE é executada antes da validação final do pacote;
- se a referência anterior não existir ou vier inválida, a geração é interrompida cedo;
- nessas condições, o `OutputCommander` não deve sobrescrever a causa institucional mais específica.

## Ordem de execução observada

1. Carregamento da referência anterior da RFE.
2. Validação estrutural do cartão final pela RFE-01.
3. Apenas se a RFE aprovar, o fluxo segue para o `OutputCommander`.
4. Persistência somente após aceitação.

## Payload exemplo observado

### Cenário com referência anterior ausente

```text
rfe_enabled=True
rfe_previous_contest_found=False
rfe_previous_contest_id=None
rfe_previous_contest_numbers=-
rfe_previous_contest_source=indisponivel
rfe_previous_contest_message=None
rfe_status=BLOQUEADO
attempts_used=0
accepted_games=0
valid_candidates_found=0
rejected_by_output_commander=0
fill_completed=False
insufficient_reason=RFE_PREVIOUS_CONTEST_NOT_FOUND
```

### Cenário com referência anterior presente e válida

```text
rfe_enabled=True
rfe_previous_contest_found=True
rfe_previous_contest_id=3703
rfe_previous_contest_numbers=01 03 05 07 08 09 10 14 15 17 21 22 23 24 25
rfe_previous_contest_source=official_lotofacil_history
rfe_status=OK
attempts_used=1
accepted_games=1
valid_candidates_found=1
rejected_by_output_commander=0
fill_completed=True
insufficient_reason=None
```

## Motivos protegidos contra sobrescrita

Quando a causa real for institucionalmente mais específica, o diagnóstico deve preservar:
- `RFE_PREVIOUS_CONTEST_NOT_FOUND`
- `RFE_PREVIOUS_CONTEST_INVALID_NUMBERS`
- `INSUFFICIENT_RFE_APPROVED_CANDIDATES`

Esses motivos não devem ser substituídos por textos genéricos como:
- `INSUFFICIENT_VALID_CANDIDATES`
- `Pacote bloqueado por não atingir a quantidade solicitada.`

## Conclusão

Bloqueios com `attempts_used=0` e `rfe_status=BLOQUEADO` pertencem à RFE-01 e devem ser apresentados no ADM com a causa institucional original preservada.

## Referência de commit

- `34a57e7` - `fix: corrige leitura do concurso anterior na RFE`
