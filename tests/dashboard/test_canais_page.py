from __future__ import annotations

from dashboard.pages.canais import build_canais_snapshot


def test_build_canais_snapshot_defaults(monkeypatch) -> None:
    monkeypatch.delenv("MANYCHAT_STATUS", raising=False)
    monkeypatch.delenv("MANYCHAT_CONTACTS", raising=False)
    snapshot = build_canais_snapshot()
    assert "Aguardando configuração" in snapshot["manychat_status"]
    assert snapshot["manychat_plan"] == "Free"
    assert snapshot["manychat_panel_url"].startswith("https://")
    assert snapshot["lotoia_chat_url"] == "https://www.lotoia.chat"


def test_build_canais_snapshot_active(monkeypatch) -> None:
    monkeypatch.setenv("MANYCHAT_STATUS", "ativo")
    monkeypatch.setenv("MANYCHAT_CONTACTS", "842")
    snapshot = build_canais_snapshot()
    assert snapshot["manychat_status"] == "✅ Ativo"
    assert snapshot["manychat_contacts"] == "842"
