# Novo App Limpo Zero

## Objetivo
Criar um entrypoint limpo e independente em `dashboard/lotoia_clean_zero.py`, sem herdar layout, sidebar ou fluxos do dashboard antigo.

## O que foi entregue
- Novo app limpo em `dashboard/lotoia_clean_zero.py`.
- Módulo neutro de suporte em `dashboard/clean_core.py`.
- Persistência e leitura do histórico analítico sem depender do `institutional_app.py`.

## Interface
- Título: `LotoIA Clean`
- Subtítulo: `Gerador limpo 15/17/18`
- Seletor de quantidade de jogos
- Seletor de formato do cartão:
  - `15 dezenas — Núcleo Lei 15`
  - `17 dezenas — Lei 15 + 2 reservas auditadas`
  - `18 dezenas — Lei 15 + 3 reservas auditadas`
- Botão: `Gerar com Lei 15`

## Persistência
Os formatos 15, 17 e 18 são persistidos no histórico com:
- `núcleo_lei_15`
- `reservas_auditadas`
- `cartão_final`
- `formato_cartao`
- `quantidade_final`

## Validação
- `python -m py_compile dashboard/lotoia_clean_zero.py dashboard/clean_core.py dashboard/institutional_app.py`
- `python -m pytest tests/test_clean_app_formats.py -q`
- Resultado: `4 passed`

## Conclusão
O novo app limpo foi recriado como entrypoint zero, visualmente e tecnicamente independente do dashboard antigo, mantendo apenas o núcleo 15–17–18 aprovado.
