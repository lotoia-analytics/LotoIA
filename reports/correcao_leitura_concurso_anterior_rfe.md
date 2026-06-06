# Correção da leitura do concurso anterior pela RFE-01

## 1. Causa encontrada

A RFE-01 estava recebendo referência anterior de forma frágil. Quando o concurso anterior não era encontrado na base oficial persistida, a geração ainda podia seguir para tentativas excessivas, terminando com `attempts_used=10000` e o motivo genérico `INSUFFICIENT_VALID_CANDIDATES`.

No ambiente local, o concurso `3703` ainda não está persistido na base oficial. Por isso, a correção precisava garantir:
- diagnóstico explícito;
- parada antecipada;
- nenhum ciclo de 10.000 tentativas quando a referência anterior não existe.

## 2. Função alterada

- [`dashboard/institutional_app.py`](../dashboard/institutional_app.py)
- [`src/lotoia/governance/structural_rfe.py`](../src/lotoia/governance/structural_rfe.py)

## 3. Como o concurso anterior é identificado

Fluxo aplicado:
- se houver concurso alvo, a referência anterior é `target_contest - 1`;
- se não houver concurso alvo definido, a referência usa o último concurso oficial persistido como base anterior;
- nunca há consulta externa;
- nunca há importação nova;
- a leitura fica restrita à base oficial já persistida.

## 4. Como as dezenas oficiais são normalizadas

Foi adicionado suporte a variações de schema e de formato:
- campos aceitos para concurso: `contest_number`, `contest_id`, `id`, `numero`, `concurso`, `draw_number`;
- campos aceitos para dezenas: `numbers`, `dezenas`, `drawn_numbers`, `resultado`, `official_numbers`;
- strings como `01 03 05 07 ...` também são normalizadas;
- o helper só considera referência válida quando encontra exatamente 15 dezenas distintas entre 1 e 25.

## 5. O que acontece se o concurso anterior não existir

- `found = False`
- `attempts_used = 0`
- `accepted_games = 0`
- `valid_candidates = 0`
- `fill_completed = False`
- `insufficient_reason = RFE_PREVIOUS_CONTEST_NOT_FOUND`
- mensagem institucional exibida: `RFE-01 bloqueada: concurso anterior não encontrado na base oficial persistida.`

## 6. O que acontece se as dezenas forem inválidas

- `found = False`
- `insufficient_reason = RFE_PREVIOUS_CONTEST_INVALID_NUMBERS`
- o bloqueio é explícito e institucional;
- não há tentativa de gerar 10.000 candidatos para contornar a ausência de validação.

## 7. Diagnósticos adicionados ao ADM

Campos adicionados/propagados:
- `rfe_previous_contest_found`
- `rfe_previous_contest_id`
- `rfe_previous_contest_numbers`
- `rfe_previous_contest_source`
- `rfe_previous_contest_message`
- `rfe_status`
- `rfe_01_rejected_games`
- `rfe_02_rejected_games`
- `rfe_rejected_games`
- `insufficient_reason`

## 8. Confirmação de que a geração não roda 10.000 tentativas sem referência anterior

Confirmado no fluxo:
- quando a referência anterior não existe, a geração é interrompida antes do loop;
- `attempts_used` permanece em `0`;
- o motivo não cai mais no genérico `INSUFFICIENT_VALID_CANDIDATES`.

## 9. Confirmação de que Lei 15 não foi alterada

Nenhuma lógica de Lei 15 foi alterada.

## 10. Confirmação de que Lei 16 não foi alterada

Nenhuma lógica de Lei 16 foi alterada.

## 11. Testes criados/alterados

### Novos testes em `tests/test_protocol_structural_pipeline.py`
- referência 3704 usa 3703 quando o registro oficial existe;
- bloqueio antes das tentativas quando a referência anterior falta;
- bloqueio quando a referência anterior possui menos de 15 dezenas;
- normalização de dezenas vindas como string.

### Testes já existentes mantidos
- `tests/test_structural_rfe.py`

## 12. Resultado dos testes

Executados com sucesso:
- `python -m py_compile dashboard/institutional_app.py src/lotoia/governance/structural_rfe.py`
- `python -m pytest tests/test_structural_rfe.py -q`
- `python -m pytest tests/test_protocol_structural_pipeline.py -q`
- `python -m pytest tests/test_global_batch_deduplication.py -q`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

Resumo:
- `7 passed`
- `5 passed`
- `2 passed`
- `26 passed`

## 13. Print/log com `rfe_previous_contest_id` e `rfe_previous_contest_numbers`

### Ambiente local real

No banco local atual, o concurso anterior `3703` ainda não está persistido:

```text
rfe_previous_contest_found=False
rfe_previous_contest_id=3703
rfe_previous_contest_numbers=
rfe_previous_contest_source=official_lotofacil_history
```

### Prova da referência esperada com `3703` disponível

Em cenário com o concurso oficial anterior presente:

```text
rfe_previous_contest_found=True
rfe_previous_contest_id=3703
rfe_previous_contest_numbers=01 03 05 07 08 09 10 14 15 17 21 22 23 24 25
rfe_previous_contest_source=official_lotofacil_history
```

## 14. Commit

- `3c8b649` - `feat: implementa RFE como validacao estrutural do cartao final`

## 15. Conclusão

A correção tornou a alimentação da RFE-01 diagnóstica, segura e paradora:
- concurso anterior ausente não dispara tentativa massiva;
- dezenas oficiais inválidas bloqueiam com causa institucional;
- a validação estrutural segue entre Lei 15 e Lei 16, sem alterar as leis.
