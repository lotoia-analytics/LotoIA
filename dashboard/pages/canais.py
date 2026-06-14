from __future__ import annotations

import os
from typing import Any

import streamlit as st

_STATUS_LABELS = {
    "ativo": "✅ Ativo",
    "aguardando_configuracao": "⏳ Aguardando configuração",
    "inativo": "⛔ Inativo",
}


def _read_manychat_config() -> dict[str, str]:
    return {
        "panel_url": os.getenv("MANYCHAT_PANEL_URL", "https://app.manychat.com/").strip(),
        "status": os.getenv("MANYCHAT_STATUS", "aguardando_configuracao").strip().lower(),
        "contacts": os.getenv("MANYCHAT_CONTACTS", "").strip(),
        "plan": os.getenv("MANYCHAT_PLAN", "Free").strip(),
        "lotoia_chat_url": os.getenv("LOTOIA_CHAT_URL", "https://www.lotoia.chat").strip(),
    }


def _manychat_status_label(status: str) -> str:
    return _STATUS_LABELS.get(status, f"ℹ️ {status}")


def build_canais_snapshot() -> dict[str, Any]:
    config = _read_manychat_config()
    contacts_display = config["contacts"] if config["contacts"] else "— (informar após go-live)"
    return {
        "manychat_status": _manychat_status_label(config["status"]),
        "manychat_plan": config["plan"],
        "manychat_contacts": contacts_display,
        "manychat_panel_url": config["panel_url"],
        "lotoia_chat_url": config["lotoia_chat_url"],
    }


def render_canais_page() -> None:
    snapshot = build_canais_snapshot()

    st.subheader("Canais de Comunicação")
    st.caption(
        "Referência operacional M-094. ManyChat é porteiro de captação; "
        "WhatsApp (Evolution API) permanece como canal principal de operação."
    )

    col_fb, col_wa = st.columns(2)

    with col_fb:
        st.markdown("#### 📘 Facebook / Instagram")
        st.markdown(f"**Canal:** ManyChat")
        st.markdown(f"**Status:** {snapshot['manychat_status']}")
        st.markdown("**Função:** Captação → WhatsApp")
        st.markdown(f"**Contatos:** {snapshot['manychat_contacts']}")
        st.markdown(f"**Plano:** {snapshot['manychat_plan']}")
        st.link_button("Abrir painel ManyChat", snapshot["manychat_panel_url"], use_container_width=True)
        st.info(
            "Canal de captação — não de operação. "
            "Responde DM e comentários e direciona para assinatura."
        )

    with col_wa:
        st.markdown("#### 📱 WhatsApp")
        st.markdown("**Canal:** Evolution API")
        st.markdown("**Status:** ✅ Operacional")
        st.markdown("**Função:** Geração de jogos + conferência RESULTADO")
        st.markdown(f"**Assinatura:** [{snapshot['lotoia_chat_url']}]({snapshot['lotoia_chat_url']})")
        st.success(
            "Canal principal de operação. Bot institucional com PostgreSQL (Lei No 001)."
        )

    st.markdown("---")
    st.markdown("#### Palavras-chave ManyChat (M-094)")
    st.markdown(
        """
| Keyword | Ação |
|---------|------|
| `PLANOS` / `PREÇO` | Tabela de planos + link de assinatura |
| `COMO FUNCIONA` | Explicação dos pilares estatísticos + link |
| `RESULTADO` | Direciona para assinantes via WhatsApp |
| `OI` / `OLÁ` | Boas-vindas padrão |
        """
    )

    st.markdown("#### Checklist ADM (configuração manual)")
    st.markdown(
        """
1. Criar conta em [manychat.com](https://manychat.com)
2. Conectar Página Facebook **LotoIA**
3. Conectar Instagram **LotoIA**
4. Configurar fluxos DM Facebook, DM Instagram, comentários e keywords (M-094)
5. Testar E2E: comentário → DM → `www.lotoia.chat` → assinatura → jogos no WhatsApp
6. Atualizar variáveis `MANYCHAT_STATUS=ativo` e `MANYCHAT_CONTACTS` no Railway após go-live
        """
    )

    st.caption(
        "ADR-012: `docs/governance/ADR-012-manychat.md` — integração nativa Messenger descontinuada."
    )
