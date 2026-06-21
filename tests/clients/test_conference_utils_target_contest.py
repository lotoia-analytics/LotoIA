"""Geração → Conferência: target_contest prospectivo real (PR #280 follow-up)."""

from __future__ import annotations

import pytest

from lotoia.clients import conference_utils
from lotoia.database.database import LotofacilOfficialHistory, create_database, get_session


@pytest.fixture(autouse=True)
def _isolate_database_url_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("DATABASE_URL", "LOTOIA_DATABASE_URL", "DATABASE_PUBLIC_URL", "LOTOIA_DATABASE_POOLER_URL"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture()
def db_path(tmp_path):
    path = tmp_path / "target_contest.db"
    create_database(path)
    with get_session(path) as session:
        session.add(
            LotofacilOfficialHistory(
                contest_number=3716,
                draw_date="01/01/2026",
                numbers=" ".join(f"{n:02d}" for n in range(1, 16)),
                numbers_signature="sig-3716",
                source="test",
                is_valid=1,
            )
        )
        session.add(
            LotofacilOfficialHistory(
                contest_number=5000,
                draw_date="01/01/2099",
                numbers=" ".join(f"{n:02d}" for n in range(1, 16)),
                numbers_signature="sig-5000",
                source="phantom",
                is_valid=0,
            )
        )
        session.commit()
    return path


def test_resolve_next_target_ignores_invalid_phantom_max(db_path) -> None:
    assert conference_utils.resolve_next_target_contest(db_path) == 3717


@pytest.mark.parametrize(
    ("candidate", "latest", "expected"),
    [
        (3717, 3716, True),
        (3716, 3716, False),
        (5000, 3716, False),
        (0, 3716, False),
        (None, 3716, False),
    ],
)
def test_is_valid_generation_target_contest(candidate, latest, expected) -> None:
    assert (
        conference_utils.is_valid_generation_target_contest(
            candidate,
            latest_drawn_contest=latest,
        )
        is expected
    )


def test_coerce_rejects_phantom_and_last_drawn(db_path) -> None:
    assert conference_utils.coerce_generation_target_contest(5000, db_path=db_path) == 3717
    assert conference_utils.coerce_generation_target_contest(3716, db_path=db_path) == 3717
    assert conference_utils.coerce_generation_target_contest(3717, db_path=db_path) == 3717


def test_institutional_persist_target_contest_from_generation_result(
    monkeypatch: pytest.MonkeyPatch,
    db_path,
) -> None:
    from dashboard import institutional_app as admin_app

    monkeypatch.setattr(admin_app, "DB_PATH", db_path)
    monkeypatch.setattr(
        admin_app,
        "get_latest_official_contest",
        lambda: {"contest_number": 3716, "dezenas": list(range(1, 16))},
    )

    assert admin_app._resolve_persist_target_contest({"target_contest": 3717}) == 3717
    assert admin_app._resolve_persist_target_contest({"target_contest": 5000}) == 3717
    assert admin_app._resolve_persist_target_contest({"target_contest": 3716}) == 3717
    assert admin_app._resolve_persist_target_contest({}) == 3717
