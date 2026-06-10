# LotoIA — Baseline Institucional

## Identificação

```yaml
baseline_id: LOTOIA_INSTITUTIONAL_BASELINE_2026_06_10
status: approved_candidate
effective_date: 2026-06-10
runtime: institutional_app (PostgreSQL / Railway)
```

## Posicionamento

Baseline institucional candidata aprovada da plataforma LotoIA como **Plataforma
Estatística Estrutural com Assistência Supervisionada Incremental**.

Não é baseline de previsão lottery. É baseline de **governança operacional**,
rastreabilidade e fronteiras normativas entre Lei 15, Lei 15A, Lei 001 e ML assistivo.

---

## Locks obrigatórios

| Lock | Norma / evidência | Estado |
|------|-------------------|--------|
| `Lei_001_PostgreSQL_soberano` | `LEI_001_FONTE_UNICA_DA_VERDADE.md`, AUD-005 (#18), AUD-006 (em curso) | **Ativo** |
| `Lei_15_geracao_soberana` | `LEI_15_NUCLEO_OPERACIONAL_15D.md`, `ADR_LEI15_NUCLEO_15D_CONGELADO.md` | **Ativo** |
| `Lei_15A_registro_operacional` | `ADR_LEI15A_CARTAO_REGISTRO_APOSTA.md`, runtime 15D–20D | **Ativo** |
| `Conferencia_cartao_final_por_jogo` | AUD-004 (#15), `validate_conference_15d_source()` | **Ativo** |
| `ML_assistivo_nao_gerador` | `POLITICA_ML_ASSISTIVO.md`, ADR-042 | **Ativo** |
| `Main_protegida` | `BRANCH_PROTECTION_MAIN.md`, governance-gate CI | **Ativo** |
| `Legados_nao_operacionais` | `admin_app.py`, entrypoints legados fora do runtime institucional | **Ativo** |

### Regras dos locks

1. **Lei 001** — PostgreSQL Institucional é a única fonte operacional da verdade.
   CSV = export/auditoria/migração. `session_state` = cache/filtro transitório.
2. **Lei 15** — Geração soberana inalterável por ML, CSV ou painel observacional.
3. **Lei 15A** — Registro operacional de aposta (15D–20D); 21D–23D observacionais.
4. **Conferência** — `cartao_final` por jogo; proibido núcleo fixo repetido em 15D.
5. **ML assistivo** — Ranking, diagnóstico e validação apenas; nunca gerador central.
6. **Main protegida** — Merge apenas com CI verde e revisão institucional.
7. **Legados bloqueados** — `admin_app`, fluxos SQLite/CSV operacionais e quarentena
   não entram no caminho institucional publicado.

---

## Escopo congelado neste baseline

### Runtime oficial

- `dashboard/institutional_app.py`
- PostgreSQL via `DATABASE_URL` (Railway)
- Conferência → `reconciliation_runs` / `reconciliation_games`
- Histórico oficial → `lotofacil_official_history`

### Documentação normativa vinculada

- `docs/governance/LEI_001_FONTE_UNICA_DA_VERDADE.md`
- `docs/governance/GOVERNANCA_OPERACIONAL_LOTOIA.md`
- `docs/governance/LEI_15_NUCLEO_OPERACIONAL_15D.md`
- `docs/governance/ADR_LEI15_NUCLEO_15D_CONGELADO.md`
- `docs/governance/ADR_LEI15A_CARTAO_REGISTRO_APOSTA.md`
- `docs/governance/POLITICA_ML_ASSISTIVO.md`
- `docs/governance/BRANCH_PROTECTION_MAIN.md`

### Auditorias mergeadas até este baseline

| ID | Escopo | PR |
|----|--------|-----|
| AUD-004 | Conferência 15D `cartao_final` por jogo | #15 |
| AUD-005 | Remediação P0 Lei 001 | #18 |

### Em aberto (pós-baseline candidate)

| ID | Escopo | PR / branch |
|----|--------|-------------|
| AUD-006 | HAI DB-first (Histórico / Analítico / Institucional) | #25 `cursor/aud-006-db-first-hai-1a55` |
| DOC-001 | ADR expansão dimensional 15D→23D | #26 (draft) |
| DOC-002 | Rótulos semânticos painel Lei 15 / Lei 15A | #27 (draft) |

---

## Próximos passos (`next`)

```yaml
next:
  - validar_producao_railway_estavel
  - encerrar_AUD_005_pos_deploy
  - executar_AUD_006_DB_FIRST_HAI
  - manter_legados_bloqueados
```

### 1. `validar_producao_railway_estavel`

Critérios mínimos de aceite:

- `DATABASE_URL` apontando para PostgreSQL institucional
- Backend resolvido como `postgresql` na Auditoria Runtime
- Sync Caixa com `commit_state=ok` antes de sucesso visual
- Sem timeout de pool por sessão DB aninhada (hotfix #19)
- UI Conferência estável (hotfixes #20, #22)

### 2. `encerrar_AUD_005_pos_deploy`

Checklist de encerramento pós-deploy:

- [ ] `tests/test_aud_005_p0_lei_001.py` verde em produção
- [ ] `_get_latest_contest()` retorna concurso de `lotofacil_official_history`
- [ ] `_sync_latest_official_result_now()` não retorna `ok` sem commit
- [ ] Conferência resolve `reconciliation_runs` do DB antes de `session_state`
- [ ] Registro formal: `AUD_005_STATUS=ENCERRADO_POS_DEPLOY`

### 3. `executar_AUD_006_DB_FIRST_HAI`

Entrega esperada:

- Merge PR AUD-006 dedicado
- Testes: `db_first`, `no_csv_operational`, `no_session_truth`,
  `exports_from_db`, `no_nested_db_session`
- HAI (Histórico Analítico + Histórico Institucional + Auditoria) DB-first

### 4. `manter_legados_bloqueados`

- `admin_app.py` e entrypoints legados fora do fluxo operacional
- Quarentena institucional visível mas desabilitada na sidebar
- Nenhum fallback silencioso DB→CSV/session em páginas HAI

---

## Promoção de status

| De | Para | Condição |
|----|------|----------|
| `approved_candidate` | `approved_production` | `RAILWAY_VALIDATION_STATUS=PASS` + AUD-005 encerrado + AUD-006 mergeado (#25) |

---

## Histórico

| Data | Evento |
|------|--------|
| 2026-06-10 | Registro `LOTOIA_INSTITUTIONAL_BASELINE_2026_06_10` como `approved_candidate` |
| 2026-06-10 | PR #28 mergeado; deploy Railway `f263197` state=success; validação deploy em `RAILWAY_PRODUCTION_VALIDATION_2026_06_10.md` |
