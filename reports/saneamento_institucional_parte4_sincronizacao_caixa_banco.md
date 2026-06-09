# Saneamento Institucional - Parte 4: Sincronizacao Banco Ativo x Fonte Oficial Caixa/RFE

## 1. Resumo executivo

Esta parte auditou, sem alterar dados, o banco ativo do Painel ADM e comparou suas tabelas reais `imported_contests` e `contests` contra a fonte oficial da Caixa acessada pelo cliente institucional do projeto.

Conclusao executiva:
- o banco ativo foi identificado com exatidao;
- `imported_contests` e `contests` sao consistentes entre si nos concursos compartilhados;
- a fonte oficial da Caixa esta acessivel via `CaixaApiClient`;
- o banco ativo esta **defasado** em relacao a Caixa, pois nao possui todos os concursos oficiais ja disponiveis;
- nao houve alteracao de dados, schema, banco ou painel durante a auditoria.

Classificacao final:
- **PARTE_4_BLOQUEADA_BANCO_DEFASADO**

---

## 2. Base herdada das Partes 1, 2 e 3

- Parte 1: identificacao do repositorio candidato.
- Parte 2: identificacao do painel ativo.
- Parte 3: identificacao do banco ativo do painel.

Esta Parte 4 preserva o mesmo repositorio candidato e o mesmo painel ativo observados nas etapas anteriores:

- `REPO_ROOT_CANDIDATO = C:\Projetos\LotoIA`
- painel ativo: `dashboard/institutional_app.py`
- porta: `8501`
- URL: `http://localhost:8501`
- banco ativo: `C:\Projetos\LotoIA\data\lotoia.db`

---

## 3. Banco ativo confirmado

- **Banco ativo**: `C:\Projetos\LotoIA\data\lotoia.db`
- **Tipo**: SQLite local
- **Tamanho**: `7012352` bytes
- **Ultima modificacao observada**: `07/06/2026 15:09:08`
- **WAL presente**: `sim` (`data\lotoia.db-wal`)
- **SHM presente**: `sim` (`data\lotoia.db-shm`)
- **Painel Streamlit aberto**: `sim`
  - PID observado: `7864`
  - comando observado: `C:\Python314\python.exe -m streamlit run dashboard/institutional_app.py --server.port 8501 --server.headless true`

### Hash do banco

- **Hash antes da auditoria**: `07d33c50a4a94844870564e24f023a45798a89c4a6882c62e7ebff2bff7ee250`
- **Hash depois da auditoria**: `07d33c50a4a94844870564e24f023a45798a89c4a6882c62e7ebff2bff7ee250`
- **Mudou?**: nao

---

## 4. Leitura de `imported_contests`

### Estrutura observada

- colunas:
  - `contest_number`
  - `created_at`
  - `data`
  - `dezenas`
  - `metadata_json`

### Consolidado

- total de registros: `8`
- menor concurso: `3689`
- maior concurso: `3704`
- concursos presentes:
  - `3689`
  - `3697`
  - `3698`
  - `3699`
  - `3700`
  - `3702`
  - `3703`
  - `3704`
- concursos faltantes na faixa oficial observada:
  - `3690`
  - `3691`
  - `3692`
  - `3693`
  - `3694`
  - `3695`
  - `3696`
  - `3701`
- duplicados: nenhum
- registros invalidos: nenhum
- status: `PARCIALMENTE_PREENCHIDA`

### Ultimo registro

- concurso: `3704`
- data: `06/06/2026`
- dezenas: `01,03,04,09,10,11,12,13,14,15,19,20,22,23,25`

---

## 5. Leitura de `contests`

### Estrutura observada

- colunas:
  - `concurso`
  - `data`
  - `dezenas`

### Consolidado

- total de registros: `8`
- menor concurso: `3689`
- maior concurso: `3704`
- concursos presentes:
  - `3689`
  - `3697`
  - `3698`
  - `3699`
  - `3700`
  - `3702`
  - `3703`
  - `3704`
- concursos faltantes na faixa oficial observada:
  - `3690`
  - `3691`
  - `3692`
  - `3693`
  - `3694`
  - `3695`
  - `3696`
  - `3701`
- duplicados: nenhum
- registros invalidos: nenhum
- status: `PARCIALMENTE_PREENCHIDA`

### Ultimo registro

- concurso: `3704`
- data: `06/06/2026`
- dezenas: `01,03,04,09,10,11,12,13,14,15,19,20,22,23,25`

---

## 6. Consistencia entre `imported_contests` e `contests`

Os concursos compartilhados entre as duas tabelas batem em data e dezenas.

### Status por concurso comparavel

| Concurso | imported_contests | contests | Status |
|---|---|---|---|
| 3689 | `19/05/2026` / `01,02,04,05,06,07,08,09,10,11,12,13,14,15,16` | `19/05/2026` / `01,02,04,05,06,07,08,09,10,11,12,13,14,15,16` | OK |
| 3697 | `28/05/2026` / `01,05,06,07,09,10,13,15,17,18,19,20,21,24,25` | `28/05/2026` / `01,05,06,07,09,10,13,15,17,18,19,20,21,24,25` | OK |
| 3698 | `29/05/2026` / `01,03,05,06,07,08,09,10,12,13,16,18,20,21,23` | `29/05/2026` / `01,03,05,06,07,08,09,10,12,13,16,18,20,21,23` | OK |
| 3699 | `30/05/2026` / `01,02,03,05,06,08,09,11,14,18,20,21,22,24,25` | `30/05/2026` / `01,02,03,05,06,08,09,11,14,18,20,21,22,24,25` | OK |
| 3700 | `01/06/2026` / `01,03,07,08,09,10,12,13,14,17,18,19,20,23,25` | `01/06/2026` / `01,03,07,08,09,10,12,13,14,17,18,19,20,23,25` | OK |
| 3702 | `03/06/2026` / `02,03,05,09,13,14,15,16,17,18,20,21,22,23,25` | `03/06/2026` / `02,03,05,09,13,14,15,16,17,18,20,21,22,23,25` | OK |
| 3703 | `05/06/2026` / `01,03,05,07,08,09,10,14,15,17,21,22,23,24,25` | `05/06/2026` / `01,03,05,07,08,09,10,14,15,17,21,22,23,24,25` | OK |
| 3704 | `06/06/2026` / `01,03,04,09,10,11,12,13,14,15,19,20,22,23,25` | `06/06/2026` / `01,03,04,09,10,11,12,13,14,15,19,20,22,23,25` | OK |

