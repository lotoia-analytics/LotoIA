from __future__ import annotations

from scripts.checks.railway_panel_deploy_sync_check import validate_panel_body


def test_validate_panel_body_passes_with_expected_build_and_sha() -> None:
    body = (
        "institutional-adm-runtime-v4 | commit=b5dd3ba12345 "
        "Jogos Gerados LotoIA — Acesso Institucional"
    )
    errors, evidence = validate_panel_body(
        body,
        expected_build="institutional-adm-runtime-v4",
        expected_sha="b5dd3bae6f7d6b5f78840fa9ea31f0f825783d95",
    )
    assert errors == []
    assert evidence["expected_build"] == "institutional-adm-runtime-v4"


def test_validate_panel_body_fails_on_stale_build_marker() -> None:
    body = "institutional-adm-runtime-v3 Gerador não carregado bloqueada na home"
    errors, _ = validate_panel_body(
        body,
        expected_build="institutional-adm-runtime-v4",
        expected_sha="b5dd3ba",
    )
    assert any("obsoleto" in error or "bloqueada" in error for error in errors)


def test_institutional_build_marker_not_deprecated() -> None:
    from dashboard.institutional_build import BUILD_MARKER, DEPRECATED_BUILD_MARKERS

    assert BUILD_MARKER not in DEPRECATED_BUILD_MARKERS
    assert BUILD_MARKER.startswith("institutional-adm-runtime-v")
