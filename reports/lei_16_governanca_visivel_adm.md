# Lei 16 no ADM - Governança Visível

## Objetivo

Expor a Lei 16 no painel institucional do ADM apenas como leitura documental, sem criar botão, controle, seletor, parâmetro ou modo alternativo de geração.

## Página afetada

- `dashboard/institutional_app.py`

## Seção adicionada

- `Lei 16 — Integridade Global da Geração`

## Conteúdo exibido

- status da lei como formalizada documentalmente
- classificação como compatível com a Lei 15
- aderência institucional alta
- explicação de que a Lei 16 garante:
  - duplicados globais zero
  - memória de assinaturas compartilhada entre grupos
  - unicidade por jogo entregue
  - soberania inalterada da Lei 15

## O que não foi criado

- nenhum botão
- nenhum controle operacional
- nenhum seletor
- nenhum parâmetro de geração
- nenhuma recalibração
- nenhuma alternativa de estratégia

## Confirmação institucional

- a Lei 16 aparece como governança visível
- a Lei 15 permanece soberana
- a alteração é apenas documental/visual

## Validação

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

