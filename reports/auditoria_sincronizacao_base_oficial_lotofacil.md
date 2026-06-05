# Auditoria de Sincronização da Base Oficial Lotofácil

## Objetivo

Auditar a consolidação da base oficial Lotofácil entre CSV histórico, importação via API e persistência institucional no banco.

## Estado do CSV

- Último concurso no CSV: `3700`
- Total de concursos no CSV: `3699`
- Uso: seed histórico/preservação documental
- Papel: o CSV não deve ser tratado como verdade final quando a base persistida já estiver mais atualizada

## Estado do banco local validado

### `imported_contests`

- COUNT: `4`
- MIN/MAX: `3697 / 3700`
- Últimos concursos: `3700, 3699, 3698, 3697`

### `lotofacil_official_history`

- COUNT: `4`
- MIN/MAX: `3697 / 3700`
- Últimos concursos: `3700, 3699, 3698, 3697`
- Concursos 3700/3701/3702 verificados explicitamente
  - `3700`: presente
  - `3701`: ausente no banco local validado
  - `3702`: ausente no banco local validado

### Lacunas

- Lacunas detectadas no banco local validado: `nenhuma` entre `3697` e `3700`
- Entre o último importado esperado no runtime e a base oficial persistida, a correção passa a considerar o último importado como teto de diagnóstico, evitando falso positivo de base incompleta.

## Estado da importação via API

- O botão `Importar último resultado oficial` aciona `ResultSyncService.sync_latest()`
- A rotina persiste em `imported_contests` e `lotofacil_official_history` via `ContestRepository.save_contest()`
- Após a sincronização, a rotina foi reforçada para:
  - executar reconciliação adicional de `lotofacil_official_history` a partir de `imported_contests`
  - recomputar os diagnósticos oficiais com base no último concurso importado e não apenas no intervalo interno da tabela oficial

## Causa da divergência observada no runtime

- O diagnóstico institucional podia ficar marcado como `INCOMPLETA` quando o último concurso importado no runtime estava à frente do recorte já persistido na base oficial.
- A correção passou a tratar o último importado como teto de referência para cálculo de lacunas.

## Correção aplicada

- `dashboard/institutional_app.py`
- Ajuste em `_load_official_history_diagnostics()` para calcular lacunas até o maior entre:
  - último concurso da base oficial
  - último concurso importado
- Ajuste em `_sync_latest_official_result_now()` para:
  - executar reconciliação oficial pós-importação
  - persistir o diagnóstico oficial consolidado após a sincronização

## Queries executadas

- `SELECT COUNT(*) FROM imported_contests`
- `SELECT MIN(contest_number), MAX(contest_number) FROM imported_contests`
- `SELECT contest_number FROM imported_contests ORDER BY contest_number DESC LIMIT 10`
- `SELECT * FROM imported_contests WHERE contest_number IN (3700, 3701, 3702)`
- `SELECT COUNT(*) FROM lotofacil_official_history`
- `SELECT MIN(contest_number), MAX(contest_number) FROM lotofacil_official_history`
- `SELECT contest_number FROM lotofacil_official_history ORDER BY contest_number DESC LIMIT 10`
- `SELECT * FROM lotofacil_official_history WHERE contest_number IN (3700, 3701, 3702)`

## Validação após correção

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py tests/test_result_sync_service.py -q`

Resultado:

- `30 passed`
- 1 warning de cache do pytest no ambiente

## Confirmação institucional

- Nenhuma lógica de Lei 15 foi alterada.
- Nenhuma memória científica ou calibração foi alterada.
- A correção é de sincronização/persistência e de diagnóstico da base oficial.
- O CSV permanece como seed histórico/documental, não como verdade final quando a base persistida estiver consolidada.
