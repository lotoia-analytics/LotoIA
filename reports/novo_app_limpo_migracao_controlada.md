# Novo App Limpo - Migração Controlada

## Visão Geral
Foi criado um novo app limpo separado do app atual da LotoIA, preservando a página existente como backup operacional e referência institucional.

## Preservação do App Atual
- O app atual não foi desmontado.
- O app atual não foi apagado.
- O app atual não foi substituído.
- O app atual permanece intacto como backup operacional.

## Novo App
- Arquivo principal: `dashboard/clean_app.py`
- Escopo: núcleo institucional aprovado, sem legado ativo.
- Fluxo:
  - usuário escolhe `15 / 17 / 18`
  - clica `Gerar com Lei 15`
  - Lei 15 gera o núcleo
  - 17/18 aplicam expansão auditada
  - Lei 17 valida 12+
  - Lei 18 valida 13+

## Arquitetura Institucional
- Lei 15 = única COMMANDER da geração
- Lei 15 gera base 11+ com busca contínua por 14 e 15
- Lei 17 = validação pós-geração 12+ com busca contínua por 14 e 15
- Lei 18 = validação pós-geração 13+ com busca contínua por 14 e 15
- Formato 15 = núcleo Lei 15
- Formato 17 = núcleo Lei 15 + 2 reservas auditadas
- Formato 18 = núcleo Lei 15 + 3 reservas auditadas

## Persistência no Histórico
O novo app persiste:
- núcleo_lei_15
- reservas_auditadas
- cartão_final
- formato_cartao
- quantidade_final

## Testes de Integridade
Validações executadas com sucesso:
- `python -m py_compile dashboard/institutional_app.py dashboard/clean_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py tests/test_clean_app_formats.py -q`
- Resultado: `30 passed`

## Deploy Separado
A criação do deploy separado foi tentada, mas a plataforma retornou limite de quota para criação de novo projeto.
O app limpo ficou criado no repositório e pronto para deploy assim que houver quota disponível.

## Desacoplamento do App Antigo
O entrypoint `dashboard/clean_app.py` foi desacoplado do `dashboard/institutional_app.py` e passou a usar `dashboard/clean_core.py` com helpers neutros e funções puras necessárias para execução independente no Render.

Com isso, o novo app não depende diretamente do entrypoint antigo como base de execução.

## Comando de Execução
```bash
streamlit run dashboard/clean_app.py --server.port $PORT --server.address 0.0.0.0
```

## Conclusão
O novo app limpo foi criado em ambiente separado, preservando o app atual como backup operacional. A Lei 15 permanece como única comandante da geração, Lei 17 e Lei 18 permanecem como validações pós-geração, e os formatos 17/18 são apenas expansão auditada do núcleo 15, sem recalibração, sem legado ativo e sem redesenho arquitetural.
