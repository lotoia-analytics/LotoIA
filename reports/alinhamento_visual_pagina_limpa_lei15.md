# Alinhamento Visual da Página Limpa Lei 15

## Resumo executivo
A parte inferior da página limpa Lei 15 foi restaurada visualmente após as atualizações recentes.

O ajuste manteve intactos:
- Lei 15;
- algoritmo de geração;
- banco;
- schema;
- gateway oficial;
- guardrail da fonte oficial.

## O que foi ajustado
Foram adicionados blocos explícitos de renderização após a tabela de `Jogos gerados`:
- `Rastros institucionais`
- `Diagnóstico inferior`
- `Assinaturas e rastreabilidade final`

Esses blocos exibem:
- `generation_event_id`
- `official_contest_source`
- `official_contest_id`
- `official_contest_numbers`
- `rfe_previous_contest_*`
- `rfe_status`

## Ordem visual preservada
1. aviso Lei 15;
2. botão;
3. resumo da geração;
4. rastros institucionais;
5. métricas;
6. jogos gerados;
7. diagnóstico inferior;
8. assinaturas/rastreabilidade final.

## Validação executada
- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_clean_app_formats.py tests/test_protocol_structural_pipeline.py -q --basetemp=tmp_pytest_cleanpage`

Resultado:
- `32 passed`

## Confirmações finais
- não houve alteração da Lei 15;
- não houve alteração do motor de geração;
- não houve alteração do banco;
- não houve alteração do schema;
- não houve alteração do gateway oficial;
- não houve alteração do guardrail da fonte oficial;
- não houve `push`.

## Status final
**PAGINA_LIMPA_LEI15_COM_PARTE_INFERIOR_RESTAURADA**
