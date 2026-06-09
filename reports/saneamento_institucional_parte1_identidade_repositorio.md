# Saneamento Institucional Parte 1: Identidade, Origem e Estado Real do Repositório LotoIA

## 1. Resumo executivo

Auditoria de origem e rastreabilidade executada no repositório localizado em `C:\Projetos\LotoIA`. O repositório existe, possui branch ativa `main`, está em `HEAD` local `b7f37ed`, encontra-se com worktree sujo e está à frente de `origin/main` por 1 commit. O commit crítico `3efd905230d1f2bff12a3b2150a7d1fb89f40fac` existe, está publicado no remoto e é ancestral do `HEAD`. O commit crítico `b7f37edb0c1e9098a78a5c9312979fd2bdbd6aa5` existe, está no `HEAD` atual, é ancestral do `HEAD` e não está publicado no remoto. Não foram identificadas cópias paralelas reais do projeto fora da raiz auditada; os diretórios encontrados são backups e temporários internos ao próprio repositório.

## 2. Diretório atual auditado

- Caminho absoluto atual: `C:\Projetos\LotoIA`
- Saída de `pwd`: `C:/Projetos/LotoIA`
- Saída de `cd`: `C:\Projetos\LotoIA`

## 3. REPO_ROOT_DETECTADO

- `git rev-parse --show-toplevel`: `C:/Projetos/LotoIA`
- O diretório contém `.git`: sim
- Pasta do projeto: `LotoIA`
- Parecer: parece ser a raiz real do repositório auditado

## 4. Branch atual

- Branch atual: `main`
- Branch remota rastreada: `origin/main`
- Branch de backup adicional encontrada: `backup-mission12` (não é branch ativa)

## 5. HEAD atual

- HEAD completo antes do commit desta Parte 1: `b7f37edb0c1e9098a78a5c9312979fd2bdbd6aa5`
- HEAD curto antes do commit desta Parte 1: `b7f37ed`
- Commit atual no topo da linha local: `audit: implementa tabela institucional matriz no painel`

## 6. Estado do worktree

Classificação: `SUJO`

Evidências:
- modificado: `reports/ativacao_menu_apagar_limpar_historico.md`
- untracked: `acl_backup.txt`
- untracked: `backups/`
- untracked: `data/corrupted/`
- untracked: `data/data/`
- untracked: `data/shared_backend_validation.db-shm`
- untracked: `data/shared_backend_validation.db-wal`
- untracked: `lotoia.db-shm`
- untracked: `lotoia.db-wal`
- untracked: `tmp_git_index`
- untracked: `tmp_lotoia_test.db-shm`
- untracked: `tmp_lotoia_test.db-wal`

## 7. Estado local x remoto

Classificação: `AHEAD_LOCAL`

Evidências:
- `git status -sb`: `## main...origin/main [ahead 1]`
- commits locais não publicados:
  - `b7f37ed audit: implementa tabela institucional matriz no painel`
- commits remotos não incorporados: nenhum identificado
- `git log origin/main..HEAD --oneline`:
  - `b7f37ed audit: implementa tabela institucional matriz no painel`
- `git log HEAD..origin/main --oneline`: vazio

## 8. Commits locais não publicados

- `b7f37ed audit: implementa tabela institucional matriz no painel`

## 9. Commits remotos não incorporados

- Nenhum identificado no momento

## 10. Situação do commit 3efd905230d1

- Existe localmente: sim
- Mensagem: `audit: aplica regra executavel e constroi celulas 16d`
- Arquivos alterados: `reports/construcao_validacao_executiva_16d_top10_20_30_50.md`
- Branch(es) que contêm: `main`, `origin/main`
- Está em HEAD atual: não
- É ancestral do HEAD: sim
- Está publicado no remoto: sim
- Classificação: `COMMIT_PUBLICADO_NO_REMOTO` e `COMMIT_PRESENTE_ANCESTRAL`

## 11. Situação do commit b7f37ed

- Existe localmente: sim
- Mensagem: `audit: implementa tabela institucional matriz no painel`
- Arquivos alterados: `dashboard/institutional_app.py`, `reports/implementacao_tabela_institucional_matriz_painel.md`, `tests/test_clean_app_formats.py`
- Branch(es) que contêm: `main`
- Está em HEAD atual: sim
- É ancestral do HEAD: sim
- Está publicado no remoto: não
- Classificação: `COMMIT_LOCAL_NAO_PUBLICADO` e `COMMIT_PRESENTE_NO_HEAD`

## 12. Linha histórica recente

