# Implementação da Segunda Tabela "Leitura Institucional da Matriz" no Painel ADM

## Resumo executivo

Foi adicionada ao Painel ADM uma segunda tabela visual e institucional, posicionada imediatamente abaixo da tabela técnica "Jogos gerados". A nova leitura usa os mesmos jogos já carregados na tela e não altera geração, Lei 15, RFE, conferência, schema ou persistência. O objetivo foi oferecer uma leitura institucional derivada da matriz já exibida, sem transformar a tabela em novo motor operacional.

## Decisão institucional

- A tabela técnica "Jogos gerados" permanece inalterada.
- A nova tabela "Leitura institucional da matriz" é apenas visual e derivada.
- O objeto auditado continua sendo o jogo já carregado na página.
- Não houve criação de nova geração, nova consulta de banco ou nova persistência.
- O rodapé técnico original foi preservado e um segundo rodapé institucional foi adicionado abaixo da nova tabela.

## Base usada

A nova tabela foi construída exclusivamente a partir da lista de jogos já carregada na tela da geração limpa Lei 15. Não há leitura adicional de fonte externa nem reconsulta à base oficial.

## Composição da camada visual

Campos expostos na nova tabela:

- `celula_matriz`
- `formato_d`
- `escala_top`
- `nucleo_a_dezenas`
- `referencias_auditadas_j12_j34`
- `vigilancia_j71`
- `status_institucional`
- `leitura_institucional`

### Regras de leitura

- Se houver referências J12/J34 e J71, o status é `NUCLEO_A_COM_REFERENCIA_E_VIGILANCIA`.
- Se houver referências J12/J34 apenas, o status é `NUCLEO_A_COM_REFERENCIA_AUDITADA`.
- Se houver J71 apenas, o status é `NUCLEO_A_COM_VIGILANCIA`.
- Caso contrário, o status é `NUCLEO_A`.

### Observação obrigatória

Se os campos `reservas_auditadas` e `cartao_final` aparecerem por herança técnica do sistema, isso não significa formato 20D nem expansão de dezenas nesta missão. O objeto auditado é o jogo 15D, com leitura institucional derivada apenas para visualização.

## Arquivos alterados

- `dashboard/institutional_app.py`
- `tests/test_clean_app_formats.py`

## Testes executados

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_clean_app_formats.py -q`

## Resultado dos testes

Os testes novos validam:

- inferência de célula matriz para `15D Top 20`
- leitura institucional de um jogo 15D com vigilância
- leitura institucional de um jogo 16D com referência e vigilância

## Conclusão institucional

A nova tabela foi implementada como leitura institucional visual, sem interferência no fluxo técnico de geração, sem alterar a Lei 15 e sem abrir qualquer nova camada operacional.

## Confirmações finais

- não houve nova geração
- não houve alteração da Lei 15
- não houve alteração de schema
- não houve alteração da RFE
- não houve alteração de conferência
- a tabela técnica original foi preservada
- o rodapé técnico original foi preservado
- não houve push para `origin/main`
