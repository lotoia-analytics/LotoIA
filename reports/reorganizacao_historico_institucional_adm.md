# Reorganização do Histórico Institucional do ADM

## Estrutura anterior

- Mistura de rastreabilidade institucional com memória pós-conferência e memória científica legada.
- Exposição de termos sensíveis como recomendação operacional na área principal.
- Erro técnico de `Expanders may not be nested inside other expanders`.

## Nova estrutura por blocos

1. Cabeçalho institucional.
2. Estado da infraestrutura.
3. Rastreabilidade institucional principal.
4. Base oficial Lotofácil.
5. Memória pós-conferência observacional.
6. Memória consolidada da bateria conferida.
7. Histórico oficial Lotofácil.
8. Memória científica legada em quarentena documental.
9. Detalhes técnicos avançados recolhidos.

## Correção técnica aplicada

- O bloco de diagnóstico histórico deixou de ser um `expander` externo que abrigava outros `expanders`.
- O conteúdo científico sensível foi movido para a seção recolhida `Memória científica legada — quarentena documental`.
- O painel científico passou a ser exibido apenas como documentação, sem comando operacional.

## Localização da correção

- `dashboard/institutional_app.py`
- Função principal afetada: `_render_history_institutional_page`
- Função de apoio ajustada: `_render_scientific_policy_panel`

## Termos sensíveis preservados em quarentena documental

- `scientific_calibration_decisions`
- `recommended_action`
- `recalibrate_from_*`
- `LEI DESCOBERTA E SELECIONADA`
- `Lei Científica da Geração`
- `cross_validated_scientific_batch_memory`
- `policy_id`
- `selection_score`
- `selected_at`
- `risk_overfit`
- `confidence`
- `dominant_memory`
- `selection_variant`

## Garantias

- Dados preservados.
- Nenhuma lógica funcional alterada.
- Banco, endpoints, geração, conferência e simulação intactos.
- Lei 15 soberana preservada.

## Validações executadas

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

## Riscos residuais

- A página continua extensa por natureza institucional, mas agora os blocos sensíveis estão recolhidos e separados.
- Alguns rótulos técnicos continuam existindo no payload legado, apenas não dominam a camada principal.
