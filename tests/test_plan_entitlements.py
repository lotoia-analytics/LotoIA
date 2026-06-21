"""Testes do plano único e fases de entitlement."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import inspect

from lotoia.clients.client_guard import validate_request
from lotoia.clients.constants import DAILY_LIMIT, DEFAULT_PLAN_ID
from lotoia.clients.plan_entitlements import (
    effective_formato_maximo,
    is_trial_phase,
    resolve_plan_for_activation,
    subscription_duration_days,
)
from lotoia.clients.repository import ClientRepository
from lotoia.database.database import LotoiaClient, create_database, get_engine, get_session


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "lotoia.db"
    create_database(path)
    return path


def _activate(db_path: Path, *, phone: str = "5511999999999", plan: str = DEFAULT_PLAN_ID) -> dict:
    return ClientRepository(db_path).activate_client(
        phone=phone,
        plan=plan,
        valor_pago=99.90,
        name="Ana",
    )


def _set_started_days_ago(db_path: Path, client_id: int, days: int) -> None:
    with get_session(db_path) as session:
        row = session.get(LotoiaClient, int(client_id))
        assert row is not None
        row.data_inicio = datetime.now(UTC) - timedelta(days=days)
        session.commit()


def test_resolve_legacy_plan_alias_to_completo() -> None:
    assert resolve_plan_for_activation("elite") == DEFAULT_PLAN_ID
    assert resolve_plan_for_activation("basico") == DEFAULT_PLAN_ID


def test_subscription_duration_is_seven_days_plus_twelve_months() -> None:
    assert subscription_duration_days(DEFAULT_PLAN_ID) == 372


def test_completo_trial_phase_allows_only_15d(db_path: Path) -> None:
    client = _activate(db_path)
    assert is_trial_phase(client) is True
    assert effective_formato_maximo(client) == 15
    blocked = validate_request("5511999999999", 20, 5, db_path=db_path)
    assert blocked.ok is False
    assert blocked.error_code == "FORMAT_NOT_ALLOWED"
    assert validate_request("5511999999999", 15, 5, db_path=db_path).ok is True


def test_completo_after_trial_allows_15_and_20d(db_path: Path) -> None:
    client = _activate(db_path)
    _set_started_days_ago(db_path, int(client["id"]), 8)
    refreshed = ClientRepository(db_path).get_by_phone("5511999999999")
    assert refreshed is not None
    assert is_trial_phase(refreshed) is False
    assert effective_formato_maximo(refreshed) == 20
    assert validate_request("5511999999999", 15, 5, db_path=db_path).ok is True
    assert validate_request("5511999999999", 20, 5, db_path=db_path).ok is True
    blocked = validate_request("5511999999999", 18, 5, db_path=db_path)
    assert blocked.ok is False
    assert blocked.error_code == "FORMAT_NOT_ALLOWED"


def test_client_status_exposes_effective_format(db_path: Path) -> None:
    client = _activate(db_path)
    status = ClientRepository(db_path).get_client_status("5511999999999")
    assert status is not None
    assert status["formato_maximo_efetivo"] == 15
    assert status["fase"] == "trial"
    assert status["dias_trial_restantes"] == 7


def test_database_creates_whatsapp_client_tables(db_path: Path) -> None:
    tables = set(inspect(get_engine(db_path)).get_table_names())
    assert "lotoia_clients" in tables


def test_validate_request_daily_limit_reached(db_path: Path) -> None:
    client = _activate(db_path)
    _set_started_days_ago(db_path, int(client["id"]), 8)
    repository = ClientRepository(db_path)
    repository.increment_daily_usage(int(client["id"]), quantidade=DAILY_LIMIT)
    result = validate_request("5511999999999", 20, 1, db_path=db_path)
    assert result.ok is False
    assert result.error_code == "DAILY_LIMIT_REACHED"
