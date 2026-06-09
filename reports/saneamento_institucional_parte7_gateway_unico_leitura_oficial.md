# Saneamento Institucional - Parte 7
## Consolidação do Gateway Único de Leitura Oficial

### 1. Resumo executivo
A auditoria da Parte 7 confirmou que a LotoIA já possui um gateway institucional lógico para leitura de concursos oficiais, centrado em:
- `get_official_contest()`
- `get_latest_official_contest()`
- `get_previous_official_contest()`

Essas funções concentram a resolução do concurso oficial e a exposição de metadados institucionais como:
- `official_contest_source`
- `official_contest_id`
- `official_contest_numbers`

A persistência operacional continua em `imported_contests / contests`, enquanto a camada oficial histórica segue em `lotofacil_official_history` como read-model oficial.

### 2. Estado atual herdado da Parte 6
Na Parte 6 ficou definido que:
- a camada operacional permanece em `imported_contests / contests`;
- a camada oficial histórica existe em `lotofacil_official_history`;
- a governança deve ser baseada em gateway único de leitura;
- a recomendação institucional foi a decisão `B`.

Essa decisão permanece válida e é reforçada nesta parte.

### 3. Banco ativo e camadas existentes
Banco ativo conferido:
- `C:\Projetos\LotoIA\data\lotoia.db`

Camadas relevantes:
- operacional:
  - `contests`
  - `imported_contests`
- oficial histórica:
  - `lotofacil_official_history`

Situação quantitativa observada:
- `imported_contests`: `16`
- `contests`: `16`
- `lotofacil_official_history`: `3704`

Último concurso em ambas as camadas:
- `3704`

### 4. Gateway institucional identificado
O gateway único lógico já existe no painel e é exposto por:

#### `get_official_contest(contest_id)`
- resolve o concurso oficial por identificador;
- usa a leitura oficial histórica;
- injeta:
  - `official_contest_source = "official_lotofacil_history"`
  - `official_contest_id`
  - `official_contest_numbers`

#### `get_latest_official_contest()`
- retorna o concurso oficial mais recente;
- parte da diagnóstica oficial histórica;
- reutiliza `get_official_contest()`.

#### `get_previous_official_contest(target_contest)`
- usa `target_contest - 1` quando há concurso alvo;
- caso contrário, recai no último concurso oficial;
- mantém a origem como `official_lotofacil_history`.

### 5. Mapa de consumidores diretos

#### Consumidores no `dashboard/institutional_app.py`
- `_institutional_source_map()`
- blocos de memória institucional
- diagnóstico da conferência
- RFE estrutural
- conferência por concurso
- geração limpa e seus diagnósticos
- páginas de auditabilidade visual

#### Consumidores em outros módulos
- `src/lotoia/database/contest_repository.py`
- `src/lotoia/ingestion/result_sync_service.py`
- `src/lotoia/ingestion/official_caixa_validation.py`
- `src/lotoia/governance/temporal_scientific_governance.py`
- `src/lotoia/governance/temporal_history_registry.py`
- `src/lotoia/ml/walk_forward_validation.py`
- `src/lotoia/backtesting/backtester.py`

Leitura institucional:
- os consumidores diretos foram identificados;
- a maioria dos consumidores externos usa a camada operacional;
- os consumidores da camada oficial histórica devem passar pelo gateway do painel ou por seus equivalentes institucionais.

### 6. Acessos diretos removidos ou isolados
Nesta etapa não foi aplicada refatoração destrutiva.

O que foi confirmado:
- o acesso oficial lógico já está centralizado em `get_official_contest()`, `get_latest_official_contest()` e `get_previous_official_contest()`;
- os loaders privados `_load_official_history_contest()` e `_load_official_history_diagnostics()` continuam como implementação interna da camada oficial;
- a sincronização oficial permanece em `sync_official_history_from_imported_contests()` no repositório;
- não houve remoção de tabelas;
- não houve alteração de schema;
- não houve alteração da Lei 15.

