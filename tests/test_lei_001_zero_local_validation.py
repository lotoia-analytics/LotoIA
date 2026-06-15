from __future__ import annotations

import os

from scripts.checks.lei_001_zero_local_read_validation import run_validation


def test_lei_001_validation_passes_without_cloud_signals(monkeypatch) -> None:
    for env_name in (
        "LOTOIA_CLOUD_ONLY",
        "RAILWAY_ENVIRONMENT",
        "RAILWAY_PROJECT_ID",
        "DATABASE_URL",
        "LOTOIA_DATABASE_URL",
    ):
        monkeypatch.delenv(env_name, raising=False)

    report = run_validation(strict=False)
    assert report["status"] == "PASS"


def test_lei_001_validation_fails_in_strict_mode_with_sqlite(monkeypatch) -> None:
    for env_name in ("DATABASE_URL", "LOTOIA_DATABASE_URL", "LOTOIA_DATABASE_POOLER_URL"):
        monkeypatch.delenv(env_name, raising=False)

    report = run_validation(strict=True)
    assert report["status"] == "FAIL"
    assert any("sqlite" in error.lower() for error in report["errors"])


def test_lei_001_validation_passes_with_postgresql_url(monkeypatch) -> None:
    monkeypatch.setenv("LOTOIA_CLOUD_ONLY", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@postgres.railway.internal:5432/railway")

    report = run_validation(strict=True)
    assert report["status"] == "PASS"
