from __future__ import annotations

import os

from lotoia.clients.result_conference_service import RESULTADO_CONFERENCE_FORMAT


def build_deploy_info() -> dict[str, str]:
    git_sha = (
        os.getenv("RAILWAY_GIT_COMMIT_SHA")
        or os.getenv("RAILWAY_GIT_COMMIT")
        or os.getenv("GIT_COMMIT_SHA")
        or ""
    ).strip()
    return {
        "git_sha": git_sha[:7] if git_sha else "local",
        "resultado_conference": RESULTADO_CONFERENCE_FORMAT,
    }
