from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, create_engine
from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DEFAULT_DATABASE_PATH = Path("data/lotoia.db")


class Base(DeclarativeBase):
    pass


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    contests: Mapped[int] = mapped_column(Integer, nullable=False)
    games_per_contest: Mapped[int] = mapped_column(Integer, nullable=False)
    pool_size: Mapped[int] = mapped_column(Integer, nullable=False)
    history_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lotoia_average_hits: Mapped[float] = mapped_column(Float, nullable=False)
    filtered_average_hits: Mapped[float] = mapped_column(Float, nullable=False)
    random_average_hits: Mapped[float] = mapped_column(Float, nullable=False)
    superiority_rate: Mapped[float] = mapped_column(Float, nullable=False)
    average_advantage: Mapped[float] = mapped_column(Float, nullable=False)
    standard_deviation: Mapped[float] = mapped_column(Float, nullable=False)
    report_path: Mapped[str] = mapped_column(String, default="", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    contests: Mapped[int] = mapped_column(Integer, nullable=False)
    games_per_contest: Mapped[int] = mapped_column(Integer, nullable=False)
    average_hits: Mapped[float] = mapped_column(Float, nullable=False)
    hit_distribution: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    correlation: Mapped[float] = mapped_column(Float, nullable=False)
    stability: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    best_game: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    worst_game: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    report_path: Mapped[str] = mapped_column(String, default="", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class CalibrationRun(Base):
    __tablename__ = "calibration_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    weight_configuration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    average_hits: Mapped[float] = mapped_column(Float, nullable=False)
    correlation: Mapped[float] = mapped_column(Float, nullable=False)
    stability: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    report_path: Mapped[str] = mapped_column(String, default="", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    whatsapp: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String, default="public", nullable=False)
    ip_hash: Mapped[str] = mapped_column(String, default="", nullable=False)
    user_agent: Mapped[str] = mapped_column(String, default="", nullable=False)
    __table_args__ = (
        Index("ix_leads_created_at", "created_at"),
        Index("ix_leads_whatsapp", "whatsapp"),
        Index("ix_leads_source", "source"),
    )


class GenerationEvent(Base):
    __tablename__ = "generation_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    generated_games: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    ml_enabled: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    ranking_score: Mapped[float] = mapped_column(Float, nullable=False)
    execution_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    __table_args__ = (
        Index("ix_generation_events_created_at", "created_at"),
        Index("ix_generation_events_lead_id", "lead_id"),
        Index("ix_generation_events_ml_enabled", "ml_enabled"),
    )


class CheckEvent(Base):
    __tablename__ = "check_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    contest_id: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_numbers: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    hits: Mapped[int] = mapped_column(Integer, nullable=False)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    __table_args__ = (
        Index("ix_check_events_created_at", "created_at"),
        Index("ix_check_events_lead_id", "lead_id"),
        Index("ix_check_events_contest_id", "contest_id"),
    )


class ImportedContest(Base):
    __tablename__ = "imported_contests"

    contest_number: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    data: Mapped[str] = mapped_column(String, default="", nullable=False)
    dezenas: Mapped[str] = mapped_column(String, default="", nullable=False)
    metadata_json: Mapped[str] = mapped_column(String, default="{}", nullable=False)


class GeneratedGame(Base):
    __tablename__ = "generated_games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    generation_event_id: Mapped[int] = mapped_column(Integer, nullable=False)
    lead_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_contest: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origin: Mapped[str] = mapped_column(String, default="dashboard", nullable=False)
    generation_mode: Mapped[str] = mapped_column(String, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    game_index: Mapped[int] = mapped_column(Integer, nullable=False)
    numbers: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    profile_type: Mapped[str] = mapped_column(String, default="", nullable=False)
    final_score: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    quadra_score: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    generation_event_id: Mapped[int] = mapped_column(Integer, nullable=False)
    lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contest_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String, default="official_result", nullable=False)
    status: Mapped[str] = mapped_column(String, default="reconciled", nullable=False)
    prize_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_hits: Mapped[int] = mapped_column(Integer, nullable=False)
    best_hits: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ReconciliationGame(Base):
    __tablename__ = "reconciliation_games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reconciliation_run_id: Mapped[int] = mapped_column(Integer, nullable=False)
    generation_event_id: Mapped[int] = mapped_column(Integer, nullable=False)
    lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contest_id: Mapped[int] = mapped_column(Integer, nullable=False)
    game_index: Mapped[int] = mapped_column(Integer, nullable=False)
    numbers: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    hits: Mapped[int] = mapped_column(Integer, nullable=False)
    matched_numbers: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    prize_status: Mapped[str] = mapped_column(String, default="nao_premiado", nullable=False)
    prize_tier: Mapped[str] = mapped_column(String, default="", nullable=False)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


def database_url(path: Path = DEFAULT_DATABASE_PATH) -> str:
    return f"sqlite:///{path}"


def get_engine(path: Path = DEFAULT_DATABASE_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url(path), future=True)

    @event.listens_for(engine, "connect")
    def _configure_sqlite(dbapi_connection, connection_record):  # type: ignore[unused-ignore]
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA wal_autocheckpoint=100;")
            cursor.close()
        except Exception:
            pass

    return engine


def create_database(path: Path = DEFAULT_DATABASE_PATH) -> None:
    engine = get_engine(path)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS imported_contests (
                contest_number INTEGER PRIMARY KEY NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL DEFAULT '',
                dezenas TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS generated_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generation_event_id INTEGER NOT NULL,
                lead_id INTEGER NOT NULL,
                target_contest INTEGER,
                origin TEXT NOT NULL DEFAULT 'dashboard',
                generation_mode TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                game_index INTEGER NOT NULL,
                numbers JSON NOT NULL,
                profile_type TEXT NOT NULL DEFAULT '',
                final_score JSON NOT NULL DEFAULT '{}',
                quadra_score JSON NOT NULL DEFAULT '{}',
                context_json JSON NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS reconciliation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generation_event_id INTEGER NOT NULL,
                lead_id INTEGER,
                contest_id INTEGER NOT NULL,
                source TEXT NOT NULL DEFAULT 'official_result',
                status TEXT NOT NULL DEFAULT 'reconciled',
                prize_count INTEGER NOT NULL,
                total_hits INTEGER NOT NULL,
                best_hits INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                payload JSON NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS reconciliation_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reconciliation_run_id INTEGER NOT NULL,
                generation_event_id INTEGER NOT NULL,
                lead_id INTEGER,
                contest_id INTEGER NOT NULL,
                game_index INTEGER NOT NULL,
                numbers JSON NOT NULL,
                hits INTEGER NOT NULL,
                matched_numbers JSON NOT NULL,
                prize_status TEXT NOT NULL DEFAULT 'nao_premiado',
                prize_tier TEXT NOT NULL DEFAULT '',
                context_json JSON NOT NULL DEFAULT '{}'
            )
            """
        )
        generated_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(generated_games)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE generated_games ADD COLUMN target_contest INTEGER", "target_contest"),
            ("ALTER TABLE generated_games ADD COLUMN origin TEXT NOT NULL DEFAULT 'dashboard'", "origin"),
            ("ALTER TABLE generated_games ADD COLUMN generation_mode TEXT NOT NULL DEFAULT ''", "generation_mode"),
            ("ALTER TABLE generated_games ADD COLUMN context_json JSON NOT NULL DEFAULT '{}'", "context_json"),
        ):
            if column_name not in generated_columns:
                connection.exec_driver_sql(column_sql)
        reconciliation_run_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(reconciliation_runs)").fetchall()
        }
        if "payload" not in reconciliation_run_columns:
            connection.exec_driver_sql("ALTER TABLE reconciliation_runs ADD COLUMN payload JSON NOT NULL DEFAULT '{}'")
        reconciliation_game_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(reconciliation_games)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE reconciliation_games ADD COLUMN prize_status TEXT NOT NULL DEFAULT 'nao_premiado'", "prize_status"),
            ("ALTER TABLE reconciliation_games ADD COLUMN prize_tier TEXT NOT NULL DEFAULT ''", "prize_tier"),
            ("ALTER TABLE reconciliation_games ADD COLUMN context_json JSON NOT NULL DEFAULT '{}'", "context_json"),
        ):
            if column_name not in reconciliation_game_columns:
                connection.exec_driver_sql(column_sql)
        columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(imported_contests)").fetchall()
        }
        if "metadata_json" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE imported_contests ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'"
            )


def get_session(path: Path = DEFAULT_DATABASE_PATH) -> Session:
    create_database(path)
    session_factory = sessionmaker(bind=get_engine(path), expire_on_commit=False, future=True)
    return session_factory()
