from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import lotoia
from lotoia_runtime import ensure_src_layout


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_PACKAGE = PROJECT_ROOT / "src" / "lotoia" / "__init__.py"


def test_parallel_lotoia_directory_was_removed() -> None:
    assert not (PROJECT_ROOT / "lotoia").exists()


def test_imported_lotoia_uses_official_src_layout() -> None:
    assert Path(lotoia.__file__).resolve() == OFFICIAL_PACKAGE.resolve()


def test_find_spec_resolves_official_package_after_bootstrap() -> None:
    ensure_src_layout()

    spec = importlib.util.find_spec("lotoia")

    assert spec is not None
    assert spec.origin is not None
    assert Path(spec.origin).resolve() == OFFICIAL_PACKAGE.resolve()


def test_bare_project_root_import_resolves_official_package() -> None:
    code = (
        "import lotoia, pathlib; "
        "print(pathlib.Path(lotoia.__file__).resolve())"
    )
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()).resolve() == OFFICIAL_PACKAGE.resolve()


def test_pythonpath_src_import_resolves_official_package() -> None:
    code = (
        "import lotoia, pathlib; "
        "print(pathlib.Path(lotoia.__file__).resolve())"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()).resolve() == OFFICIAL_PACKAGE.resolve()
