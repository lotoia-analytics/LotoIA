# Saneamento Institucional - Parte 4B: Reconciliacao Controlada dos Concursos Faltantes Banco x Caixa

## 1. Resumo executivo

Esta parte executou uma reconciliação controlada do banco ativo do Painel ADM, inserindo exclusivamente os concursos faltantes previamente identificados na Parte 4 nas tabelas reais `imported_contests` e `contests`.

Resultado final:
- o backup pré-correção foi criado antes de qualquer escrita;
- os 8 concursos faltantes foram obtidos da Caixa via `CaixaApiClient`;
- os 8 concursos foram inseridos nas duas tabelas reais;
- a faixa 3689–3704 ficou sem lacunas;
- `imported_contests` e `contests` passaram a ficar consistentes entre si em toda a faixa auditada;
- o banco passou a bater com a Caixa na faixa auditada;
- o hash do arquivo principal mudou, como esperado após a persistência controlada.

Classificação final:
- **PARTE_4B_APROVADA_BANCO_RECONCILIADO_CAIXA**

---

## 2. Base herdada da Parte 4

Base institucional herdada da Parte 4:
- banco ativo identificado: `C:\Projetos\LotoIA\data\lotoia.db`
- tipo: SQLite local
- último concurso oficial: `3704`
- último concurso do banco antes da reconciliação: `3704`
- concursos faltantes no banco antes da correção:
  - `3690`
  - `3691`
  - `3692`
  - `3693`
  - `3694`
  - `3695`
  - `3696`
  - `3701`
- fonte oficial já auditada: Caixa Lotofácil via `src/lotoia/ingestion/caixa_api_client.py`

Status inicial:
- `BANCO_DEFASADO_CONFIRMADO`

---

## 3. Status inicial

Antes da reconciliação:
- `imported_contests` possuía `8` registros;
- `contests` possuía `8` registros;
- ambos estavam consistentes entre si nos concursos compartilhados;
- a faixa 3689–3704 apresentava lacunas internas;
- o banco estava defasado em relação à Caixa.

### Ação autorizada

- inserir apenas os concursos faltantes identificados na Parte 4;
- não alterar concursos já existentes;
- não criar tabela nova;
- não alterar schema;
- não alterar painel;
- não fazer push.

### Concursos autorizados

- `3690`
- `3691`
- `3692`
- `3693`
- `3694`
- `3695`
- `3696`
- `3701`

---

## 4. Banco ativo corrigido

- **Banco ativo**: `C:\Projetos\LotoIA\data\lotoia.db`
- **Tipo**: SQLite local
- **WAL presente**: sim
- **SHM presente**: sim
- **Painel Streamlit aberto**: sim
  - PID observado: `7864`
  - comando observado: `python -m streamlit run dashboard/institutional_app.py --server.port 8501 --server.headless true`

### Hash do banco

- **Hash antes da correção**: `07d33c50a4a94844870564e24f023a45798a89c4a6882c62e7ebff2bff7ee250`
- **Hash depois da correção**: `88fd31310a03682b894d646aa516af6befebe315efea8c80a3bdff1817a780ef`
- **Hash mudou?**: sim
- **Risco de alteração indevida**: não identificado

---

## 5. Backup pré-correção criado

### Backup físico

- **Caminho do backup**: `C:\Projetos\LotoIA\backups\db_pre_reconcile_lotoia_20260608_050237.db`
- **Criado antes de qualquer escrita**: sim
- **Tamanho**: `7012352` bytes
- **Data/hora observada**: `07/06/2026 15:09:08`

### Hash do backup

- **Hash do backup**: `07D33C50A4A94844870564E24F023A45798A89C4A6882C62E7EBFF2BFF7EE250`

### Arquivos de suporte observados

- `data\lotoia.db-wal`
- `data\lotoia.db-shm`

---

## 6. Concursos autorizados para correção

Concursos autorizados e efetivamente consultados na Caixa:
- `3690`
- `3691`
- `3692`
- `3693`
- `3694`
- `3695`
- `3696`
- `3701`

### Validação de formato

Todos os concursos acima apresentaram:
- exatamente 15 dezenas;
- dezenas entre `01` e `25`;
- sem duplicidade interna;
- data presente;
- número do concurso igual ao solicitado.

---

## 7. Dados oficiais obtidos da Caixa

Fonte:
- `CaixaApiClient`

Métodos:
- `fetch_latest()`
- `fetch_contest(contest_number)`

Endpoint:
- `https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil`

### Resumo dos concursos recuperados

| Concurso | Data oficial | Dezenas oficiais |
|---|---|---|
| 3690 | 20/05/2026 | 02 05 06 07 08 09 12 15 18 19 20 21 22 24 25 |
| 3691 | 21/05/2026 | 02 03 05 08 09 10 13 14 15 18 19 21 23 24 25 |
| 3692 | 22/05/2026 | 02 03 05 06 07 09 10 13 14 15 19 20 23 24 25 |
| 3693 | 23/05/2026 | 01 04 06 07 09 10 11 13 14 16 17 18 20 21 25 |
| 3694 | 25/05/2026 | 02 04 05 07 08 09 13 14 17 18 19 20 22 23 24 |
| 3695 | 26/05/2026 | 01 02 03 04 06 08 09 13 15 17 18 21 22 23 24 |
| 3696 | 27/05/2026 | 02 03 05 06 07 09 11 13 15 16 17 19 21 23 24 |
| 3701 | 02/06/2026 | 01 02 04 07 08 09 10 12 13 14 17 22 23 24 25 |

