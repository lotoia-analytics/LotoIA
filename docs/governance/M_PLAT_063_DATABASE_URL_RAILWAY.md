# M-PLAT-063 — Corrigir DATABASE_URL no Railway

**Status:** procedimento operacional  
**Variável soberana:** `DATABASE_URL`  
**Compatibilidade temporária:** `DATABASE_PUBLIC_URL` (proxy TCP público)

---

## Problema

`DATABASE_URL` configurado como texto literal `DATABASE_URL` em vez de connection string PostgreSQL.

**Sintoma:** serviços não conectam; workaround manual `export DATABASE_URL="$DATABASE_PUBLIC_URL"`.

---

## Correção no Railway (obrigatória)

Para **cada** serviço que usa banco (Streamlit, FastAPI/WhatsApp, backup cron):

1. Railway → projeto LotoIA → serviço → **Variables**
2. Editar `DATABASE_URL`:
   ```env
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   ```
3. **Não** usar valor literal `DATABASE_URL`
4. Salvar → aguardar redeploy

### Serviços a conferir

| Serviço | Config file |
|---------|-------------|
| Painel institucional | `railway.toml` |
| Backend WhatsApp | `railway.api.toml` |
| Backup cron | `railway.backup.toml` |

### DATABASE_PUBLIC_URL (opcional, temporário)

Manter apenas se necessário para Cloud Agent / acesso externo ao proxy TCP:

```env
DATABASE_PUBLIC_URL=postgresql://postgres:***@shortline.proxy.rlwy.net:PORTA/railway
```

Não é caminho principal após M-PLAT-063.

---

## Validação

```bash
python scripts/checks/postgresql_cloud_health_check.py
python scripts/ops/apply_cloud_migrations.py
```

**PASS esperado:** `database_source: DATABASE_URL` (não `DATABASE_PUBLIC_URL`).

---

## Segurança

- Não commitar `.env`
- Não colar connection string em chat, PR ou logs
- Não usar literal `DATABASE_URL` como fallback válido
