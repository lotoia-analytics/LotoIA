# Railway — DATABASE_URL para consultas do agente Cloud / dev local

**Atenção:** use só para desenvolvimento/consulta. Não commitar `.env`. Não colar senha no chat.

---

## Cursor Cloud Agent (recomendado — o agente consulta sozinho)

Para o **Cloud Agent** rodar SQL e scripts (`generations_today_query.py`, health-check) sem você colar queries no Railway shell:

### 1. Postgres com TCP público (Railway)

1. Railway → projeto LotoIA → serviço **Postgres**
2. **Settings** → **Networking** → ative **TCP Proxy** / **Public Networking**
3. Anote **host** e **porta** (ex.: `shortline.proxy.rlwy.net:32647`)

### 2. Montar `DATABASE_URL`

```text
postgresql://postgres:SENHA@HOST_PUBLICO:PORTA/railway
```

- **SENHA:** Postgres → **Variables** → `POSTGRES_PASSWORD`
- **HOST/PORTA:** do TCP proxy (não use `postgres.railway.internal`)

### 3. Secret no Cursor (não no GitHub)

1. Abra [cursor.com/dashboard](https://cursor.com/dashboard) → **Cloud Agents** → **Secrets**
2. Adicione:
   - **Nome:** `DATABASE_URL`
   - **Valor:** URL completa do passo 2
   - **Tipo:** **Runtime Secret** (senha não aparece no chat nem em commits)
3. Salve e **inicie um novo Cloud Agent** (secrets novos não entram em sessões já abertas)

### 4. Validar (o agente roda isto)

```bash
source .venv/bin/activate
python scripts/checks/postgresql_cloud_health_check.py
python scripts/checks/generations_today_query.py --json
```

Se `PASS`, o agente passa a consultar o PostgreSQL de produção diretamente.

**Estado atual deste workspace:** `.env` local usa placeholder `SUA_SENHA` — conexão falha até o secret `DATABASE_URL` existir no dashboard Cursor.

---

## Dev local (opcional — seu PC)

### Passo 1 — Ativar rede pública no Postgres (Railway)

1. Railway → projeto LotoIA → serviço **Postgres**
2. Aba **Settings**
3. Seção **Networking** (ou **Public Networking**)
4. Ative **TCP Proxy** / **Public Networking**
5. Anote:
   - **Host público** (ex.: `containers-us-west-xxx.railway.app`)
   - **Porta** (ex.: `5432` ou porta proxy)
   - Usuário, senha, database (já existem na variável interna)

---

## Passo 2 — Montar URL pública

Formato:

```text
postgresql://postgres:SENHA@HOST_PUBLICO:PORTA/railway
```

**Onde achar a senha:** Postgres → **Variables** → `POSTGRES_PASSWORD` ou referência em `DATABASE_URL` interna.

**Substitua:**
- `HOST_PUBLICO` → host do TCP proxy (não use `postgres.railway.internal`)
- `PORTA` → porta pública do proxy
- `SENHA` → senha do Postgres

---

## Passo 3 — Criar `.env` no workspace (local)

Na raiz do projeto LotoIA:

```bash
cp .env.example .env
```

Edite `.env` e descomente/configure:

```env
DATABASE_URL=postgresql://postgres:SUA_SENHA@HOST_PUBLICO:PORTA/railway
APP_ENV=development
```

**Não** use `LOTOIA_CLOUD_ONLY=1` no `.env` local (senão fail-closed bloqueia sem necessidade).

---

## Passo 4 — Testar conexão

```bash
source .venv/bin/activate
python scripts/checks/postgresql_cloud_health_check.py
```

Esperado: `postgresql-cloud-health-check: PASS`

---

## Passo 5 — Consultar gerações de hoje

```bash
python scripts/checks/generations_today_query.py
```

Ou com data específica:

```bash
python scripts/checks/generations_today_query.py --date 2026-06-15 --json
```

---

## Segurança

| Regra | Motivo |
|-------|--------|
| `.env` no `.gitignore` | Senha não vai pro GitHub |
| Não colar senha no chat | Exposição |
| Preferir IP allowlist no Railway | Se disponível no plano |
| Desativar TCP público quando não usar | Reduz superfície de ataque |

---

## Alternativa mais segura (sem URL pública)

Rodar no **shell Railway** (`intuitive-gratitude` ou Postgres):

```bash
python scripts/checks/generations_today_query.py
```

Lá `DATABASE_URL` já existe via `${{Postgres.DATABASE_URL}}` — sem expor Postgres à internet.
