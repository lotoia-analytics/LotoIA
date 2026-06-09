# Lei No 001 - Auditoria Institucional de Aderencia

## Escopo

Auditoria da cadeia de verdade institucional da LotoIA.

## Resposta objetiva

- **Fonte oficial da verdade:** PostgreSQL Institucional
- **Fluxo oficial:** CAIXA -> Importacao -> Validacao -> PostgreSQL Institucional -> Conferencia -> Persistencia -> Memoria HB -> Painel -> WhatsApp

## A) Modulos aderentes

- `dashboard/institutional_app.py`
  - painel institucional novo
  - leitura de `DATABASE_URL` via adaptador
  - conferencia e historicos a partir do banco institucional
  - exportacao historica derivada do banco
  - auditoria de runtime visivel
- `src/lotoia/database/database.py`
  - define a base ORM institucional e a resolucao de engine
- `src/lotoia/database/contest_repository.py`
  - fonte para concursos importados e persistidos
- `src/lotoia/ingestion/result_sync_service.py`
  - aderente quando usado com `ContestRepository` institucional
- `src/lotoia/ingestion/sync.py`
  - sincronizacao oficial e exportacao do historico espelho
- `src/lotoia/data/history_export.py`
  - exporta CSV espelho a partir do banco institucional
- `src/lotoia/governance/*`
  - documentos, auditoria e classificacao institucional

## B) Modulos nao aderentes ou com risco

- `dashboard/admin_app.py`
  - superficie legada com risco de divergencia visual e de fluxo
- entrypoints/fluxos que aceitam SQLite local como fallback operacional
- historicos/exports que possam usar CSV como fonte principal
- testes de infraestrutura que usam SQLite apenas para isolamento
- qualquer modulo que use `contest_ids` como dezenas
- qualquer modulo que exiba resumo sem recarregar o concurso persistido

## C) Fontes de dados por modulo

- **Gerador:** PostgreSQL institucional
- **Conferencia:** PostgreSQL institucional
- **Historico Analitico:** PostgreSQL institucional
- **Historico Institucional:** PostgreSQL institucional
- **Apagar Historico:** PostgreSQL institucional
- **CSV historico:** espelho/backup derivado do banco institucional

## D) Riscos encontrados

1. Divergencia entre ambiente local e publicado.
2. Persistencia de artefatos de teste em runtime publicado.
3. Uso de SQLite local em vez do banco institucional em execucoes de auditoria.
4. Exibicao de identificadores de concurso no lugar das dezenas oficiais.
5. Historicos analiticos e institucionais misturando snapshots e dados persistidos.
6. Confusao entre simulacao visual e conferencia persistida.

## E) Plano de adequacao

1. Manter `institutional_app.py` como runtime oficial limpo.
2. Garantir que toda leitura operacional venha do PostgreSQL institucional.
3. Tratar CSV apenas como espelho, nunca como verdade principal.
4. Remover/evitar dependencias do `admin_app.py` no fluxo institucional.
5. Explicitar auditoria de runtime na UI publicada.
6. Registrar excecoes arquiteturais em ADR antes de expandir o fluxo.

## Observacao operacional

Durante esta auditoria, o workspace local pode resolver para SQLite. A validacao final da Lei No 001 deve ocorrer no runtime publicado do Railway com `DATABASE_URL` institucional ativo.
