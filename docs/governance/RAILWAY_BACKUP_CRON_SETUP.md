# Railway — Cron de Backup PostgreSQL

## Identificação

| Campo | Valor |
|-------|-------|
| Script | `scripts/ops/postgresql_cloud_backup.py` |
| Config cron | `railway.backup.toml` |
| Schedule | `0 3 * * *` (03:00 UTC diário) |
| Retenção | `LOTOIA_BACKUP_RETENTION_DAYS=14` (padrão) |
| Lei | Lei No 001 — PostgreSQL fonte única |

---

## Por que um serviço separado?

O painel Streamlit (`lotoia-production`) roda 24/7. Cron no Railway exige um **serviço dedicado** que executa, termina e libera recursos. Não se agenda cron no mesmo serviço do dashboard.

---

## Passo a passo no Railway

### 1. Criar o serviço de backup

1. Railway → projeto **LotoIA**
2. **+ New** → **GitHub Repo** → mesmo repositório `LotoIA`
3. Nome sugerido: `lotoia-postgresql-backup`

### 2. Config-as-code

1. Serviço `lotoia-postgresql-backup` → **Settings**
2. **Config File Path:** `railway.backup.toml`
3. Salvar (Railway redeploya com cron)

### 3. Variáveis de ambiente

| Variável | Valor |
|----------|--------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (referência ao Postgres do projeto) |
| `LOTOIA_BACKUP_OUTPUT_DIR` | `/backups/postgresql` |
| `LOTOIA_BACKUP_RETENTION_DAYS` | `14` |
| `APP_ENV` | `production` |

### 4. Volume persistente

1. Serviço `lotoia-postgresql-backup` → **Volumes**
2. **Add Volume**
3. Mount path: `/backups/postgresql`
4. Tamanho inicial: 1 GB (ajustar conforme crescimento)

Sem volume, os dumps ficam no disco efêmero e são perdidos entre execuções.

### 5. Confirmar cron

1. **Settings** → **Cron Schedule** deve mostrar: `0 3 * * *`
2. **Start Command** (via `railway.backup.toml`):

```bash
python scripts/ops/postgresql_cloud_backup.py --json --output-dir /backups/postgresql
```

### 6. Teste manual (antes de esperar o cron)

1. Serviço `lotoia-postgresql-backup` → **Deployments**
2. **Deploy** ou abrir **Shell** e executar:

```bash
python scripts/ops/postgresql_cloud_backup.py --json --output-dir /backups/postgresql
```

**Sucesso esperado:**

```json
{
  "status": "PASS",
  "backup_file": "/backups/postgresql/lotoia_<host>_YYYYMMDDTHHMMSSZ.sql.gz",
  "retention_days": 14
}
```

3. Verificar arquivo no volume:

```bash
ls -lh /backups/postgresql/
```

---

## Horário (UTC → Brasil)

| UTC | Brasília (UTC-3) |
|-----|------------------|
| 03:00 | 00:00 (meia-noite) |

Para backup às 03:00 Brasília, use cron `0 6 * * *`.

---

## Monitoramento

- **Logs** do serviço `lotoia-postgresql-backup` após cada execução
- Saída JSON com `status: PASS` ou `FAIL`
- Falhas comuns:
  - `pg_dump não encontrado` → `nixpacks.toml` não aplicado (rebuild)
  - `DATABASE_URL ausente` → variável não configurada
  - `pg_dump falhou` → credenciais ou rede Postgres

---

## Restauração (referência)

```bash
gunzip -c /backups/postgresql/lotoia_<host>_<timestamp>.sql.gz | psql "$DATABASE_URL"
```

Executar apenas em ambiente de recuperação, com validação institucional pós-restore (ADR-035).

---

## Checklist de conclusão

- [ ] Serviço `lotoia-postgresql-backup` criado
- [ ] `railway.backup.toml` configurado
- [ ] `DATABASE_URL` referenciado
- [ ] Volume `/backups/postgresql` montado
- [ ] Teste manual retorna `PASS`
- [ ] Primeira execução cron registrada nos logs