### 7. Auditoria do painel, RFE e memória institucional

#### Painel
O painel expõe a fonte oficial por meio dos diagnósticos:
- `official_contest_source`
- `official_contest_id`
- `official_contest_numbers`
- `official_history_diagnostics`

#### RFE
A RFE usa a mesma lógica de leitura oficial para determinar:
- `rfe_previous_contest_found`
- `rfe_previous_contest_id`
- `rfe_previous_contest_numbers`
- `rfe_previous_contest_source`
- `rfe_previous_contest_message`

#### Memória institucional
A memória institucional também lê os diagnósticos oficiais da mesma camada lógica.

Conclusão:
- painel, RFE e memória institucional compartilham a mesma lógica de fonte oficial;
- a camada operacional não substitui a camada oficial histórica;
- o risco residual está na coexistência de múltiplas rotas de leitura, não na ausência do gateway.

### 8. Fluxo de sincronização oficial
Fluxo observado:
1. `CaixaApiClient` obtém o concurso oficial;
2. `ResultSyncService` grava em `imported_contests` / `contests`;
3. `ContestRepository.sync_official_history_from_imported_contests()` espelha a história para `lotofacil_official_history`;
4. o painel lê a camada oficial histórica por gateway;
5. a governança e a RFE usam o mesmo princípio de origem oficial.

### 9. Testes de regressão de leitura oficial
Os testes já existentes cobrem parte relevante da rastreabilidade institucional:
- `tests/test_protocol_structural_pipeline.py`
- `tests/test_result_sync_service.py`
- `tests/test_clean_app_formats.py`
- `tests/test_global_batch_deduplication.py`

Esses testes validam:
- referência anterior da RFE;
- origem oficial da conferência;
- integração de leitura oficial;
- consistência entre painel e diagnósticos.

### 10. Classificação dos caminhos

#### Caminho operacional
- `imported_contests / contests`
- classe: `persistência operacional`

#### Caminho oficial histórico
- `lotofacil_official_history`
- classe: `read-model oficial`

#### Caminho institucional lógico
- `get_official_contest()`
- `get_latest_official_contest()`
- `get_previous_official_contest()`
- classe: `gateway único de leitura`

### 11. Comparativo de riscos
- **Leitura direta dispersa**: risco alto.
- **Gateway lógico único com read-model oficial**: risco controlado.
- **Migrar tudo para uma única tabela sem compatibilidade**: risco alto.

### 12. Decisão institucional recomendada
**Decisão recomendada: B**

Interpretação:
- `lotofacil_official_history` permanece como read-model oficial;
- `imported_contests / contests` permanecem como persistência operacional;
- todas as leituras oficiais devem passar pelo gateway lógico institucional;
- não é necessária migração destrutiva nesta fase.

### 13. Trava provisória de fonte única
Regra institucional recomendada:

> Toda leitura oficial de concursos deve passar pelo gateway institucional; leituras diretas só podem existir como implementação interna controlada, nunca como consumo disperso no painel ou nos diagnósticos.

### 14. Impactos para a Parte 8
A Parte 8 deve:
- reduzir leituras diretas fora do gateway;
- consolidar contratos de leitura para painel, RFE e memória institucional;
- preservar compatibilidade com a persistência operacional;
- manter a separação entre escrita operacional e leitura oficial.

### 15. Conclusão institucional
A Parte 7 confirma que o gateway único já existe logicamente e que a plataforma opera melhor com a decisão B:
- leitura oficial histórica em `lotofacil_official_history`;
- persistência operacional em `imported_contests / contests`;
- governança de acesso via gateway institucional.

Não houve necessidade de alterar banco, schema, geração ou Lei 15.

### 16. Confirmações finais
- não houve alteração de banco;
- não houve alteração de schema;
- não houve alteração de código funcional;
- não houve alteração de Lei 15;
- não houve `push`.

### 17. Status final da parte
**PARTE_7_APROVADA_GATEWAY_UNICO_IDENTIFICADO_E_CONSOLIDADO**
