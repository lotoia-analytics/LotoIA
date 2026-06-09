# Saneamento Institucional - Parte 6
## Decisão sobre `official_lotofacil_history` e Fonte Única de Concursos

### 1. Resumo executivo
A auditoria confirmou que a base ativa da LotoIA está sincronizada na faixa operacional `3689-3704` e que o banco local possui duas camadas relevantes de concursos:
- `contests` / `imported_contests`, usadas pelo fluxo operacional e de persistência;
- `lotofacil_official_history`, preenchida e disponível como camada oficial de leitura histórica.

A decisão institucional recomendada nesta parte é manter uma fonte única **lógica** via gateway institucional, com a camada operacional permanecendo em `imported_contests / contests` e a camada oficial de leitura em `lotofacil_official_history`, sem permitir leituras diretas fora do gateway.

### 2. Estado atual herdado da Parte 5
Na Parte 5 foi definida a política candidata `POLITICA_C_HIBRIDA_CONTROLADA`, com a faixa observacional confiável `3689-3704`.

Na Parte 6, a investigação mostrou que essa faixa já está materialmente disponível no banco ativo e que a tabela oficial histórica existe e está preenchida, o que reduz o risco de ambiguidade na leitura institucional.

### 3. Banco ativo e tabelas existentes
Banco ativo conferido:
- `C:\Projetos\LotoIA\data\lotoia.db`

Tabelas relevantes existentes:
- `contests`
- `imported_contests`
- `lotofacil_official_history`
- `generation_events`
- `generated_games`
- `reconciliation_runs`
- `reconciliation_games`
- `institutional_output_signatures`
- `scientific_institutional_memory`
- `scientific_calibration_decisions`
- `operational_logs`

Resumo quantitativo:
- `imported_contests`: `16`
- `contests`: `16`
- `lotofacil_official_history`: `3704`

Último concurso persistido na camada operacional:
- `3704`

Último concurso persistido na camada oficial histórica:
- `3704`

### 4. Confirmação da presença de `official_lotofacil_history`
A tabela `lotofacil_official_history` **existe** no schema do banco ativo e está preenchida.

Estrutura observada:
- `contest_number`
- `created_at`
- `draw_date`
- `numbers`
- `numbers_signature`
- `source`
- `imported_at`
- `validated_at`
- `is_valid`
- `metadata_json`

Conclusão desta seção:
- não há ausência da tabela oficial histórica;
- a camada existe como leitura histórica institucional;
- o problema desta parte não é falta de dados, mas definição de governança de fonte única.

### 5. Mapa completo de referências a `official_lotofacil_history`
Foram encontradas referências diretas e indiretas em:

#### `dashboard/institutional_app.py`
- `_institutional_source_map()`
- `get_official_contest()`
- `get_latest_official_contest()`
- `get_previous_official_contest()`
- `_load_official_history_contest()`
- `_load_official_history_diagnostics()`
- `_ensure_official_history_seeded()`
- `_sync_latest_official_result_now()`
- blocos de diagnóstico e memória institucional
- blocos de RFE e conferência que expõem `official_contest_source`

#### `src/lotoia/database/contest_repository.py`
- `create_table()`
- `save_contest()`
- `sync_official_history_from_imported_contests()`
- leituras e rotinas de persistência relacionadas a concursos

#### `src/lotoia/ingestion/result_sync_service.py`
- fluxo de sincronização da Caixa para persistência local

#### `src/lotoia/ingestion/official_caixa_validation.py`
- validação oficial de janela histórica contra a fonte externa e a persistência local

#### `src/lotoia/governance/temporal_scientific_governance.py`
- uso da base operacional `imported_contests`

#### `src/lotoia/governance/temporal_history_registry.py`
- registro temporal e artefatos históricos de governança

#### `src/lotoia/ml/walk_forward_validation.py`
- validação temporal sem uso explícito da tabela oficial histórica

#### `src/lotoia/backtesting/backtester.py`
- backtesting sobre histórico temporal

### 6. Auditoria de `contest_repository.py`
O repositório segue com duas responsabilidades:

1. Persistência operacional:
- gravação em `contests`
- gravação em `imported_contests`

2. Espelhamento / apoio à camada oficial:
- sincronização de `lotofacil_official_history`
- possibilidade de bootstrap da história oficial a partir do CSV e dos importados

Leitura institucional:
- o módulo ainda é compatível com uma arquitetura híbrida;
- ele não quebra a camada oficial histórica, mas também não elimina a base operacional antiga;
- isso reforça a necessidade de um gateway único de leitura, em vez de múltiplos consumidores diretos.

### 7. Auditoria de `dashboard/institutional_app.py`
O painel já contém as três camadas conceituais:

- camada operacional:
  - `imported_contests`
  - `contests`

- camada oficial histórica:
  - `lotofacil_official_history`

