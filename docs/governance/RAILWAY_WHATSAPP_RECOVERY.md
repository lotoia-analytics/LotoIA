# Railway — Recuperação WhatsApp (geração de jogos)

## Cadeia operacional

```text
Usuário WhatsApp
  → Evolution API (evolution.lotoia)
  → POST /whatsapp/webhook (backend FastAPI)
  → gera jogos + PostgreSQL
  → Evolution envia resposta ao usuário
```

**Painel ADM (`lotoia-production`) não participa do WhatsApp.**

---

## Diagnóstico rápido (15/06/2026)

| Serviço | URL esperada | Sintoma |
|---------|--------------|---------|
| Backend FastAPI | `intuitive-gratitude-production.up.railway.app` | **Inacessível** — SSL/conexão falha |
| Evolution API | `evolution.lotoia.up.railway.app` | **Inacessível** |
| Painel Streamlit | `lotoia-production.up.railway.app` | **Ok** |

**Conclusão provável:** backend WhatsApp parado ou URL/domínio desatualizado. Evolution não consegue entregar webhook → **não gera jogos**.

---

## Passo 1 — Identificar o serviço backend no Railway

No mapa do projeto, procure o serviço que **não** é:

- `lotoia-production` (Streamlit)
- `hearty-upliftment` (backup cron)
- `Evolution API`
- `Postgres` / `Redis`

Candidatos comuns: `meticulous-creativity`, `terrific-contentment`, `intuitive-gratitude`.

Abra o serviço e confira **Start Command**:

| Tipo | Comando |
|------|---------|
| Backend WhatsApp (certo) | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
| Painel (errado para WhatsApp) | `streamlit run dashboard/institutional_app.py ...` |

Se estiver Streamlit, esse serviço **não** processa WhatsApp.

---

## Passo 2 — Configurar backend (se ausente ou errado)

### Config file (recomendado)

1. Serviço backend → **Settings** → **Config File Path:** `railway.api.toml`
2. Salvar → redeploy

### Variáveis obrigatórias

| Variável | Valor |
|----------|--------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `EVOLUTION_API_URL` | `https://evolution.lotoia.up.railway.app` |
| `EVOLUTION_API_KEY` | chave da Evolution |
| `EVOLUTION_INSTANCE_NAME` | nome da instância WhatsApp |
| `APP_ENV` | `production` |
| `LOTOIA_CLOUD_ONLY` | `1` |

### Domínio público

1. Serviço backend → **Settings** → **Networking** → **Generate Domain**
2. Anote a URL (ex.: `https://seu-backend.up.railway.app`)

---

## Passo 3 — Testar backend

No navegador ou curl:

```text
https://<seu-backend>/health
→ {"status":"ok", ...}

https://<seu-backend>/whatsapp/status
→ "configured": true na seção evolution
```

Script (shell Railway ou local com vars):

```bash
python scripts/checks/whatsapp_stack_health_check.py --backend-url https://<seu-backend>
```

---

## Passo 4 — Configurar webhook na Evolution

Na Evolution API (painel ou API), webhook deve apontar para:

```text
https://<seu-backend>/whatsapp/webhook
```

**Não** use `intuitive-gratitude` se esse domínio estiver morto — use o domínio **ativo** do Passo 2.

Eventos: `MESSAGES_UPSERT` (ou equivalente inbound).

---

## Passo 5 — Evolution API no ar

1. Serviço **Evolution API** → status **Running**
2. Instância WhatsApp **conectada** (QR escaneado)
3. Teste: enviar `oi` no WhatsApp → deve responder menu

---

## Erros comuns (usuário recebe mensagem mas não jogos)

| Sintoma | Causa | Ação |
|---------|-------|------|
| "Número não cadastrado" | Cliente ausente no PostgreSQL | Ativar via `/client/activate` ou Asaas |
| "Plano expirou" | `data_expiracao` vencida | Renovar assinatura |
| "Erro ao gerar jogos" | Falha na geração (DB/engine) | Logs do backend |
| Silêncio total | Webhook não chega / backend down | Passos 1–4 |
| Jogos gerados mas não entregues | Evolution delivery fail | Logs `EVOLUTION_DELIVERY_FAILED` |

---

## Checklist de conclusão

- [ ] Serviço backend com `uvicorn backend.main:app`
- [ ] `/health` → ok
- [ ] `/whatsapp/status` → evolution configured
- [ ] Webhook Evolution → `/whatsapp/webhook` URL correta
- [ ] Evolution instância conectada
- [ ] Teste: `oi` → menu; escolher quantidade → jogos
