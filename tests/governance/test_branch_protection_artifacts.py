"""Valida artefatos de proteção da branch main e gate de governança."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_codeowners_covers_institutional_paths() -> None:
    text = (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    required_fragments = (
        "/docs/governance/",
        "/dashboard/",
        "@lotoia-analytics",
        "*lei15*",
        "*lei15a*",
        "/.github/",
    )
    for fragment in required_fragments:
        assert fragment in text


def test_governance_gate_workflow_declares_required_checks() -> None:
    workflow = (ROOT / ".github" / "workflows" / "governance-gate.yml").read_text(encoding="utf-8")
    for check in (
        "name: lint",
        "name: tests",
        "name: governance-contract-check",
        "name: lei15-lei15a-boundary-check",
        "name: dashboard-semantic-label-check",
        "name: dashboard-deploy-manifest-check",
    ):
        assert check in workflow


def test_branch_protection_documentation_exists() -> None:
    doc = ROOT / "docs" / "governance" / "BRANCH_PROTECTION_MAIN.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    assert "Require a pull request before merging" in text or "pull request" in text.lower()
    assert "governance-contract-check" in text


def test_institutional_check_scripts_exist() -> None:
    for script in (
        "scripts/checks/governance_contract_check.py",
        "scripts/checks/lei15_lei15a_boundary_check.py",
        "scripts/checks/dashboard_semantic_label_check.py",
        "scripts/checks/dashboard_deploy_manifest_check.py",
        "scripts/checks/railway_panel_deploy_sync_check.py",
        "scripts/apply_main_branch_protection.sh",
    ):
        assert (ROOT / script).exists()