| hash | mensagem | data | autor | branch | arquivos principais alterados | natureza aparente | status institucional |
| --- | --- | --- | --- | --- | --- | --- | --- |
| b7f37ed | audit: implementa tabela institucional matriz no painel | 2026-06-07 22:21 -0300 | lotoia-analytics | main | dashboard/institutional_app.py; reports/implementacao_tabela_institucional_matriz_painel.md; tests/test_clean_app_formats.py | painel; teste; relatório | LOCAL_NAO_PUBLICADO |
| 3efd905 | audit: aplica regra executavel e constroi celulas 16d | 2026-06-07 18:31 -0300 | lotoia-analytics | main / origin/main | reports/construcao_validacao_executiva_16d_top10_20_30_50.md | relatório | LEGITIMO_CANDIDATO |
| 0563c5b | audit: define regra executavel montagem 16d | 2026-06-07 17:56 -0300 | lotoia-analytics | main | reports/regra_executavel_montagem_16d.md | relatório | LEGITIMO_CANDIDATO |
| 97f3502 | audit: constroi e valida celulas 16d | 2026-06-07 17:45 -0300 | lotoia-analytics | main | reports/construcao_validacao_executiva_16d_top10_20_30_50.md | relatório | LEGITIMO_CANDIDATO |
| 332a233 | audit: valida celulas 16d top10 top20 top30 top50 | 2026-06-07 17:36 -0300 | lotoia-analytics | main | reports/validacao_real_celulas_16d_top10_20_30_50.md | relatório | LEGITIMO_CANDIDATO |
| 327f596 | audit: retifica classificacao 16d sem evidencia | 2026-06-07 17:29 -0300 | lotoia-analytics | main | reports/validacao_16d_por_escalas_top10_20_30_50.md | relatório | LEGITIMO_CANDIDATO |
| d055767 | audit: valida 16d por escalas top10 top20 top30 top50 | 2026-06-07 17:18 -0300 | lotoia-analytics | main | reports/validacao_16d_por_escalas_top10_20_30_50.md | relatório | LEGITIMO_CANDIDATO |
| 6293c2b | audit: prepara 16d a partir do modelo 15d fechado | 2026-06-07 17:13 -0300 | lotoia-analytics | main | reports/preparacao_auditada_16d_a_partir_15d_fechado.md | relatório | LEGITIMO_CANDIDATO |
| 362a551 | audit: fecha modelo 15d por escalas top10 top20 top30 top50 | 2026-06-07 16:56 -0300 | lotoia-analytics | main | reports/fechamento_definitivo_modelo_15d_top10_20_30_50.md | relatório | LEGITIMO_CANDIDATO |
| 6370ef9 | audit: registra matriz validacao 15d 23d por escala top | 2026-06-07 16:41 -0300 | lotoia-analytics | main | reports/matriz_institucional_validacao_15d_23d_top10_20_30_50.md | relatório | LEGITIMO_CANDIDATO |

## 13. Possíveis cópias paralelas encontradas

Nenhuma cópia paralela real do repositório foi identificada fora de `C:\Projetos\LotoIA`.

Diretórios encontrados dentro da árvore do próprio projeto:
- `C:\Projetos\LotoIA\backups` -> classificado como `BACKUP_CANDIDATO`
- `C:\Projetos\LotoIA\deployment\backup` -> classificado como `BACKUP_CANDIDATO`
- `C:\Projetos\LotoIA\tmp_daily_cleanup` -> classificado como `DIRETORIO_TEMPORARIO`
- `C:\Projetos\LotoIA\src\lotoia` -> diretório do código principal, não é cópia paralela
- `C:\Projetos\LotoIA\src\lotoia.egg-info` -> metadados de empacotamento, não é cópia paralela

Teste resumido nos diretórios encontrados:
- nenhum dos diretórios de backup/temp encontrados contém `.git`
- nenhum contém `dashboard/institutional_app.py`
- nenhum contém `clean_app.py`
- nenhum contém `lotoia_clean_zero.py`

## 14. Arquivos recentes de missão/emenda

