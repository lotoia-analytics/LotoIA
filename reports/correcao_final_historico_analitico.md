# Correção final do Histórico Analítico

## Função/bloco alterado

- `dashboard/institutional_app.py`
- Bloco `_render_analytical_page(snapshot)`

## Strings de acentuação corrigidas

- `Histórico Analítico`
- `Visão`
- `gerações`
- `histórico`
- `conferíveis`
- `conferível`
- `secundária`
- `analítica`
- `diagnóstico`

## Mensagem amarela antiga e nova

- Antiga: `Bateria estruturalmente aprovada, mas cientificamente reprovada. Disponível para diagnóstico/conferência supervisionada.`
- Nova: `Bateria estruturalmente conferível. Diagnóstico científico preservado apenas como registro observacional, sem comando operacional.`

## Tratamento dado a `REPROVADO`

- Permanece apenas como valor técnico em memória/expansão técnica.
- Não aparece como decisão principal na tabela observacional.

## Tratamento dado a `NEAR_MISS_GLOBAL`

- Permanece como classificação técnica/legada.
- Não aparece como comando principal na área visível.

## Tratamento dado a `recalibrate_from_*`

- Valores brutos foram mantidos apenas em detalhes técnicos avançados / quarentena documental.
- A área principal mostra apenas o rótulo observacional legado.

## Confirmação institucional

- Valores brutos ficaram restritos aos detalhes técnicos.
- A página continua analítica e observacional.
- A página não gera jogos, não recalibra a Lei 15 e não altera histórico.

## Testes executados

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

Resultado:

- `26 passed`

## Observação

- A tabela de jogos históricos conferíveis continua visível.
- O diagnóstico legado permanece disponível, mas rebaixado institucionalmente.
