# Railway Cloud-Only — Deploy Institucional

## Identificação

| Campo | Valor |
|-------|-------|
| Missão | Migração operação institucional cloud-only |
| Data | 2026-06-15 |
| Lei soberana | Lei No 001 — PostgreSQL fonte única |
| Runtime oficial | `dashboard/institutional_app.py` |
| Branch deploy | `main` → Railway |

---

## 1. Serviços Railway

| Serviço | Entrypoint | Porta |
|---------|------------|-------|
| Dashboard institucional | `dashboard/institutional_app.py` | `$PORT` (Railway) |
| FastAPI (WhatsApp/backend) | `uvicorn backend.main:app` | 8000 |
| Landing | `lotoia-landing` (Next.js) | `$PORT` |

**Procfile / railway.toml:** ambos apontam para `institutional_app.py`.

---

## 2. Variáveis Railway — obrigatórias (produção)

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `DATABASE_URL` | **Sim** | PostgreSQL Railway — fonte única (Lei No 001) |
| `LOTOIA_CLOUD_ONLY` | Recomendado | `1` — força política cloud-only |
| `LOTOIA_AUTH_REQUIRED` | Recomendado | `1` — login obrigatório no painel ADM |
| `LOTOIA_ADMIN_EMAIL` | **Sim** (bootstrap) | E-mail do admin inicial |
| `LOTOIA_ADMIN_PASSWORD` | **Sim** (bootstrap) | Senha do admin inicial (Railway Secrets) |
| `APP_ENV` | Recomendado | `production` |
| `PORT` | Auto (Railway) | Injetado pelo Railway |

### Variáveis opcionais

| Variável | Descrição |
|----------|-----------|
| `LOTOIA_DATABASE_URL` | Alias institucional de `DATABASE_URL` |
| `LOTOIA_DATABASE_POOLER_URL` | URL pooler (Supabase/Railway proxy) |
| `LOTOIA_SUPABASE_PROJECT_REF` | Ref Supabase para rewrite pooler |
| `LOTOIA_BACKUP_RETENTION_DAYS` | Retenção de dumps (`default: 14`) |
| `EVOLUTION_API_URL` | Evolution API WhatsApp |
| `EVOLUTION_API_KEY` | Chave Evolution |
| `EVOLUTION_INSTANCE_NAME` | Instância WhatsApp |

### Proibidas em produção

| Variável / padrão | Motivo |
|-------------------|--------|
| `sqlite:///` | Lei No 001 |
| `localhost` / `127.0.0.1` em `DATABASE_URL` | Cloud-only |
| Ausência de `DATABASE_URL` | Fallback SQLite silencioso |

---

## 3. Autenticação ADM

- Gate: `dashboard/institutional_auth.py`
- Serviço: `AuthenticationService` (`src/lotoia/authentication/service.py`)
- Bootstrap: primeiro login cria admin se `LOTOIA_ADMIN_EMAIL` + `LOTOIA_ADMIN_PASSWORD` configurados e tabela vazia
- Sessão: `st.session_state` apenas como cache de UI — persistência em `auth_sessions` PostgreSQL

---

## 4. Migrations cloud

```bash
python scripts/ops/apply_cloud_migrations.py
python scripts/ops/apply_cloud_migrations.py --dry-run
```

Migrations versionadas em `database/migrations/` com registro em `schema_migrations`.

---

## 5. Backup cloud

```bash
python scripts/ops/postgresql_cloud_backup.py
```

### Schedule recomendado (Railway Cron)

| Campo | Valor |
|-------|-------|
| Frequência | Diário 03:00 UTC |
| Comando | `python scripts/ops/postgresql_cloud_backup.py --json` |
| Storage | Volume Railway `/backups/postgresql` ou S3 externo |
| Retenção | `LOTOIA_BACKUP_RETENTION_DAYS=14` |

---

## 6. Scripts de validação

```bash
# Health-check PostgreSQL
python scripts/checks/postgresql_cloud_health_check.py

# Lei No 001 — zero leitura local
python scripts/checks/lei_001_zero_local_read_validation.py --strict

# Validação completa Railway
python scripts/checks/railway_production_validation.py
```

---

## 7. Confirmação CPU local desligado

Com Railway ativo e `DATABASE_URL` configurado:

