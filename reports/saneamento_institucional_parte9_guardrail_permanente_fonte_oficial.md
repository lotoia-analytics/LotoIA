# Saneamento Institucional - Parte 9
## Guardrail Permanente de Fonte Oficial

### 1. Resumo executivo
A Parte 9 converteu a trava provisória de fonte única em um guardrail verificável por teste, com foco em impedir regressões futuras para leituras diretas dispersas de concursos oficiais.

O resultado institucional é:
- a fonte oficial lógica continua centralizada em um gateway;
- o read-model oficial continua em `lotofacil_official_history`;
- a persistência operacional continua em `imported_contests / contests`;
- regressões de leitura direta passam a ser detectadas por teste.

### 2. Estado herdado da Parte 8
Na Parte 8 foi confirmado que:
- não há consumo disperso externo fora do gateway lógico;
- as leituras internas remanescentes são compatibilidades documentadas;
- o painel, a RFE e a memória institucional compartilham a mesma origem lógica oficial.

### 3. Regra documentada de acesso oficial
Regra permanente proposta:

> Toda leitura oficial de concursos deve passar pelo gateway institucional. Leituras diretas só podem existir como implementação interna controlada, documentada e coberta por regressão.

### 4. Lista permitida de funções gateway
Funções institucionais autorizadas como gateway:
- `get_official_contest()`
- `get_latest_official_contest()`
- `get_previous_official_contest()`

Essas funções concentram a resolução do concurso oficial e a exposição de:
- `official_contest_source`
- `official_contest_id`
- `official_contest_numbers`

### 5. Lista de exceções internas autorizadas
Leituras internas autorizadas por compatibilidade:
- `_load_official_history_contest()`
- `_load_official_history_diagnostics()`
- `_ensure_official_history_seeded()`
- `_sync_latest_official_result_now()`

Essas funções não constituem novo consumo disperso; elas implementam o mecanismo interno do gateway ou a compatibilidade operacional da camada institucional.

### 6. Teste de regressão adicionado
Foi adicionado o teste:

- `tests/test_official_history_gateway_guardrail.py`

Objetivo do teste:
- congelar os callsites permitidos do gateway;
- detectar surgimento futuro de novas leituras diretas fora do mapa autorizado;
- garantir que painel, RFE e memória institucional não passem a ler concursos oficiais por caminhos dispersos.

O teste valida o conjunto de callsites permitidos no arquivo:
- `dashboard/institutional_app.py`

### 7. Evidências de regressão
Validações executadas:
- `python -m pytest tests/test_official_history_gateway_guardrail.py tests/test_protocol_structural_pipeline.py tests/test_result_sync_service.py -q --basetemp=tmp_pytest_part9`

Resultado:
- `23 passed`

### 8. Impacto sobre painel, RFE e memória institucional
Confirmado no conjunto de testes e no mapa de callsites:
- o painel utiliza o gateway oficial lógico;
- a RFE utiliza a mesma origem lógica para o concurso anterior;
- a memória institucional usa a mesma trilha oficial;
- novas leituras dispersas diretas passam a ser barradas pelo guardrail.

### 9. Decisão institucional
Decisão recomendada:
- manter `lotofacil_official_history` como read-model oficial;
- manter `imported_contests / contests` como persistência operacional;
- usar o gateway como contrato institucional permanente;
- proteger a arquitetura com teste de regressão.

### 10. Comparativo de riscos
- **Sem guardrail**: risco de regressão futura por novas leituras diretas.
- **Com guardrail em teste**: risco reduzido e detectável.
- **Alterar schema ou banco nesta fase**: risco desnecessário.

### 11. Conclusão institucional
A Parte 9 estabelece uma barreira permanente, verificável por teste, contra regressão de acesso direto disperso à fonte oficial.

Não houve necessidade de alterar:
- banco;
- schema;
- geração;
- Lei 15.

### 12. Confirmações finais
- não houve alteração de banco;
- não houve alteração de schema;
- não houve alteração de geração;
- não houve alteração de Lei 15;
- não houve `push`.

### 13. Status final da parte
**PARTE_9_APROVADA_GUARDARAIL_PERMANENTE_FONTE_OFICIAL_IMPLEMENTADO**
