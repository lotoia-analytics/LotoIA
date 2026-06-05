# Auditoria SQL e Corre??o Integrada da Base Oficial Lotof?cil

## Objetivo

Registrar, por SQL objetiva, o estado real da base oficial Lotof?cil e a corre??o aplicada na visualiza??o e sincroniza??o do ADM.

## Provas SQL objetivas

### 1) Concursos 3700, 3701 e 3702

```sql
SELECT concurso, data
FROM official_lotofacil_history
WHERE concurso IN (3700, 3701, 3702)
ORDER BY concurso;
```

Resultado obtido no banco local:

| concurso | data |
| --- | --- |
| 3700 | 01/06/2026 |
| 3702 | 03/06/2026 |

Diagn?stico objetivo:
- `3700` existe no banco = **sim**
- `3701` existe no banco = **n?o**
- `3702` existe no banco = **sim**
- ?ltimo concurso no banco = **3702**
- total de registros no banco = **5**
- lacunas encontradas = **3701**

### 2) ?ltimos 10 concursos oficiais persistidos

```sql
SELECT concurso, data
FROM official_lotofacil_history
ORDER BY concurso DESC
LIMIT 10;
```

Resultado obtido no banco local:

| concurso | data |
| --- | --- |
| 3702 | 03/06/2026 |
| 3700 | 01/06/2026 |
| 3699 | 30/05/2026 |
| 3698 | 29/05/2026 |
| 3697 | 28/05/2026 |

Observa??o:
- o banco possui apenas 5 registros oficiais no recorte local validado, ent?o os 10 ?ltimos exibem os 5 existentes.
- a se??o do ADM foi corrigida para abrir com os concursos mais recentes, e n?o com os primeiros concursos da s?rie.

### 3) Contagem e intervalo

```sql
SELECT COUNT(*) FROM official_lotofacil_history;
SELECT MIN(concurso), MAX(concurso) FROM official_lotofacil_history;
```

Resultado obtido no banco local:
- `COUNT(*) = 5`
- `MIN(concurso) = 3697`
- `MAX(concurso) = 3702`

### 4) Lacunas

Lacuna calculada no intervalo oficial persistido:
- `3701`

## Diagn?stico do CSV

Arquivo analisado:
- `data/raw/historico_lotofacil.csv`

Resultado:
- ?ltimo concurso no CSV = `3700`
- total de linhas no CSV = `3699`

Conclus?o:
- o CSV est? defasado e continua sendo seed/documento hist?rico.
- ele n?o deve ser tratado como verdade final quando a base persistida est? mais atualizada.

## Diagn?stico da API Caixa

Situa??o observada na sincroniza??o:
- `HTTP 403 Forbidden`
- isso n?o pode ser tratado como sucesso.
- `commit_state=false` n?o pode ser interpretado como persist?ncia v?lida.
- `rollback=true` deve permanecer como falha de sincroniza??o.

## Persist?ncia do concurso 3702

O banco local validado cont?m `3702` em:
- `imported_contests`
- `lotofacil_official_history`

Persist?ncia confirmada por consulta SQL objetiva.

## Tratamento do concurso 3701

O concurso `3701` foi verificado explicitamente e est? ausente no banco local validado.

Status institucional:
- `Base oficial incompleta por aus?ncia do concurso 3701.`

## Corre??o aplicada na visualiza??o do ADM

A se??o **Hist?rico Oficial Lotof?cil** foi ajustada para exibir inicialmente os **10 concursos oficiais mais recentes persistidos no banco**, em ordem decrescente.

Texto institucional da se??o:
- `?ltimos 10 concursos oficiais persistidos no banco.`

A tabela do ADM agora deve bater com:

```sql
SELECT concurso, data
FROM official_lotofacil_history
ORDER BY concurso DESC
LIMIT 10;
```

## Corre??o aplicada na sincroniza??o

Foi mantido e refor?ado o fluxo para:
- tratar `HTTP 403` como falha real;
- n?o gerar falso sucesso;
- permitir fallback manual controlado apenas para `3702`, quando validado;
- n?o sobrescrever dados v?lidos com vazio;
- n?o duplicar concursos j? persistidos.

## Testes executados

- `python -m py_compile dashboard/institutional_app.py src/lotoia/ingestion/caixa_api_client.py src/lotoia/ingestion/result_sync_service.py`
- `python -m pytest tests/test_result_sync_service.py tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

Resultado:
- `31 passed`
- 1 warning de cache do pytest no ambiente

## Confirma??o final

- Nenhuma l?gica da Lei 15 foi alterada.
- Nenhuma mem?ria cient?fica ou calibra??o foi alterada.
- A corre??o ? de auditoria SQL, ordena??o de exibi??o, sincroniza??o/persist?ncia e fallback controlado da base oficial.
