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
