from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import inspect

from lotoia.clients.client_guard import validate_request
from lotoia.clients.constants import DAILY_LIMIT
from lotoia.clients.repository import ClientRepository
from lotoia.database.database import LotoiaClient, create_database, get_engine, get_session


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "lotoia.db"
    create_database(path)
    return path


def _activate(db_path: Path, *, phone: str = "5511999999999", plan: str = "pro") -> dict:
    return ClientRepository(db_path).activate_client(phone=phone, plan=plan, valor_pago=49.99, name="Ana")


def test_database_creates_whatsapp_client_tables(db_path: Path) -> None:
    tables = set(inspect(get_engine(db_path)).get_table_names())
    assert "lotoia_clients" in tables
    assert "lotoia_client_daily_usage" in tables
    assert "lotoia_client_generations" in tables


def test_validate_request_client_not_found(db_path: Path) -> None:
    result = validate_request("5511888888888", 15, 5, db_path=db_path)
    assert result.ok is False
    assert result.error_code == "CLIENT_NOT_FOUND"


def test_validate_request_plan_expired(db_path: Path) -> None:
    client = _activate(db_path)
    with get_session(db_path) as session:
        row = session.get(LotoiaClient, int(client["id"]))
        assert row is not None
        row.data_expiracao = datetime.now(UTC) - timedelta(days=1)
        row.status = "expirado"
        session.commit()
    result = validate_request("5511999999999", 15, 5, db_path=db_path)
    assert result.ok is False
    assert result.error_code == "PLAN_EXPIRED"


def test_validate_request_format_not_allowed(db_path: Path) -> None:
    _activate(db_path, plan="basico")
    result = validate_request("5511999999999", 17, 5, db_path=db_path)
    assert result.ok is False
    assert result.error_code == "FORMAT_NOT_ALLOWED"
    assert "15D" in str(result.message)


def test_validate_request_plus_allows_15_and_16_only(db_path: Path) -> None:
    _activate(db_path, plan="plus")
    assert validate_request("5511999999999", 15, 5, db_path=db_path).ok is True
    assert validate_request("5511999999999", 16, 5, db_path=db_path).ok is True
    blocked = validate_request("5511999999999", 17, 5, db_path=db_path)
    assert blocked.ok is False
    assert blocked.error_code == "FORMAT_NOT_ALLOWED"


def test_validate_request_invalid_quantity(db_path: Path) -> None:
    _activate(db_path, plan="elite")
    result = validate_request("5511999999999", 20, 15, db_path=db_path)
    assert result.ok is False
    assert result.error_code == "INVALID_QUANTITY"


def test_validate_request_daily_limit_reached(db_path: Path) -> None:
    client = _activate(db_path, plan="elite")
    repository = ClientRepository(db_path)
    repository.increment_daily_usage(int(client["id"]), quantidade=DAILY_LIMIT)
    result = validate_request("5511999999999", 20, 1, db_path=db_path)
    assert result.ok is False
    assert result.error_code == "DAILY_LIMIT_REACHED"


def test_validate_request_daily_limit_partial(db_path: Path) -> None:
    client = _activate(db_path, plan="elite")
    repository = ClientRepository(db_path)
    repository.increment_daily_usage(int(client["id"]), quantidade=25)
    result = validate_request("5511999999999", 20, 10, db_path=db_path)
    assert result.ok is False
    assert result.error_code == "DAILY_LIMIT_PARTIAL"
    assert result.restante == 5


def test_validate_request_ok(db_path: Path) -> None:
    _activate(db_path, plan="pro")
    result = validate_request("5511999999999", 18, 10, db_path=db_path)
    assert result.ok is True
    assert result.formato == 18
    assert result.quantidade == 10
