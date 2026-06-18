#!/usr/bin/env python3
"""Gate de PR: alterações no dashboard exigem bump de BUILD_MARKER."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD_FILE = ROOT / "dashboard" / "institutional_build.py"
DASHBOARD_DIR = ROOT / "dashboard"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _git_diff_names(base_ref: str) -> list[str]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        completed = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _dashboard_paths_changed(changed_files: list[str]) -> bool:
    return any(path.startswith("dashboard/") for path in changed_files)


def _build_marker_changed(changed_files: list[str]) -> bool:
    target = BUILD_FILE.relative_to(ROOT).as_posix()
    return target in changed_files


def main() -> int:
    base_ref = str(__import__("os").getenv("GITHUB_BASE_REF", "origin/main") or "origin/main").strip()
    if not base_ref.startswith("origin/"):
        base_ref = f"origin/{base_ref}"

    changed_files = _git_diff_names(base_ref)
    if not changed_files:
        print("dashboard-deploy-manifest-check: PASS (sem diff detectável)")
        return 0

    if not _dashboard_paths_changed(changed_files):
        print("dashboard-deploy-manifest-check: PASS (dashboard inalterado)")
        return 0

    if not BUILD_FILE.exists():
        print("dashboard-deploy-manifest-check: FAIL — institutional_build.py ausente")
        return 1

    build_text = BUILD_FILE.read_text(encoding="utf-8")
    marker_line = next((line for line in build_text.splitlines() if line.startswith("BUILD_MARKER")), "")
    if not marker_line:
        print("dashboard-deploy-manifest-check: FAIL — BUILD_MARKER ausente")
        return 1

    from dashboard.institutional_build import BUILD_MARKER, DEPRECATED_BUILD_MARKERS

    if BUILD_MARKER in DEPRECATED_BUILD_MARKERS:
        print(f"dashboard-deploy-manifest-check: FAIL — BUILD_MARKER obsoleto: {BUILD_MARKER}")
        return 1

    if not _build_marker_changed(changed_files):
        print(
            "dashboard-deploy-manifest-check: FAIL — arquivos em dashboard/ alterados "
            f"sem bump de {BUILD_FILE.name} (BUILD_MARKER={BUILD_MARKER})"
        )
        print("  Arquivos alterados:")
        for path in changed_files:
            if path.startswith("dashboard/"):
                print(f"    - {path}")
        return 1

    print(f"dashboard-deploy-manifest-check: PASS (BUILD_MARKER={BUILD_MARKER})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