1. Desligar processos locais (FastAPI, Streamlit, SQLite)
2. Acessar URL Railway do painel ADM
3. Login obrigatório deve aparecer
4. Geração, conferência e histórico devem ler PostgreSQL cloud
5. Scripts de validação devem retornar `PASS` no shell Railway

---

## 8. Evidências para o Auditor

| Entrega | Artefato |
|---------|----------|
| Deploy Railway | `railway.toml`, `Procfile` |
| Auth ADM | `dashboard/institutional_auth.py` |
| Fail-closed PG | `src/lotoia/governance/cloud_runtime_policy.py` |
| Variáveis auditadas | Este documento + `.env.example` |
| Migrations | `scripts/ops/apply_cloud_migrations.py` |
| Backup | `scripts/ops/postgresql_cloud_backup.py` |
| Health-check | `scripts/checks/postgresql_cloud_health_check.py` |
| Lei 001 | `scripts/checks/lei_001_zero_local_read_validation.py` |

---

## 9. Checklist pós-merge (PR #98)

### Status em 2026-06-15

| Etapa | Status | Evidência |
|-------|--------|-----------|
| PR #98 mergeado em `main` | **PASS** | merge commit `e2dce4c` |
| CI `governance-gate` | **PASS** | headSha `e2dce4c` |
| Deploy Railway produção | **PENDENTE** | SHA ativo `fb18ef7` — aguardar auto-deploy de `e2dce4c` |
| Variáveis Railway | **PENDENTE** | Configurar no painel (passo 9.1) |
| `RAILWAY_FULL_VALIDATION` | **PENDENTE** | Executar no shell Railway (passo 9.3) |

### 9.1 Configurar variáveis no Railway Dashboard

**Serviço:** dashboard institucional (`considerate-curiosity` ou equivalente)

1. Railway → projeto LotoIA → serviço Streamlit → **Variables**
2. Adicionar/atualizar:

```env
DATABASE_URL=${{Postgres.DATABASE_URL}}
LOTOIA_CLOUD_ONLY=1
LOTOIA_AUTH_REQUIRED=1
LOTOIA_ADMIN_EMAIL=admin@lotoia.chat
LOTOIA_ADMIN_PASSWORD=<gerar secret forte>
APP_ENV=production
LOTOIA_BACKUP_RETENTION_DAYS=14
```

3. **Não** usar `localhost` em `DATABASE_URL`
4. Salvar → Railway redeploya automaticamente

**Referência Postgres Railway:** se o serviço PostgreSQL estiver no mesmo projeto, use a variável referenciada `${{Postgres.DATABASE_URL}}` em vez de copiar URL manualmente.

### 9.2 Agendar backup (Railway Cron)

1. Railway → **Cron** (ou novo serviço cron)
2. Schedule: `0 3 * * *` (03:00 UTC diário)
3. Comando:

```bash
python scripts/ops/postgresql_cloud_backup.py --json
```

4. Montar volume em `/backups/postgresql` se persistência local de dumps for necessária

### 9.3 Validar no shell Railway

Após redeploy com SHA `e2dce4c` e variáveis configuradas:

```bash
# Checklist completo (recomendado)
python scripts/checks/railway_post_merge_checklist.py --expected-sha e2dce4c

# Ou passo a passo:
python scripts/checks/railway_production_validation.py --expected-sha e2dce4c
python scripts/checks/postgresql_cloud_health_check.py
python scripts/checks/lei_001_zero_local_read_validation.py --strict
python scripts/ops/apply_cloud_migrations.py
```

**Critério de sucesso:** todos retornam `PASS`.

### 9.4 Confirmar CPU local desligado

1. Parar Streamlit/FastAPI locais
2. Abrir URL Railway do painel ADM no navegador
3. Verificar tela de login institucional
4. Login com `LOTOIA_ADMIN_EMAIL` / `LOTOIA_ADMIN_PASSWORD`
5. Auditoria Runtime → `backend: postgresql`, `database_source: DATABASE_URL`

### 9.5 Modo deploy-only (sem shell Railway)

Para validar merge + CI a partir de qualquer ambiente com `gh`:

```bash
python scripts/checks/railway_post_merge_checklist.py --deploy-only --expected-sha e2dce4c
```