### Divergencias registradas

- Nenhuma divergencia entre `imported_contests` e `contests` nos concursos comparaveis.
- A divergencia encontrada e entre o banco local e a fonte oficial da Caixa, por ausencia de concursos no banco.

---

## 7. Fonte oficial / RFE identificada

### Fonte oficial usada

- **Fonte oficial**: Caixa Lotofacil via cliente institucional do projeto
- **Arquivo responsavel**: `src/lotoia/ingestion/caixa_api_client.py`
- **Metodo de consulta**:
  - `fetch_latest()`
  - `fetch_contest(contest_number)`
- **Endpoint oficial**:
  - `https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil`

### Observacao sobre RFE

- A RFE do projeto usa o contexto institucional do banco e do painel.
- Para esta auditoria, a referencia oficial foi obtida diretamente pela API da Caixa, sem escrita no banco.

---

## 8. Metodologia de consulta oficial

Consulta feita em modo somente leitura, sem INSERT/UPDATE/DELETE.

### Faixa consultada

- faixa completa entre o menor e o maior concurso presentes no banco ativo:
  - `3689` a `3704`

### Ultimo concurso oficial identificado

- **Ultimo concurso oficial**: `3704`
- **Data do ultimo oficial**: `06/06/2026`
- **Dezenas do ultimo oficial**: `01 03 04 09 10 11 12 13 14 15 19 20 22 23 25`
- **Total de concursos obtidos na referencia**: `16`

---

## 9. Comparacao banco x fonte oficial

### Resultado geral

O banco ativo nao contem todos os concursos oficiais ja disponiveis na fonte Caixa.

### Concursos OK

- `3689`
- `3697`
- `3698`
- `3699`
- `3700`
- `3702`
- `3703`
- `3704`

### Concursos faltantes no banco

- `3690`
- `3691`
- `3692`
- `3693`
- `3694`
- `3695`
- `3696`
- `3701`

### Concursos faltantes na fonte oficial

- nenhum, dentro da faixa consultada e acessivel

### Defasagem em concursos

- banco ativo: `8` concursos
- fonte oficial: `16` concursos
- defasagem: `8` concursos

---

## 10. Classificacao de sincronizacao institucional

### Classificacao final

- **DEFASADO_EM_RELACAO_CAIXA**

### Motivo

- Os concursos existentes no banco batem com a Caixa.
- O banco, porem, possui menos concursos que a fonte oficial.
- Ha lacunas internas em relacao ao conjunto oficial disponivel.

---

## 11. Hash depois da auditoria

- **Hash depois**: `07d33c50a4a94844870564e24f023a45798a89c4a6882c62e7ebff2bff7ee250`
- **Mudou?**: nao
- **Escrita indevida?**: nao identificada

---

## 12. Riscos criticos

1. **Defasagem em relacao a Caixa**
   - o banco ativo nao contem todos os concursos oficiais ja publicados.

2. **Schema institucional divergente**
   - o banco ativo usa `contests` e `imported_contests` como referencia local.
   - a tabela `official_lotofacil_history` nao existe no schema observado nesta sessao.

3. **Risco de fallback silencioso**
   - o painel possui caminhos de leitura alternativos e diagnosticos de sincronizacao.
   - a rastreabilidade depende de manter claro qual fonte foi consultada.

4. **Arquivo em uso**
   - o banco esta aberto pelo processo Streamlit.

---

## 13. Pendencias para Parte 4B

A Parte 4B so deve existir se houver autorizacao posterior para correcao ou reconcilacao.

Possiveis pendencias:
- restaurar a continuidade dos concursos ausentes;
- alinhar a tabela oficial do banco ao historico completo da Caixa;
- consolidar explicitamente a fonte institucional unica para conferencias futuras.

---

## 14. Conclusao institucional

A auditoria confirma que `imported_contests` e `contests` sao consistentes entre si nos concursos que compartilham, mas o banco ativo do Painel ADM esta **defasado em relacao a Caixa** porque nao possui todos os concursos oficiais ja disponiveis na fonte oficial consultada.

O hash do banco foi preservado durante toda a auditoria, e nenhuma alteracao foi feita no banco, schema, painel ou fonte oficial.

### Status final da Parte 4

- **PARTE_4_BLOQUEADA_BANCO_DEFASADO**

### Confirmacoes finais

- houve ou nao alteracao de dados: **nao**
- houve ou nao push: **nao**
- o hash do banco foi preservado: **sim**
- `imported_contests` e `contests` sao consistentes entre si: **sim**
- o banco ativo bate com a fonte oficial: **nao integralmente**
- o ultimo concurso oficial: **3704**
- o banco esta defasado: **sim**
- houve divergencia de dezenas: **nao nos concursos comparaveis**

