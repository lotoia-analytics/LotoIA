# Relatório agent_plataforma — Rodada Multiagente

**Veredicto:** **CONCLUÍDO PARCIALMENTE — RISCOS MAPEADOS; AÇÕES SEGURAS ADIADAS A MISSÃO ALTO RISCO**

---

## Missões executadas

1. Mapeamento riscos Painel ADM
2. Avaliação segregação `public_app` × `institutional_app`
3. Rotas API `GET /generate/*`
4. `page_keys` órfãs
5. Entrypoint produção e build markers

---

## Arquivos lidos

- `railway.toml`, `Procfile`, `render.yaml`, `railway.api.toml`
- `dashboard/public_app.py`, `dashboard/institutional_app.py`
- `backend/main.py`
- `docs/governance/INVENTARIO_REDesenHO_CONCEITUAL_PAINEL_ADM_LEI15_CORE002.md`

---

## Arquivos alterados

Nenhum (auditoria documental nesta rodada).

---

## Implementado vs planejado

| Item | Status |
|------|--------|
| Relatório técnico | ✅ Este documento |
| Remoção páginas órfãs | ⏳ Planejado — missão média/alta (13k-line file) |
| Segregação public_app | ⏳ Plano only — **alto risco governance** |

---

## Riscos identificados

| ID | Risco | Severidade |
|----|-------|------------|
| P1 | `public_app.py` delega 100% para `institutional_app` — sem segregação | Alto (governance) |
| P2 | Deploy usa `institutional_app.py`; docs citam `public_app` | Médio (drift doc) |
| P3 | 10+ `page_key` órfãs em `main()` fora de `allowed_pages` | Médio |
| P4 | `_render_generation_page` com botões — código morto mas perigoso se re-wired | Médio |
| P5 | API `GET /generate/game` retorna 500 vs 422 inconsistente | Baixo |
| P6 | Build marker v7 OK; `institutional_light_mode.py` versionado | OK |

---

## Entrypoint produção

| Config | Entry |
|--------|-------|
| Railway Streamlit | `dashboard/institutional_app.py` |
| Railway API | `uvicorn backend.main:app` |
| `public_app` | Wrapper opcional — **não** entry Railway atual |

---

## Confirmações

- Geração: não executada
- Purge: não executado
- Banco/schema: não alterado
- LEI15_CORE_002: não alterado
- Lei 15A: não reativada
- ML operacional: não ativado
- public_app: **não removido**

---

## Próximos passos

- **M-PLAT-033** (proposta): Plano segregação public_app + normalização API 422
- **M-PLAT-034** (proposta): Limpeza órfãs `institutional_app` (faseada, com testes)