---

## 8. Validação de formato dos concursos oficiais

Todos os concursos oficiais obtidos tiveram validação positiva:
- quantidade de dezenas = `15`;
- faixa numérica válida;
- sem duplicidade interna;
- números alinhados ao concurso solicitado;
- datas oficiais presentes.

Status de consulta:
- `OK`

---

## 9. Ausência confirmada antes da inserção

Antes da escrita:
- cada um dos 8 concursos autorizados estava ausente em `imported_contests`;
- cada um dos 8 concursos autorizados estava ausente em `contests`;
- não havia inconsistência pré-existente entre as duas tabelas para esses concursos;
- a ação planejada foi inserir nos dois lugares.

---

## 10. Inserções feitas em `imported_contests`

Concursos inseridos:
- `3690`
- `3691`
- `3692`
- `3693`
- `3694`
- `3695`
- `3696`
- `3701`

### Mapeamento aplicado

- `contest_number` = número do concurso
- `created_at` = timestamp atual de auditoria
- `data` = data oficial
- `dezenas` = dezenas oficiais em formato CSV com vírgula, preservando o padrão da tabela
- `metadata_json` = payload bruto oficial da Caixa

### Resultado

- inserções concluídas sem sobrescrever registros existentes
- sem `INSERT OR REPLACE`
- sem alteração de concursos já existentes

---

## 11. Inserções feitas em `contests`

Concursos inseridos:
- `3690`
- `3691`
- `3692`
- `3693`
- `3694`
- `3695`
- `3696`
- `3701`

### Mapeamento aplicado

- `concurso` = número do concurso
- `data` = data oficial
- `dezenas` = dezenas oficiais em formato CSV com vírgula, preservando o padrão da tabela

### Resultado

- inserções concluídas sem sobrescrever registros existentes
- sem alteração de concursos já existentes

---

## 12. Validação pós-inserção

### Totais após a correção

- `imported_contests`: `16` registros na faixa 3689–3704
- `contests`: `16` registros na faixa 3689–3704

### Faixa completa

Concursos presentes na faixa 3689–3704:
- `3689`
- `3690`
- `3691`
- `3692`
- `3693`
- `3694`
- `3695`
- `3696`
- `3697`
- `3698`
- `3699`
- `3700`
- `3701`
- `3702`
- `3703`
- `3704`

### Lacunas remanescentes

- nenhuma

### Duplicados

- nenhum

### Formato das dezenas

- consistente em todos os concursos da faixa auditada

---

## 13. Consistência `imported_contests` x `contests`

### Resultado final

- os 16 concursos da faixa 3689–3704 batem entre si em data e dezenas;
- não há divergência entre `imported_contests` e `contests` para a faixa auditada.

### Status por concurso

| Concurso | Status |
|---|---|
| 3689 | OK |
| 3690 | OK |
| 3691 | OK |
| 3692 | OK |
| 3693 | OK |
| 3694 | OK |
| 3695 | OK |
| 3696 | OK |
| 3697 | OK |
| 3698 | OK |
| 3699 | OK |
| 3700 | OK |
| 3701 | OK |
| 3702 | OK |
| 3703 | OK |
| 3704 | OK |

---

## 14. Comparação final banco x Caixa

### Resultado final

- o banco ativo passou a bater com a Caixa na faixa auditada `3689–3704`;
- não restaram concursos faltantes nessa faixa;
- não houve divergência de dezenas;
- não houve divergência de datas.

### Último concurso do banco depois da correção

- `3704`

### Último concurso oficial

- `3704`

---

## 15. Hash do banco depois

- **Hash depois da correção**: `88fd31310a03682b894d646aa516af6befebe315efea8c80a3bdff1817a780ef`
- **Mudou?**: sim
- **Persistência confirmada**: sim

---

## 16. Riscos ou impedimentos

- Nenhum impedimento operacional após a reconciliação.
- O banco principal foi escrito de forma controlada.
- O backup pré-correção foi criado antes de qualquer escrita.
- O painel não foi alterado.
- Não houve `push`.

---

## 17. Conclusão institucional

A reconciliação controlada foi concluída com sucesso. Os 8 concursos faltantes foram obtidos da Caixa por meio do cliente institucional auditado e inseridos apenas nas duas tabelas reais autorizadas, sem sobrescrever concursos já existentes e sem alterar schema, painel ou código funcional.

### Status final

- **PARTE_4B_APROVADA_BANCO_RECONCILIADO_CAIXA**

---

## 18. Confirmações finais

- backup pré-correção foi criado: **sim**
- apenas os concursos autorizados foram inseridos: **sim**
- `contests` foi atualizado: **sim**
- `imported_contests` foi atualizado: **sim**
- nenhum concurso existente foi alterado: **sim**
- nenhuma tabela nova foi criada: **sim**
- `official_lotofacil_history` não foi criada: **sim**
- schema não foi alterado: **sim**
- painel não foi alterado: **sim**
- Lei 15 não foi alterada: **sim**
- geração não foi alterada: **sim**
- não houve `push`: **sim**

