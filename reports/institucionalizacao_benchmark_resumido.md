# Institucionalização do Benchmark Resumido

## Página corrigida

- `Benchmark resumido`

## Função/bloco alterado

- `_render_benchmark_resumido_page`

## Cards técnicos removidos da área principal

- `generated_games`
- `reconciliation_runs`
- `imported_contests`
- `latest_generation`

## JSON bruto removido da área principal

- `Última geração`
- `Última reconciliação`

## Campos de última geração traduzidos

- Identificador da geração
- Seed registrada
- Total de jogos
- Concurso alvo

## Campos de última conferência traduzidos

- Identificador da conferência
- Concurso conferido
- Geração conferida
- Status
- Faixas premiadas
- Total de acertos somados
- Maior acerto
- Jogos conferidos

## Dezenas conferidas renderizadas em formato legível

- `matched_numbers` passou a ser exibido como lista textual de dezenas

## Distribuição de acertos renderizada em tabela

- `hit_distribution` passou a ser exibida como tabela legível

## Aviso institucional adicionado

- `Esta página é observacional e institucional. Não gera jogos, não recalibra a Lei 15, não altera a Lei 16 e não modifica histórico.`

## Interpretação institucional adicionada

- a leitura do benchmark foi descrita como visão sintética dos indicadores operacionais persistidos

## Detalhes técnicos movidos para expander

- a geração e a reconciliação brutas ficaram no expander `Detalhes técnicos avançados`

## Confirmações institucionais

- Lei 15 não alterada
- Lei 16 não alterada
- nenhuma lógica de geração alterada
- nenhuma persistência alterada

## Testes executados

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`
- `python -m pytest tests/test_global_batch_deduplication.py -q`

## Resultado dos testes

- compilação: OK
- pytest núcleo: OK
- pytest deduplicação global: OK

## Print final da tela

- não capturado nesta execução

## Commit

- a ser preenchido após publicação

## Critério de aceite final

- a página deve exibir apenas leitura institucional na área principal
- os dados brutos devem permanecer recolhidos no expander técnico
