# Expansão auditada Lei 15: formatos 16D a 23D

## Objetivo da expansão

Disponibilizar no ADM a expansão auditada do cartão Lei 15 para formatos de 16 a 23 dezenas, preservando o núcleo soberano de 15 dezenas e mantendo `Geração` / `generation_event_id` como eixo operacional.

## Confirmação institucional

- Lei 15 não foi alterada
- os formatos 16D a 23D foram tratados como expansão auditada por reservas
- `batch_id` / `clean-law15-*` não voltou para a operação visual
- a conferência continua por `Geração` / `generation_event_id`

## Mapeamento oficial

| Expansão | Formato |
|---|---:|
| 15D + 1 | 16 |
| 15D + 2 | 17 |
| 15D + 3 | 18 |
| 15D + 4 | 19 |
| 15D + 5 | 20 |
| 15D + 6 | 21 |
| 15D + 7 | 22 |
| 15D + 8 | 23 |

## Arquivos alterados

- `dashboard/institutional_app.py`
- `tests/test_clean_app_formats.py`
- `reports/expansao_auditada_lei15_formatos_16a23.md`

## Testes executados

- `python -m py_compile dashboard/institutional_app.py src/lotoia/governance/structural_rfe.py`
- `python -m pytest tests/test_clean_app_formats.py tests/test_structural_rfe.py tests/test_protocol_structural_pipeline.py -q`
- `python -m pytest tests/test_global_batch_deduplication.py -q`

## Resultado dos testes

- `27 passed`
- `2 passed`

## Payload de exemplo

- `generation_event_id`: persistido após a geração
- `formato_cartao`: 16..23
- `nucleo_lei_15_size`: 15
- `reservas_auditadas_count`: `formato_cartao - 15`
- `cartao_final_size`: igual ao formato escolhido
- `accepted_games`: registrado
- `valid_candidates`: registrado
- `attempts_used`: registrado
- `fill_completed`: registrado

## Confirmação final

A expansão 16D a 23D foi implementada como extensão auditada da Lei 15, sem alterar o núcleo de 15 dezenas e sem reintroduzir `batch_id` / `clean-law15-*` como eixo operacional.

