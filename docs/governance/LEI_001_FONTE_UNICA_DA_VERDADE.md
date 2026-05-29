# Lei No 001 - Fonte Unica da Verdade LotoIA

## Status
Ativa e obrigatoria para a plataforma institucional.

## Proposito

Estabelecer uma unica cadeia oficial de verdade para importacao, validacao, conferencia,
persistencia, memoria analitica, painel e integracoes operacionais.

## Fluxo oficial e obrigatorio

```text
CAIXA
  -> Importacao
  -> Validacao
  -> PostgreSQL Institucional
  -> Conferencia
  -> Persistencia
  -> Memoria HB
  -> Painel
  -> WhatsApp
```

## Fonte oficial da verdade

**PostgreSQL Institucional**

Regra:
- a interface pode exibir, resumir e auditar;
- a memoria pode refletir e consolidar;
- o CSV pode servir como backup e exportacao;
- nenhuma outra superficie deve disputar a verdade operacional.

## Normas obrigatorias

1. Toda conferencia operacional deve ler do banco institucional.
2. Todo historico institucional deve refletir registros persistidos.
3. Toda exportacao deve ser derivada do banco institucional.
4. Todo novo modulo deve explicitar sua fonte de dados.
5. SQLite local, CSV e snapshots sao permitidos apenas como suporte, backup ou auditoria.
6. Nao e permitido criar uma fonte paralela de verdade sem ADR ou decisao arquivada.

## Fontes autorizadas por camada

- **Importacao oficial:** Caixa -> banco institucional
- **Conferencia oficial:** banco institucional
- **Memoria HB:** banco institucional + artefatos versionados
- **Painel:** banco institucional + session_state efemero
- **WhatsApp:** resultados consolidados persistidos

## Mapa de aderencia institucional

### Aderentes

- `dashboard/institutional_app.py`
- `src/lotoia/database/database.py`
- `src/lotoia/database/contest_repository.py`
- `src/lotoia/ingestion/result_sync_service.py` quando instanciado com repository institucional
- `src/lotoia/ingestion/sync.py`
- `src/lotoia/data/history_export.py`
- `src/lotoia/governance/*` de consolidacao e auditoria

### Nao aderentes ou com risco de divergencia

- entrypoints legados que ainda permitem SQLite local como fallback operacional
- `dashboard/admin_app.py`
- testes e utilitarios que usam SQLite apenas para validação isolada
- fluxos que consultam CSV como fonte principal
- qualquer modulo que use `contest_ids` como se fossem dezenas
- qualquer fluxo que leia `DB_PATH` local sem explicitar o backend publicado

## Riscos identificados

1. Divergencia entre ambiente local e ambiente publicado.
2. Uso acidental de SQLite como fonte operacional de producao.
3. Leitura de CSV como verdade em vez de espelho.
4. Regressao de conferencias quando o concurso oficial nao e recarregado do banco.
5. Persistencia parcial de historicos de teste em ambientes publicados.
6. Interfaces que exibem identificadores de concurso no lugar das dezenas persistidas.

## Plano de adequacao

1. Exibir auditoria de runtime com backend, host, database, schema, build e commit.
2. Garantir que importacao e conferencia sempre reconstroem o concurso persistido no PostgreSQL.
3. Atualizar o CSV oficial apenas como espelho do banco institucional.
4. Padronizar todas as telas de historico para ler as tabelas persistidas corretas.
5. Separar explicitamente:
   - geracao
   - conferencia
   - memoria
   - exportacao
   - limpeza
6. Registrar qualquer excecao a esta lei em ADR.

## Validade

Esta lei vale para:
- novos modulos
- novos experimentos
- novos paines
- novas integracoes
- novos fluxos de exportacao

## Nota final

Se houver conflito entre implementacao local e runtime publicado, a fonte oficial da verdade continua sendo o PostgreSQL institucional do ambiente publicado.
