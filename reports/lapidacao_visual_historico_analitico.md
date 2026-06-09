# Lapidação visual do Histórico Analítico

## Função/bloco alterado

- `dashboard/institutional_app.py`
- Bloco `_render_analytical_page(snapshot)`

## Labels técnicos substituídos

- `TOTAL_GENERATION_EVENTS_CARREGADOS` → `Gerações carregadas`
- `TOTAL_JOGOS_HISTORICOS_CARREGADOS` → `Jogos históricos carregados`
- `JOGOS_CONFERIVEIS` → `Jogos conferíveis`
- `JOGOS_DIAGNOSTICO` → `Jogos em diagnóstico`
- `GENERATION_EVENT_ID_MAIS_ANTIGO` → `Geração mais antiga`
- `GENERATION_EVENT_ID_MAIS_RECENTE` → `Geração mais recente`

## Colunas renomeadas visualmente

- `generation_event_id` → `ID da geração`
- `batch_id` → `Bateria`
- `data/hora` → `Data/hora`
- `jogo n°` → `Jogo`
- `dezenas` → `Dezenas`
- `formato_cartao` → `Formato`
- `núcleo_lei_15` → `Núcleo Lei 15`
- `reservas_auditadas` → `Reservas auditadas`
- `cartão_final` → `Cartão final`
- `quantidade_nucleo` → `Núcleo`
- `quantidade_reservas` → `Reservas`
- `quantidade_final` → `Total final`
- `estratégia` → `Estratégia`
- `score` → `Score`
- `tipo visual` → `Tipo`
- `origem/modelo` → `Origem/modelo`
- `status de conferência` → `Status de conferência`
- `concurso conferido` → `Concurso conferido`
- `acertos` → `Acertos`
- `premiação` → `Premiação`

## Diagnóstico legado preservado

- `Diagnóstico observacional legado` foi mantido.
- O texto de quarentena documental permaneceu intacto.
- A mensagem de conferência estrutural foi mantida como registro observacional sem comando operacional.

## Confirmação institucional

- Nenhuma lógica funcional foi alterada
- Nenhuma query foi modificada
- Nenhum dado persistido foi alterado
- A página segue observacional e institucional

## Testes executados

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

Resultado:

- `26 passed`

## Observação

- A tradução visual foi aplicada apenas na superfície da interface.
- Os nomes técnicos permanecem preservados internamente para compatibilidade e rastreabilidade.
