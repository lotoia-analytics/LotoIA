# Auditoria SQL e Sincroniza??o CSV/Banco da Base Oficial Lotof?cil

## Objetivo

Separar com prova objetiva o estado do PostgreSQL, do CSV versionado e da sincroniza??o oficial da Caixa.

## Prova SQL do banco local

### Concurso 3700, 3701 e 3702

```sql
SELECT concurso, data, fonte, status, imported_at
FROM official_lotofacil_history
WHERE concurso IN (3700, 3701, 3702)
ORDER BY concurso;
```

Resultado obtido no banco local validado:

| concurso | data | fonte | status | imported_at |
| --- | --- | --- | --- | --- |
| 3700 | 01/06/2026 | imported_contests | OK | 2026-06-02 20:04:20 |
| 3702 | 03/06/2026 | imported_contests | OK | 2026-06-05 00:54:22 |

Diagn?stico objetivo:
- `3700` existe no banco = **sim**
- `3701` existe no banco = **n?o**
- `3702` existe no banco = **sim**
- ?ltimo concurso no banco = **3702**
- total de registros no banco = **5**
- lacunas encontradas = **3701**
- fonte do `3701` = **ausente no banco local validado**
- fonte do `3702` = **imported_contests**

### ?ltimos 10 concursos do banco

```sql
SELECT concurso, data, fonte, status, imported_at
FROM official_lotofacil_history
ORDER BY concurso DESC
LIMIT 10;
```

Resultado obtido no banco local validado:

| concurso | data | fonte | status | imported_at |
| --- | --- | --- | --- | --- |
| 3702 | 03/06/2026 | imported_contests | OK | 2026-06-05 00:54:22 |
| 3700 | 01/06/2026 | imported_contests | OK | 2026-06-02 20:04:20 |
| 3699 | 30/05/2026 | imported_contests | OK | 2026-06-02 20:04:20 |
| 3698 | 29/05/2026 | imported_contests | OK | 2026-06-02 20:04:20 |
| 3697 | 28/05/2026 | imported_contests | OK | 2026-06-02 20:04:20 |

### Contagem e limites

```sql
SELECT COUNT(*) FROM official_lotofacil_history;
SELECT MIN(concurso), MAX(concurso) FROM official_lotofacil_history;
```

Resultado:
- `COUNT(*) = 5`
- `MIN(concurso) = 3697`
- `MAX(concurso) = 3702`

### Lacunas

```sql
WITH seq AS (
  SELECT generate_series(
    (SELECT MIN(concurso) FROM official_lotofacil_history),
    (SELECT MAX(concurso) FROM official_lotofacil_history)
  ) AS concurso
)
SELECT seq.concurso
FROM seq
LEFT JOIN official_lotofacil_history h USING (concurso)
WHERE h.concurso IS NULL
ORDER BY seq.concurso;
```

Resultado:
- `3701`

## Auditoria do CSV

Arquivo auditado:
- `data/raw/historico_lotofacil.csv`

Resultado atual:
- último concurso no CSV = **3700**
- total de linhas no CSV = **3699**
- `3701` presente no CSV = **não**
- `3702` presente no CSV = **não**

### Classifica??o institucional do CSV

O CSV é tratado como:
- **seed/documentação histórica** da base oficial;
- não é a fonte viva/runtime;
- a fonte viva/runtime é o **PostgreSQL institucional**.

Conclusão institucional:
- o CSV permanece como artefato histórico/versionado, mas não é a fonte viva do runtime;
- a divergência observada no GitHub era de artefato desatualizado, não de lógica da Lei 15;
- por ausência de payload oficial válido para `3701`, o CSV não foi expandido com concursos inventados.

## Diagn?stico da API Caixa

Estado observado na sincroniza??o:
- `HTTP 403 Forbidden` pode ocorrer e deve ser tratado como falha real;
- `commit_state=true` n?o pode ser inferido em caso de 403;
- `rollback=true` deve permanecer como falha de sincroniza??o;
- fallback manual controlado segue restrito ao payload validado de `3702`.

## Valida??o no ADM

A seção **Histórico Oficial Lotofácil** foi corrigida para mostrar:
- últimos concursos persistidos no banco;
- ordem padrão `concurso DESC`;
- texto institucional explícito de que o CSV é seed/documentação e o runtime oficial é PostgreSQL.

Confirmação visual/funcional esperada:
- `3702` aparece no ADM = **sim**
- `3701` aparece no ADM = **não**
- `3700` aparece no ADM = **sim**
- ordenação = **concurso DESC**

## Corre??o aplicada

- reversão do arquivo versionado `data/raw/historico_lotofacil.csv` para preservar o histórico completo;
- ajuste do texto da camada de fontes no ADM para explicitar o papel de seed/documentação do CSV;
- manutenção da sincronia entre exportação de histórico e banco, sem tratar o CSV como runtime.

## Testes executados

- `python -m py_compile dashboard/institutional_app.py`
- `python -m py_compile src/lotoia/ingestion/caixa_api_client.py src/lotoia/ingestion/result_sync_service.py`
- `python -m pytest tests/test_result_sync_service.py tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

Resultado:
- `31 passed`
- 1 warning de cache do pytest no ambiente

## Confirma??o final

- Nenhuma l?gica da Lei 15 foi alterada.
- Nenhuma mem?ria cient?fica ou calibra??o foi alterada.
- A corre??o ? de auditoria SQL, sincroniza??o CSV/banco, visualiza??o e documenta??o da base oficial.
