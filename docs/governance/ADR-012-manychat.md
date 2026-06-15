# ADR-012 — ManyChat como Canal de Captação Facebook + Instagram

| Campo | Valor |
|-------|-------|
| **Status** | **Paused** — implementação suspensa |
| **Decisão estratégica** | Accepted (direção aprovada) |
| **Implementação M-094** | **On hold** desde 12/06/2026 |
| **Missão** | M-094 |
| **Substitui** | Integração nativa Messenger (webhook próprio + App Review Meta) |

---

## Contexto

A integração direta com Facebook Messenger via API nativa **não obteve aprovação operacional** (App Review Meta). O canal nativo permanece **descontinuado**.

A direção institucional era adotar **ManyChat** como porteiro de captação (Facebook Page + Instagram), direcionando leads para `www.lotoia.chat` e operação no **WhatsApp (Evolution API)**.

---

## Decisão vigente

| Item | Status |
|------|--------|
| Messenger nativo (webhook LotoIA) | **Descontinuado** — sem retomada sem nova ADR |
| ManyChat como canal de captação | **Direção aprovada, implementação pausada** |
| WhatsApp Evolution API | **Canal principal de operação** — inalterado |
| Painel ADM / card Canais (M-094) | **Não mergeado** — aguardando retomada |
| PR #96 (M-094) | **Fechado sem merge** |

---

## Motivo da pausa (12/06/2026)

Implementação ManyChat **suspensa por hora** a pedido institucional. Prioridade atual:

1. Estabilizar operação WhatsApp (geração + `RESULTADO`)
2. Retomar ManyChat apenas quando houver decisão explícita de go-live

Configuração parcial já iniciada no painel manychat.com pode permanecer, mas **não é canal institucional ativo** até nova autorização.

---

## Regra institucional (inalterada)

> **ManyChat é porteiro — não operador.**
> Captura lead e direciona para assinatura/WhatsApp.
> Nunca substitui o bot Evolution API.

---

## Canais operacionais ativos

| Canal | Função | Status |
|-------|--------|--------|
| WhatsApp (Evolution API) | Geração, conferência, assinantes | ✅ Operacional |
| `www.lotoia.chat` | Assinatura PIX | ✅ Operacional |
| Facebook/Instagram (ManyChat) | Captação | ⏸️ Pausado |
| Messenger nativo LotoIA | Atendimento | ⛔ Descontinuado |

---

## Retomada (quando autorizada)

1. Reabrir missão M-094 ou M-095 (trial seguidor, se aplicável)
2. Concluir fluxos ManyChat (DM Página FB, keywords, FAQ)
3. Mergear documentação e card ADM (ex-PR #96)
4. Atualizar este ADR para **Active**
5. Teste E2E com critérios de aceite do auditor

---

## Referências

- Missão M-094 (documentação completa na branch `cursor/m094-manychat-docs-b54e`, não mergeada)
- `docs/governance/COMUNICACAO_INSTITUCIONAL.md`
- Código Messenger legado: `backend/messenger_webhook.py`, `src/lotoia/clients/messenger_consultor/` — **não expandir**

---

## Histórico

| Data | Evento |
|------|--------|
| 12/06/2026 | ADR-012 criada — direção ManyChat aprovada (M-094) |
| 12/06/2026 | Implementação **pausada** — PR #96 fechado sem merge |