Arquivos recentes relevantes encontrados no worktree:
- `reports/ativacao_menu_apagar_limpar_historico.md` -> modificado; origem aparente: relatório de missão anterior; rastreado pelo Git: sim; risco: MEDIO; ação futura: PRESERVAR / REVISAR
- `acl_backup.txt` -> untracked; origem aparente: backup auxiliar; rastreado pelo Git: não; risco: DESCONHECIDO; ação futura: ISOLAR
- `backups/SHA256SUMS.txt` -> untracked; origem aparente: backup; rastreado pelo Git: não; risco: BAIXO; ação futura: PRESERVAR
- `backups/lotoia_reports_institucionais_criticos_20260606_012541.zip` -> untracked; origem aparente: backup; rastreado pelo Git: não; risco: MEDIO; ação futura: ISOLAR
- `backups/lotoia_reports_manifest_20260606_012625.txt` -> untracked; origem aparente: backup; rastreado pelo Git: não; risco: BAIXO; ação futura: PRESERVAR
- `data/corrupted/*` -> untracked; origem aparente: artefatos de recuperação; rastreado pelo Git: não; risco: MEDIO/ALTO; ação futura: BLOQUEAR_INTEGRACAO
- `data/data/corrupted/*` -> untracked; origem aparente: artefatos de recuperação; rastreado pelo Git: não; risco: MEDIO/ALTO; ação futura: BLOQUEAR_INTEGRACAO
- `data/shared_backend_validation.db-shm` -> untracked; origem aparente: artefato SQLite; rastreado pelo Git: não; risco: MEDIO; ação futura: ISOLAR
- `data/shared_backend_validation.db-wal` -> untracked; origem aparente: artefato SQLite; rastreado pelo Git: não; risco: MEDIO; ação futura: ISOLAR
- `lotoia.db-shm` -> untracked; origem aparente: artefato SQLite; rastreado pelo Git: não; risco: MEDIO; ação futura: ISOLAR
- `lotoia.db-wal` -> untracked; origem aparente: artefato SQLite; rastreado pelo Git: não; risco: MEDIO; ação futura: ISOLAR
- `tmp_git_index` -> untracked; origem aparente: temporário Git; rastreado pelo Git: não; risco: MEDIO; ação futura: REMOVER_DEPOIS_DE_BACKUP
- `tmp_lotoia_test.db-shm` -> untracked; origem aparente: artefato SQLite temporário; rastreado pelo Git: não; risco: MEDIO; ação futura: ISOLAR
- `tmp_lotoia_test.db-wal` -> untracked; origem aparente: artefato SQLite temporário; rastreado pelo Git: não; risco: MEDIO; ação futura: ISOLAR

## 15. Arquivos principais verificados

### `dashboard/institutional_app.py`
- Existe: sim
- Rastreado pelo Git: sim
- Último commit que alterou: `b7f37ed audit: implementa tabela institucional matriz no painel`
- Status no worktree: modificado antes do stage? não; no momento desta auditoria não há indicação de alteração adicional além do commit local da Parte 1 planejada

### `clean_app.py`
- Existe: não encontrado como arquivo rastreado
- Rastreado pelo Git: não
- Último commit: não encontrado
- Status no worktree: ausente

### `lotoia_clean_zero.py`
- Existe: não encontrado como arquivo rastreado
- Rastreado pelo Git: não
- Último commit: não encontrado
- Status no worktree: ausente

### `tests/test_clean_app_formats.py`
- Existe: sim
- Rastreado pelo Git: sim
- Último commit que alterou: `b7f37ed audit: implementa tabela institucional matriz no painel`
- Status no worktree: modificado antes do stage? não; incluído no commit local da Parte 1

### `tests/test_global_batch_deduplication.py`
- Existe: sim
- Rastreado pelo Git: sim
- Último commit que alterou: `dec48d4 Add global batch deduplication guard`
- Status no worktree: limpo para esta missão

### `reports/implementacao_tabela_institucional_matriz_painel.md`
- Existe: sim
- Rastreado pelo Git: sim
- Último commit que alterou: `b7f37ed audit: implementa tabela institucional matriz no painel`
- Status no worktree: incluído no commit local da Parte 1

### `reports/construcao_validacao_executiva_16d_top10_20_30_50.md`
- Existe: sim
- Rastreado pelo Git: sim
- Último commit que alterou: `3efd905 audit: aplica regra executavel e constroi celulas 16d`
- Status no worktree: limpo para esta missão

## 16. Riscos identificados

- Worktree sujo com muitos artefatos temporários, backups e arquivos SQLite auxiliares.
- Commit local `b7f37ed` ainda não publicado no remoto, criando divergência local/remota.
- Há um arquivo de relatório previamente modificado no worktree (`reports/ativacao_menu_apagar_limpar_historico.md`) que não faz parte desta Parte 1.
- Não foram encontradas cópias paralelas reais fora da raiz auditada, o que reduz o risco de ambiguidade estrutural.

## 17. Pendências para Parte 2

- Decidir se o commit local `b7f37ed` deve ser publicado ou mantido local.
- Tratar os artefatos temporários e backups, se houver missão específica para saneamento.
- Definir se o relatório modificado `reports/ativacao_menu_apagar_limpar_historico.md` deve ser preservado, revisado ou isolado em missão separada.
- Confirmar o status operacional dos arquivos SQLite auxiliares e diretórios `data/corrupted` e `data/data/corrupted`.

## 18. Conclusão institucional

PARTE_1_APROVADA_REPOSITORIO_CANDIDATO_IDENTIFICADO
