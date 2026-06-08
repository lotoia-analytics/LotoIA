# Saneamento Institucional - Parte 8
## Redução de Leituras Diretas Fora do Gateway Oficial

### 1. Resumo executivo
A auditoria da Parte 8 mapeou os consumidores de concursos oficiais e confirmou que a plataforma já opera com um gateway lógico institucional para leitura oficial:
- `get_official_contest()`
- `get_latest_official_contest()`
- `get_previous_official_contest()`

As leituras diretas remanescentes não aparecem como consumo disperso externo fora do painel/RFE/memória institucional; elas aparecem, em geral, como implementação interna da própria camada institucional ou da persistência operacional.

### 2. Estado herdado das partes anteriores
Na Parte 6 foi definida a decisão institucional recomendada:
- `lotofacil_official_history` como read-model oficial;
- `imported_contests / contests` como persistência operacional;
- gateway lógico único para leitura oficial.

Na Parte 7 isso foi consolidado como base arquitetural válida.

### 3. Escopo auditado
Foram auditados:
- `dashboard/institutional_app.py`
- `src/lotoia/database/contest_repository.py`
- `src/lotoia/ingestion/result_sync_service.py`
- `src/lotoia/ingestion/official_caixa_validation.py`
- `src/lotoia/governance/temporal_scientific_governance.py`
- `src/lotoia/governance/temporal_history_registry.py`
- `src/lotoia/ml/walk_forward_validation.py`
- `src/lotoia/backtesting/backtester.py`

### 4. Mapa de leituras diretas restantes

#### 4.1 `dashboard/institutional_app.py`
Pontos diretos observados:
- `_load_official_history_contest()`
- `_load_official_history_diagnostics()`
- `_ensure_official_history_seeded()`
- `_sync_latest_official_result_now()`
- `_institutional_source_map()`
- `get_official_contest()`
- `get_latest_official_contest()`
- `get_previous_official_contest()`

Classificação:
- `get_official_contest()`, `get_latest_official_contest()`, `get_previous_official_contest()`:
  - **gateway institucional**
- `_load_official_history_contest()` e `_load_official_history_diagnostics()`:
  - **implementação interna do gateway**
- `_ensure_official_history_seeded()`:
  - **compatibilidade / bootstrap interno**
- `_sync_latest_official_result_now()`:
  - **sincronização operacional**

#### 4.2 `src/lotoia/database/contest_repository.py`
Pontos diretos observados:
- criação/garantia da tabela `lotofacil_official_history`
- `save_contest()`
- `sync_official_history_from_imported_contests()`

Classificação:
- **persistência operacional**
- **espelho oficial histórico**
- **implementação interna autorizada**

#### 4.3 `src/lotoia/ingestion/result_sync_service.py`
Pontos observados:
- sincronização da Caixa para o banco operacional

Classificação:
- **operacional**
- não é consumo disperso da camada oficial

#### 4.4 `src/lotoia/ingestion/official_caixa_validation.py`
Pontos observados:
- validação oficial da janela histórica

Classificação:
- **auditoria/validação**
- consumo institucional controlado

#### 4.5 `src/lotoia/governance/temporal_scientific_governance.py`
Pontos observados:
- usa `imported_contests` como base temporal operacional

Classificação:
- **operacional / temporal**

#### 4.6 `src/lotoia/governance/temporal_history_registry.py`
Pontos observados:
- registra artefatos históricos e validações

Classificação:
- **governança institucional**

#### 4.7 `src/lotoia/ml/walk_forward_validation.py`
Pontos observados:
- validação temporal sem leitura dispersa de `official_lotofacil_history`

Classificação:
- **validação temporal**

#### 4.8 `src/lotoia/backtesting/backtester.py`
Pontos observados:
- usa histórico operacional/temporal para backtesting

Classificação:
- **backtesting**

### 5. Classificação por tipo de leitura

#### Interna
- `_load_official_history_contest()`
- `_load_official_history_diagnostics()`
- `_ensure_official_history_seeded()`

#### Operacional
- `imported_contests`
- `contests`
- `save_contest()`
- `sync_official_history_from_imported_contests()`
- `result_sync_service`

#### Oficial
- `lotofacil_official_history`
- `get_official_contest()`
- `get_latest_official_contest()`
- `get_previous_official_contest()`

#### Indevida
- **não foram identificados consumidores externos dispersos fora do gateway lógico** nesta auditoria.

### 6. Leituras que podem ser redirecionadas ao gateway
Preferencialmente, qualquer nova leitura institucional de concurso oficial deve usar:
- `get_official_contest()`
- `get_latest_official_contest()`
- `get_previous_official_contest()`

Onde houver consumo direto de `_load_official_history_contest()` fora do núcleo do painel, a recomendação é encapsular por gateway, mas nesta parte não foi aplicada alteração de código.

### 7. Leituras que devem permanecer por compatibilidade
Por compatibilidade institucional e operacional, permanecem:
- `imported_contests / contests` como persistência operacional;
- `sync_official_history_from_imported_contests()` como espelho oficial;
- `_ensure_official_history_seeded()` como compatibilidade/bootstrapping;
- `result_sync_service` como entrada operacional da Caixa.

### 8. Testes / evidências de regressão
Evidências já existentes e relevantes:
- `tests/test_protocol_structural_pipeline.py`
- `tests/test_result_sync_service.py`
- `tests/test_clean_app_formats.py`
- `tests/test_global_batch_deduplication.py`

Esses testes cobrem:
- origem oficial da RFE;
- referência anterior do concurso;
- conferência institucional;
- consistência de origem e números.

### 9. Painel, RFE e memória institucional
Confirmado neste mapeamento:
- o painel usa o gateway lógico institucional para expor `official_contest_*`;
- a RFE usa a mesma origem lógica para `rfe_previous_contest_*`;
- a memória institucional lê diagnósticos oficiais da mesma trilha.

### 10. Decisão institucional
Não foi identificada necessidade de mudança funcional nesta parte.

Decisão recomendada:
- **manter o gateway lógico único como padrão institucional**;
- **manter `lotofacil_official_history` como read-model oficial**;
- **manter `imported_contests / contests` como persistência operacional**.

### 11. Comparativo de riscos
- **Leitura direta dispersa fora do gateway**: risco alto;
- **Gateway institucional único**: risco controlado;
- **Alterar schema ou remover tabelas nesta fase**: risco alto e desnecessário.

### 12. Conclusão institucional
A Parte 8 demonstra que a plataforma não está consumindo concursos oficiais de forma dispersa fora do gateway lógico institucional. O que existe é:
- uma base operacional persistida;
- um read-model oficial;
- um conjunto de funções internas do painel que materializam o gateway;
- consumidores institucionais já alinhados à mesma lógica.

Portanto, a recomendação é **manter a arquitetura atual com gateway único lógico**, sem alteração de banco, schema ou Lei 15.

### 13. Confirmações finais
- não houve alteração de banco;
- não houve alteração de schema;
- não houve alteração de código funcional;
- não houve alteração de Lei 15;
- não houve `push`.

### 14. Status final da parte
**PARTE_8_APROVADA_LEITURAS_DIRETAS_RESTANTES_CLASSIFICADAS_E_GATEWAY_CONFIRMADO**
