from __future__ import annotations

from pathlib import Path

import dashboard.entrypoint_inventory as entrypoint_inventory
import dashboard.institutional_app as institutional_app
import dashboard.public_app as public_app
from dashboard.institutional_build import BUILD_MARKER


AUDIT_DOC = Path("docs/governance/AUDITORIA_CONSTITUCIONAL_FINAL_PAINEL_ADM_PUBLIC_APP_M_GOV_042.md")


def test_audit_report_exists_and_has_verdict() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    assert "M-GOV-042" in text
    assert "30/30 APROVADOS" in text
    assert "M-GOV-042 CONCLUÍDA — AUDITORIA CONSTITUCIONAL FINAL APROVADA" in text
    assert "FASE CONSTITUCIONAL DO PAINEL ADM E PUBLIC_APP ENCERRADA COM SUCESSO" in text


def test_build_markers_match_audit_base() -> None:
    assert institutional_app.APP_BUILD == BUILD_MARKER
    assert BUILD_MARKER == "institutional-adm-runtime-v25"
    assert public_app.PUBLIC_APP_BUILD == "public-surface-v1-m-plat-041"


def test_railway_entrypoint_is_institutional_adm() -> None:
    payload = entrypoint_inventory.build_entrypoint_inventory_snapshot(
        app_build=BUILD_MARKER,
        public_build=public_app.PUBLIC_APP_BUILD,
    )
    assert payload["railway_entrypoint"] == "dashboard/institutional_app.py"


def test_public_app_default_mode_is_public() -> None:
    assert entrypoint_inventory.resolve_dashboard_mode("public") == "public"


def test_mission_card_exists() -> None:
    card = Path(
        "docs/governance/gestao_projetos/cartoes/M-GOV-042_AUDITORIA_CONSTITUCIONAL_FINAL.md"
    )
    text = card.read_text(encoding="utf-8")
    assert "M-GOV-042" in text
    assert "CONCLUIDA" in text


def test_governance_mission_registry_includes_m_gov_042() -> None:
    from dashboard import institutional_governance

    mission_ids = {row["id"] for row in institutional_governance.MISSION_ROWS}
    assert "M-GOV-042" in mission_ids
