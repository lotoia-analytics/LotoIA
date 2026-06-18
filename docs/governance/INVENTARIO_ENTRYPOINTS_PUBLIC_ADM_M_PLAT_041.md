# Inventário de Entrypoints — public_app x ADM Institucional (M-PLAT-041)

**Missão:** `M-PLAT-041`  
**Build ADM:** `institutional-adm-runtime-v17`  
**Build público:** `public-surface-v1-m-plat-041`

---

## Decisão aplicada — Opção A

Railway **permanece** em `dashboard/institutional_app.py` (ADM intacto em produção).

`dashboard/public_app.py` default = **canal público seguro**. Modo ADM somente com
`LOTOIA_DASHBOARD_MODE=institutional` explícito (opt-in — dev/legado).

**Não** foi necessário parar por `FLUXO CONTÍNUO PARCIAL — ENTRYPOINT PUBLIC_APP SERVE ADM`:
Procfile e `railway.toml` já apontam para `institutional_app.py`.

---

## Entrypoints

| Entrypoint | Papel | Railway |
|------------|-------|---------|
| `dashboard/institutional_app.py` | Painel ADM institucional — produção | **SIM** |
| `dashboard/public_app.py` | Canal público (default) ou ADM via env | NÃO |
| `dashboard/app.py` | Streamlit Cloud → delega ADM | NÃO |
| `Procfile` / `railway.toml` | Config deploy | **SIM** → institutional |

---

## Variável de ambiente

| Variável | Valores | Default |
|----------|---------|---------|
| `LOTOIA_DASHBOARD_MODE` | `public`, `institutional` (aliases: `adm`, `admin`) | `public` |

---

## Canal público — o que NÃO expõe

- Governança Institucional — read-only
- Núcleo Lei 15 — CORE_002 (ADM)
- Gerador ADM CORE_002
- Conferir Resultados / Auditoria (ADM)
- Simulação Institucional / Backtesting (ADM)
- Central ML Assistiva / Vazamento Lateral (ADM)
- Área Restrita — Limpeza Controlada (ADM)
- Histórico institucional interno

---

## Veredicto

**M-PLAT-041 CONCLUÍDA E ATIVA EM PRODUÇÃO — PUBLIC_APP SEPARADO DO ADM INSTITUCIONAL COM SEGURANÇA**
