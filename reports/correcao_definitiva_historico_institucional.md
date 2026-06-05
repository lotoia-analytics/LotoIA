# Correção Definitiva do Histórico Institucional

## Causa do erro

O erro `StreamlitAPIException: Expanders may not be nested inside other expanders` era provocado por blocos de diagnóstico do Histórico Institucional que ainda abriam `expander` internos dentro de áreas já recolhidas da própria página.

## Local corrigido

- `dashboard/institutional_app.py`
- Função principal: `_render_history_institutional_page`
- Função de apoio ajustada: `_render_scientific_policy_panel`

## Correções aplicadas

- O painel de política científica passou a respeitar `use_expander=False` também para os detalhes por janela.
- A seção `Memória científica legada — quarentena documental` passou a conter apenas conteúdo documental, sem abrir subexpander interno.
- A memória pós-conferência e a memória consolidada foram retextualizadas como blocos observacionais e de registro técnico legado.
- O topo do bloco institucional deixou de destacar `scientific_calibration_decisions` como status primário, usando o rótulo `Registros científicos legados`.

## Termos sensíveis encontrados e tratamento

### Permanecem apenas em quarentena documental ou detalhes técnicos

- `Lei Científica da Geração`
- `LEI DESCOBERTA E SELECIONADA`
- `recalibrate_from_*`
- `recommended_action`
- `scientific_calibration_decisions`
- `dominant_memory`
- `selection_variant`
- `scientific_batch_reconciliation`
- `cross_validated_scientific_batch_memory`

### Tratamento aplicado

- Os termos foram removidos da camada principal do Histórico Institucional.
- Quando permanecem no arquivo, aparecem apenas em:
  - `Memória científica legada — quarentena documental`
  - `Detalhes técnicos avançados`
  - trechos de carga técnica/persistência, sem comando operacional.

## Estrutura final da página

1. Cabeçalho institucional
2. Estado da infraestrutura
3. Rastreabilidade institucional principal
4. Base oficial Lotofácil
5. Memória pós-conferência observacional
6. Memória consolidada da bateria conferida
7. Histórico oficial Lotofácil
8. Memória científica legada — quarentena documental
9. Detalhes técnicos avançados

## Validações executadas

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

Resultado:

- `26 passed`
- 1 warning de cache do pytest no ambiente, sem impacto funcional

## Confirmação final

- A página foi reorganizada sem alterar lógica funcional, banco, endpoints, geração, conferência ou simulação.
- A Lei 15 permanece soberana.
- A Lei 17 e a Lei 18 permanecem como validação/referência.
- O legado documental não comanda runtime oficial.
