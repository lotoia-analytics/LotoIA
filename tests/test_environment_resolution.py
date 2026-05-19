from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import lotoia
from lotoia.environment import validate_official_environment
from lotoia_runtime import ensure_src_layout


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_PACKAGE_DIR = PROJECT_ROOT / "src" / "lotoia"


def test_runtime_bootstrap_resolves_official_src_namespace() -> None:
    status = ensure_src_layout()

    assert status.is_official is True
    assert status.src_path == (PROJECT_ROOT / "src").resolve()
    assert OFFICIAL_PACKAGE_DIR.resolve() in status.package_origin.resolve().parents


def test_imported_lotoia_namespace_is_official_src_package() -> None:
    source_file = inspect.getsourcefile(lotoia)

    assert source_file is not None
    assert Path(source_file).resolve() == (OFFICIAL_PACKAGE_DIR / "__init__.py").resolve()


def test_environment_module_validates_official_namespace() -> None:
    status = validate_official_environment()

    assert status.is_official_namespace is True
    assert status.src_path == (PROJECT_ROOT / "src").resolve()


def test_script_runs_from_external_cwd_without_pythonpath(tmp_path: Path) -> None:
    script = PROJECT_ROOT / "scripts" / "run_basic_analysis.py"

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "LotoIA - analise inicial" in result.stdout
