# Contenção de Performance do ADM Antigo

## Causa provável do peso
- Abertura do Histórico Analítico materializava histórico completo com `limit=None`.
- O Histórico Institucional carregava timelines e resumos extensos logo na renderização.
- Blocos institucionais globais exibiam payloads e diagnósticos mesmo quando não eram necessários.

## Páginas afetadas
- `Histórico Analítico`
- `Histórico Institucional`
- navegação geral do ADM antigo reestruturado

## Ajustes feitos
- Criação de carregamento leve para histórico:
  - `\_load_generation_history_light(limit=25)`
  - `\_load_reconciliation_history_light(limit=25)`
  - `\_load_institutional_timeline_light(limit=25)`
  - `\_load_accumulated_analytical_rows_light(limit=25)`
- Limite inicial de abertura do Histórico Analítico para os últimos 25 registros.
- Limite inicial de timeline do Histórico Institucional para os últimos 25 eventos.
- Mensagem clara de carga inicial leve e expansão sob demanda.

## Limites aplicados
- Janela inicial leve: últimos 25 eventos.
- Histórico ampliado permanece disponível via navegação/filtros já existentes.

## Consultas otimizadas
- Substituição de carregamento completo por carregamento limitado na abertura.
- Redução da reconstrução inicial de linhas analíticas.
- Redução da timeline institucional exibida na primeira renderização.

## Validação do Histórico Analítico
- Continua acessível.
- Continua filtrável.
- Continua exibindo registros persistidos.
- Passa a abrir com carga inicial reduzida.

## Testes executados
- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

## Confirmação funcional
- Nenhuma lógica funcional foi alterada.
- A correção foi apenas de performance/renderização.

