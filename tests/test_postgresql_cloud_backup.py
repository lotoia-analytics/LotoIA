from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.ops import postgresql_cloud_backup as backup


def test_default_backup_dir_uses_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOTOIA_BACKUP_OUTPUT_DIR", str(tmp_path / "cloud-backups"))
    assert backup.default_backup_dir() == tmp_path / "cloud-backups"


def test_run_backup_fails_without_database_url(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LOTOIA_DATABASE_URL", raising=False)
    try:
        backup.run_backup(output_dir=Path("/tmp/test-backup"), compress=True)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "DATABASE_URL ausente" in str(exc)


def test_run_backup_success_with_mocked_pg_dump(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@postgres.railway.internal:5432/railway")
    monkeypatch.setenv("LOTOIA_BACKUP_RETENTION_DAYS", "7")

    mock_completed = MagicMock()
    mock_completed.returncode = 0
    mock_completed.stderr = b""

    with patch.object(backup.shutil, "which", return_value="/usr/bin/pg_dump"):
        with patch.object(backup.subprocess, "run", return_value=mock_completed):
            report = backup.run_backup(output_dir=tmp_path, compress=True)

    assert report["status"] == "PASS"
    assert report["retention_days"] == 7
    assert str(tmp_path) in report["backup_file"]
