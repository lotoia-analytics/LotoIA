from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_monitored_contest as monitored_contest
from dashboard.institutional_build import BUILD_MARKER

OPERATOR_REFERENCE_CONTEST = 3712
OPERATOR_REFERENCE_DATE = "16/06/2026"
OPERATOR_REFERENCE_NUMBERS = (
    1,
    3,
    4,
    6,
    13,
    14,
    15,
    16,
    18,
    19,
    20,
    21,
    22,
    23,
    25,
)


def _record(
    contest_number: int,
    *,
    data: str = OPERATOR_REFERENCE_DATE,
    numbers: tuple[int, ...] = OPERATOR_REFERENCE_NUMBERS,
) -> dict[str, object]:
    return {
        "contest_number": contest_number,
        "data": data,
        "dezenas": list(numbers),
        "metadata_json": "{}",
    }


def test_institutional_app_build_v22_dados_048() -> None:
    assert institutional_app.APP_BUILD == BUILD_MARKER


def test_home_page_uses_postgresql_imported_contests_only() -> None:
    source = inspect.getsource(institutional_app._render_home_page)
    assert "build_imported_contests_selection_context" in source
    assert "_list_all_imported_contest_records" in source
    assert "_load_hai_latest_contest_summary" not in source
    assert "_load_latest_contest_summary" not in source
    assert "5000" not in source


def test_monitored_contest_module_has_no_hardcoded_operator_values() -> None:
    source = inspect.getsource(monitored_contest)
    assert "3712" not in source
    assert "5000" not in source
    assert "16/06/2026" not in source


def test_card_shows_latest_imported_contest_from_postgresql() -> None:
    card = monitored_contest.build_monitored_contest_card(
        load_latest_imported_contest=lambda: _record(OPERATOR_REFERENCE_CONTEST),
        load_imported_contest=lambda contest_number: _record(contest_number),
        operator_expected_contest=None,
    )

    assert card["contest_number"] == OPERATOR_REFERENCE_CONTEST
    assert card["display_contest_number"] == str(OPERATOR_REFERENCE_CONTEST)
    assert card["source"] == "PostgreSQL / imported_contests"
    assert card["sync_status"] == "OK"


def test_card_reports_sync_divergence_when_expected_not_persisted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(monitored_contest.ENV_OPERATOR_EXPECTED_CONTEST, raising=False)

    card = monitored_contest.build_monitored_contest_card(
        load_latest_imported_contest=lambda: _record(3700),
        load_imported_contest=lambda contest_number: _record(contest_number) if contest_number == 3700 else None,
        operator_expected_contest=OPERATOR_REFERENCE_CONTEST,
    )

    assert card["sync_status"] == "SYNC_DIVERGENCE"
    assert str(OPERATOR_REFERENCE_CONTEST) in card["sync_message"]
    assert "3700" in card["sync_message"]
    assert "Base oficial PostgreSQL desatualizada" in card["sync_message"]


def test_card_reports_empty_database_without_masking() -> None:
    card = monitored_contest.build_monitored_contest_card(
        load_latest_imported_contest=lambda: None,
        load_imported_contest=lambda _contest_number: None,
        operator_expected_contest=OPERATOR_REFERENCE_CONTEST,
    )

    assert card["sync_status"] == "SYNC_DIVERGENCE"
    assert "esperado pelo operador: 3712" in card["sync_message"]
    assert card["display_contest_number"] == "—"


def test_expected_contest_numbers_match_operator_reference() -> None:
    card = monitored_contest.build_monitored_contest_card(
        load_latest_imported_contest=lambda: _record(OPERATOR_REFERENCE_CONTEST),
        load_imported_contest=lambda contest_number: _record(contest_number),
        operator_expected_contest=OPERATOR_REFERENCE_CONTEST,
    )
    validated = monitored_contest.validate_expected_contest_numbers(
        card,
        expected_numbers=OPERATOR_REFERENCE_NUMBERS,
    )

    assert validated["numbers_validation_status"] == "OK"
    assert monitored_contest.contest_numbers_match(
        card["operator_expected_record"],
        OPERATOR_REFERENCE_NUMBERS,
    )