- camada de diagnóstico / governança:
  - `official_contest_source`
  - `official_contest_id`
  - `official_contest_numbers`
  - `rfe_previous_contest_*`

Achados relevantes:
- o painel ainda cita `official_lotofacil_history` como origem em vários diagnósticos;
- a conferência e a RFE já receberam a abstração de leitura oficial;
- a função `_ensure_official_history_seeded()` mostra que o painel pode tentar completar a camada oficial histórica a partir da base operacional;
- a leitura visual do painel não distingue claramente, em todos os pontos, a camada operacional da camada oficial histórica.

### 8. Auditoria do fluxo de sincronização oficial
Fluxo observado:

1. A Caixa é lida por `CaixaApiClient`.
2. `ResultSyncService` sincroniza para o banco local.
3. `imported_contests` e `contests` recebem a persistência operacional.
4. `sync_official_history_from_imported_contests()` pode espelhar a base para `lotofacil_official_history`.
5. O painel usa a história oficial e os diagnósticos para conferência e RFE.

Leitura institucional:
- o fluxo operacional real ainda nasce na base operacional;
- a camada oficial histórica é um espelho institucional já utilizável;
- a confiabilidade da leitura depende de governança de gateway, não de acesso direto disperso.

### 9. Decisões candidatas A/B/C

#### A. `lotofacil_official_history` como fonte única imediata
Vantagens:
- nome institucional mais claro;
- leitura histórica já disponível;
- adequação ao discurso de “histórico oficial”.

Riscos:
- o ecossistema operacional ainda grava e consome `imported_contests / contests`;
- migração imediata quebraria compatibilidade sem refatoração adicional.

#### B. `imported_contests / contests` como fonte operacional e `lotofacil_official_history` como camada oficial de leitura
Vantagens:
- preserva compatibilidade com o runtime atual;
- respeita a persistência existente;
- permite um gateway único sem forçar ruptura de schema;
- deixa a história oficial como read-model institucional.

Riscos:
- exige disciplina para evitar leituras diretas concorrentes;
- a governança precisa explicitar que a camada oficial histórica é a leitura canônica, enquanto a base operacional continua sendo a persistência real.

#### C. Adiar a decisão e exigir intervenção humana
Vantagens:
- máxima cautela.

Riscos:
- prolonga a ambiguidade;
- mantém a sobreposição de fontes sem regra clara.

### 10. Comparativo de riscos
- **A**: risco alto de ruptura operacional.
- **B**: risco controlado, com compatibilidade e governança explícita.
- **C**: risco baixo imediato, mas risco institucional alto por indefinição.

### 11. Decisão institucional recomendada
**Decisão recomendada: B**

Interpretação institucional:
- `lotofacil_official_history` deve ser tratado como a camada oficial de leitura histórica;
- `imported_contests / contests` continuam como camada operacional de persistência e sincronização;
- nenhum módulo deve consultar diretamente a camada oficial ou operacional fora de um gateway institucional único.

Em outras palavras:
- a **fonte única lógica** deve ser o gateway;
- a **camada oficial de leitura** deve ser `lotofacil_official_history`;
- a **camada operacional de escrita** deve permanecer em `imported_contests / contests`.

### 12. Trava provisória de fonte única
Regra provisória recomendada:

> Nenhum consumidor institucional deve ler concursos oficiais por caminho próprio. Todas as leituras devem passar por um gateway único, que resolve a camada oficial histórica e preserva a camada operacional apenas para escrita e sincronização.

Guardrail adicional:
- leituras históricas oficiais devem considerar a faixa sincronizada e sem lacunas;
- leituras operacionais continuam válidas para persistência, mas não substituem o read-model oficial.

### 13. Impactos para a Parte 7
A Parte 7 deve:
- consolidar o gateway único de leitura;
- reduzir leitura direta de tabelas por múltiplos módulos;
- preservar compatibilidade entre conferência, RFE e memória institucional;
- formalizar a separação entre escrita operacional e leitura oficial.

### 14. Conclusão institucional
A Parte 6 define que `official_lotofacil_history` não está ausente: ela existe, está preenchida e é a melhor candidata para a leitura oficial histórica.  
Ao mesmo tempo, a base operacional continua em `imported_contests / contests`, o que exige um gateway único para evitar divergência de leitura.

Conclusão final:
- a decisão institucional recomendada é **B**;
- a governança deve tratar `lotofacil_official_history` como read-model oficial;
- a persistência operacional continua em `imported_contests / contests`;
- a fonte única deve ser lógica, via gateway, e não múltiplos acessos diretos.

### 15. Confirmações finais
- não houve alteração de banco;
- não houve alteração de schema;
- não houve alteração de código;
- não houve alteração de `.env`;
- não houve alteração de Lei 15;
- não houve alteração de geração;
- não houve `push`.

### 16. Status final da parte
**PARTE_6_APROVADA_DECISAO_OFFICIAL_HISTORY_DEFINIDA**
