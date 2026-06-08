# Saneamento Institucional - Parte 3: Banco Ativo do Painel ADM

## 1. Objetivo

Identificar, por auditoria de leitura בלבד, o banco ativo do Painel ADM em execução, sua tipologia, o caminho resolvido, o hash do arquivo ativo, as tabelas principais, a tabela candidata a concursos/resultados, o último concurso persistido e possíveis bancos paralelos ou de teste presentes no workspace.

## 2. Banco ativo do painel

- **Painel ativo observado**: `dashboard/institutional_app.py`
- **Processo ativo**: Streamlit executando `dashboard/institutional_app.py`
- **Fonte de resolução do banco**: `src/lotoia/database/database.py` + `src/lotoia/database/adapter.py`
- **Variáveis de ambiente relevantes**:
  - `DATABASE_URL =` não definida
  - `LOTOIA_DATABASE_URL =` não definida
  - `STREAMLIT_DATABASE_URL =` não definida
  - `LOTOIA_DATABASE_POOLER_URL =` não definida
  - `STREAMLIT_DATABASE_POOLER_URL =` não definida
- **Banco ativo resolvido**: SQLite local
- **Caminho resolvido**: `C:\Projetos\LotoIA\data\lotoia.db`
- **Arquivo em uso com WAL/SHM**:
  - `C:\Projetos\LotoIA\data\lotoia.db-wal`
  - `C:\Projetos\LotoIA\data\lotoia.db-shm`

## 3. Hash do banco ativo

- **SHA256 do banco ativo**: `07d33c50a4a94844870564e24f023a45798a89c4a6882c62e7ebff2bff7ee250`
- **Observação**: o arquivo está em uso pelo processo do painel, mas o hash foi obtido em leitura local somente para auditoria.

## 4. Tipologia do banco

- **Tipo**: SQLite local
- **Modo de uso no painel**: banco institucional ativo do runtime
- **Natureza**: persistência operacional do painel, não banco remoto de produção nesta sessão

## 5. Tabelas principais encontradas no banco ativo

Principais tabelas observadas na schema do `data/lotoia.db`:

- `contests`
- `imported_contests`
- `generation_events`
- `generated_games`
- `reconciliation_runs`
- `reconciliation_games`
- `institutional_output_signatures`
- `scientific_institutional_memory`
- `scientific_calibration_decisions`
- `operational_logs`
- `audit_trail`
- `runtime_metrics`
- `runtime_snapshots`

## 6. Tabela candidata a concursos/resultados

### Tabelas candidatas

1. `imported_contests`
2. `contests`

### Motivo da escolha

- Ambas estão populadas e trazem o último concurso disponível no banco local.
- A tela institucional do painel usa `imported_contests` como fonte operacional de diagnóstico.
- `contests` espelha o último concurso com o mesmo valor final observado.

## 7. Último concurso persistido no banco

### `imported_contests`

- **Quantidade total**: `8`
- **Último concurso**: `3704`
- **Data**: `06/06/2026`
- **Dezenas**: `01,03,04,09,10,11,12,13,14,15,19,20,22,23,25`

### `contests`

- **Quantidade total**: `8`
- **Último concurso**: `3704`
- **Data**: `06/06/2026`
- **Dezenas**: `01,03,04,09,10,11,12,13,14,15,19,20,22,23,25`

## 8. Divergência institucional encontrada

Foi confirmada uma divergência importante de schema:

- `contests` existe e está preenchida.
- `imported_contests` existe e está preenchida.
- `official_lotofacil_history` **não está presente** no schema do banco ativo `data/lotoia.db`.

Isso significa que o painel ativo, nesta sessão, opera com o par `contests/imported_contests` para leitura local, e não com uma tabela `official_lotofacil_history` no banco SQLite ativo.

## 9. Bancos paralelos encontrados

### Banco paralelo/local adicional

- `C:\Projetos\LotoIA\lotoia.db`
  - Hash: `d7b79bbd049a5648338bb44b86e98fa8baed6bd44a2b1791d3d244e6f28f6c62`
  - Tipo: SQLite local secundário
  - Tamanho: menor que o banco ativo
  - Conteúdo observado: tabelas mínimas, sem dados operacionais relevantes desta sessão

### Banco de validação compartilhada

- `C:\Projetos\LotoIA\data\shared_backend_validation.db`
  - Hash: `ff8d9ca4f537fe6c4e8bbb51fa3a26a8ddb1bb7aa83ebd2c4d2259df9d721f96`
  - Tipo: SQLite de validação/teste
  - Conteúdo observado: estrutura isolada para validação compartilhada
  - Uso: teste / integração, não banco ativo do painel

## 10. Bancos de teste encontrados

- `C:\Projetos\LotoIA\data\shared_backend_validation.db`
- Bancos temporários e auxiliares com sufixos `-wal`, `-shm` e diretórios `tmp_*`

Esses artefatos não devem ser tratados como banco operacional ativo do ADM.

## 11. Riscos críticos

1. **Risco de divergência de schema**
   - O código do painel já referencia caminhos institucionais que esperam `official_lotofacil_history` em alguns fluxos.
   - O banco SQLite ativo observado não possui essa tabela.

2. **Risco de leitura paralela**
   - `contests` e `imported_contests` estão ativos e consistentes entre si.
   - Fluxos que tentem usar outra tabela oficial podem falhar ou cair em fallback.

3. **Risco de contaminação entre bancos**
   - Existem bancos secundários e de validação no workspace.
   - Se algum fluxo de runtime for redirecionado por engano, a rastreabilidade do painel pode divergir.

4. **Risco de arquivo em uso**
   - O banco ativo está aberto pelo processo Streamlit.
   - Isso impede manipulação direta sem cuidado e reforça a necessidade de auditoria somente leitura nesta etapa.

## 12. Status final

- **Banco ativo do painel identificado**: sim
- **Tipo identificado**: SQLite local
- **Caminho resolvido**: sim
- **Hash obtido**: sim
- **Tabelas principais mapeadas**: sim
- **Tabela candidata de concursos/resultados**: `imported_contests` / `contests`
- **Último concurso persistido**: `3704`
- **Total de concursos persistidos**: `8`
- **Bancos paralelos encontrados**: sim
- **Bancos de teste encontrados**: sim

## 13. Conclusão institucional

A auditoria da Parte 3 identifica com clareza o banco ativo do Painel ADM como o SQLite local `C:\Projetos\LotoIA\data\lotoia.db`, em uso pelo Streamlit, com `imported_contests` e `contests` preenchidas até o concurso `3704`.

Ao mesmo tempo, foi detectada uma divergência relevante de schema: a tabela `official_lotofacil_history` não existe no banco ativo observado nesta sessão, o que obriga os fluxos institucionais a permanecerem consistentes com a fonte realmente disponível (`contests/imported_contests`) e exige atenção para evitar leitura paralela ou fallback silencioso.

### Classificação final

- **PARTE_3_APROVADA_BANCO_ATIVO_IDENTIFICADO**

## 14. Confirmações finais

- não houve alteração de dados
- não houve alteração de schema
- não houve alteração de lógica funcional
- não houve push
- o relatório é apenas documental