def test_expected_contest_numbers_mismatch_is_reported() -> None:
    card = monitored_contest.build_monitored_contest_card(
        load_latest_imported_contest=lambda: _record(
            OPERATOR_REFERENCE_CONTEST,
            numbers=tuple(range(1, 16)),
        ),
        load_imported_contest=lambda contest_number: _record(
            contest_number,
            numbers=tuple(range(1, 16)),
        ),
        operator_expected_contest=OPERATOR_REFERENCE_CONTEST,
    )
    validated = monitored_contest.validate_expected_contest_numbers(
        card,
        expected_numbers=OPERATOR_REFERENCE_NUMBERS,
    )

    assert validated["numbers_validation_status"] == "MISMATCH"
    assert str(OPERATOR_REFERENCE_CONTEST) in validated["numbers_validation_message"]


def test_operator_expected_contest_comes_from_env_not_hardcode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(monitored_contest.ENV_OPERATOR_EXPECTED_CONTEST, str(OPERATOR_REFERENCE_CONTEST))

    card = monitored_contest.build_monitored_contest_card(
        load_latest_imported_contest=lambda: _record(3700),
        load_imported_contest=lambda contest_number: _record(contest_number) if contest_number == 3700 else None,
    )

    assert card["operator_expected_contest"] == OPERATOR_REFERENCE_CONTEST
    assert card["sync_status"] == "SYNC_DIVERGENCE"


def test_conference_page_uses_imported_contests_not_official_history_max() -> None:
    source = inspect.getsource(institutional_app._render_conference_page)
    assert "build_imported_contests_selection_context" in source
    assert "_get_conference_contest_from_imported" in source
    assert "get_latest_official_contest()" not in source
    assert "get_official_contest(selected_contest)" not in source
    assert "5000" not in source


def test_outlier_filter_excludes_5000_when_cluster_is_3700s() -> None:
    records = [
        {"contest_number": 3710, "data": "01/01/2026", "dezenas": list(range(1, 16))},
        {"contest_number": 3711, "data": "02/01/2026", "dezenas": list(range(1, 16))},
        {"contest_number": 5000, "data": "01/01/2025", "dezenas": list(range(1, 16))},
    ]
    plausible_records, plausible_numbers, message = monitored_contest.filter_plausible_contest_records(records)

    assert plausible_numbers == [3710, 3711]
    assert len(plausible_records) == 2
    assert message is not None
    assert "5000" in message


def test_outlier_filter_uses_operator_expected_ceiling() -> None:
    records = [
        {"contest_number": 3712, "data": "16/06/2026", "dezenas": list(OPERATOR_REFERENCE_NUMBERS)},
        {"contest_number": 5000, "data": "01/01/2025", "dezenas": list(range(1, 16))},
    ]
    _, plausible_numbers, message = monitored_contest.filter_plausible_contest_records(
        records,
        operator_expected_contest=OPERATOR_REFERENCE_CONTEST,
    )

    assert plausible_numbers == [3712]
    assert message is not None
    assert "5000" in message


def test_conference_selection_rejects_invalid_three_number_contest() -> None:
    records = [
        {"contest_number": 3700, "data": "01/01/2026", "dezenas": list(range(1, 16))},
        {"contest_number": 5000, "data": "01/01/2025", "dezenas": [1, 2, 3]},
    ]
    selection = monitored_contest.build_imported_contests_selection_context(
        list_imported_contest_records=lambda: records,
        load_imported_contest=lambda contest_number: next(
            (record for record in records if int(record["contest_number"]) == int(contest_number)),
            None,
        ),
        official_history_max=5000,
    )

    assert selection["valid_contest_numbers"] == [3700]
    assert selection["max_contest"] == 3700
    assert selection["default_contest"] == 3700
    assert "5000" in selection["history_divergence_message"]


def test_conference_session_sanitizer_resets_invalid_5000() -> None:
    selected, message = monitored_contest.sanitize_conference_session_contest(
        session_contest=5000,
        valid_contest_numbers=[3700, 3711],
        default_contest=3711,
    )

    assert selected == 3711
    assert message is not None
    assert "5000" in message


def test_run_institutional_conference_prefers_imported_contests() -> None:
    source = inspect.getsource(institutional_app._run_institutional_conference)
    assert "_get_conference_contest_from_imported" in source
    assert source.index("_get_conference_contest_from_imported") < source.index("_load_official_history_contest")


def test_valid_lotofacil_record_requires_fifteen_dezenas() -> None:
    assert monitored_contest.is_valid_lotofacil_contest_record({"contest_number": 5000, "dezenas": [1, 2, 3]}) is False
    assert monitored_contest.is_valid_lotofacil_contest_record(
        {"contest_number": 3712, "dezenas": OPERATOR_REFERENCE_NUMBERS}
    )


def test_institutional_app_imports_cleanly() -> None:
    import dashboard.institutional_app  # noqa: F401
