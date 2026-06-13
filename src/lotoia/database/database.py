from __future__ import annotations

import logging
import os
from datetime import UTC, date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, create_engine, inspect
from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DEFAULT_DATABASE_PATH = Path("data/lotoia.db")
logger = logging.getLogger(__name__)


def _resolve_institutional_database_url(path: Path = DEFAULT_DATABASE_PATH) -> str:
    try:
        from .adapter import InstitutionalDatabaseAdapter
    except Exception:
        resolved = path if path.is_absolute() else path.resolve()
        return f"sqlite:///{resolved.as_posix()}"
    return InstitutionalDatabaseAdapter(path).database_url


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


class ScientificCalibrationDecision(Base):
    __tablename__ = "scientific_calibration_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    game_size: Mapped[int] = mapped_column(Integer, nullable=False)
    source_batch_id: Mapped[str] = mapped_column(String, nullable=False)
    source_generation_range: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    structural_status: Mapped[str] = mapped_column(String, default="", nullable=False)
    scientific_status: Mapped[str] = mapped_column(String, default="", nullable=False)
    classification: Mapped[str] = mapped_column(String, default="", nullable=False)
    main_reason: Mapped[str] = mapped_column(String, default="", nullable=False)
    recommended_action: Mapped[str] = mapped_column(String, default="", nullable=False)
    policy_before: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    policy_after: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    mode: Mapped[str] = mapped_column(String, default="OBSERVACAO", nullable=False)
    applied: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    approved_by: Mapped[str] = mapped_column(String, default="", nullable=False)
    notes: Mapped[str] = mapped_column(String, default="", nullable=False)

    __table_args__ = (
        Index("ix_scientific_calibration_decisions_created_at", "created_at"),
        Index("ix_scientific_calibration_decisions_strategy", "strategy"),
        Index("ix_scientific_calibration_decisions_source_batch_id", "source_batch_id"),
        Index("ix_scientific_calibration_decisions_mode", "mode"),
    )


class ScientificInstitutionalMemory(Base):
    __tablename__ = "scientific_institutional_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    memory_kind: Mapped[str] = mapped_column(String, default="calibration_decision", nullable=False)
    strategy_name: Mapped[str] = mapped_column(String, default="", nullable=False)
    game_size: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    batch_id: Mapped[str] = mapped_column(String, default="", nullable=False)
    generation_range: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    total_games: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_games: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_games: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    structural_status: Mapped[str] = mapped_column(String, default="", nullable=False)
    scientific_status: Mapped[str] = mapped_column(String, default="", nullable=False)
    scientific_classification: Mapped[str] = mapped_column(String, default="", nullable=False)
    main_reason: Mapped[str] = mapped_column(String, default="", nullable=False)
    recommended_action: Mapped[str] = mapped_column(String, default="", nullable=False)
    policy_applied: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    policy_before: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    policy_after: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    best_hit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_hits: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    count_11_plus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    count_12_plus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    count_13_plus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    count_14_plus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    count_15: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    validation_contests: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    cross_validation_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    frequency_alerts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    absence_alerts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    parity_alerts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    repetition_alerts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    sequence_alerts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    low_high_alerts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    range_alerts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    decision_mode: Mapped[str] = mapped_column(String, default="OBSERVACAO", nullable=False)
    approved_for_use: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str] = mapped_column(String, default="", nullable=False)
    official_history_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    official_history_first_contest: Mapped[int | None] = mapped_column(Integer, nullable=True)
    official_history_last_contest: Mapped[int | None] = mapped_column(Integer, nullable=True)
    official_history_window: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    source: Mapped[str] = mapped_column(String, default="scientific_calibration", nullable=False)

    __table_args__ = (
        Index("ix_scientific_institutional_memory_created_at", "created_at"),
        Index("ix_scientific_institutional_memory_strategy_name", "strategy_name"),
        Index("ix_scientific_institutional_memory_batch_id", "batch_id"),
        Index("ix_scientific_institutional_memory_memory_kind", "memory_kind"),
    )


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
    messenger_psid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    facebook_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    __table_args__ = (
        Index("ix_leads_created_at", "created_at"),
        Index("ix_leads_whatsapp", "whatsapp"),
        Index("ix_leads_source", "source"),
        Index("ix_leads_messenger_psid", "messenger_psid"),
    )


class MessengerConversationState(Base):
    __tablename__ = "messenger_conversation_state"

    psid: Mapped[str] = mapped_column(String(64), primary_key=True)
    state: Mapped[str] = mapped_column(String(40), default="initial", nullable=False)
    free_checks_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_interaction: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class LotoiaClient(Base):
    __tablename__ = "lotoia_clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, default="", nullable=False)
    plan: Mapped[str] = mapped_column(String, default="basico", nullable=False)
    formato_maximo: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    valor_pago: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    data_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    data_expiracao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String, default="ativo", nullable=False)
    messenger_psid: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    channel: Mapped[str] = mapped_column(String(20), default="whatsapp", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    __table_args__ = (
        Index("ix_lotoia_clients_phone", "phone"),
        Index("ix_lotoia_clients_status", "status"),
        Index("ix_lotoia_clients_data_expiracao", "data_expiracao"),
        Index("ix_lotoia_clients_messenger_psid", "messenger_psid"),
        Index("ix_lotoia_clients_channel", "channel"),
    )


class LotoiaClientDailyUsage(Base):
    __tablename__ = "lotoia_client_daily_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("lotoia_clients.id"), nullable=False)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False)
    geracoes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jogos_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    __table_args__ = (
        UniqueConstraint("client_id", "usage_date", name="uq_lotoia_client_daily_usage_client_date"),
        Index("ix_lotoia_client_daily_usage_client_id", "client_id"),
        Index("ix_lotoia_client_daily_usage_usage_date", "usage_date"),
    )


class LotoiaClientGeneration(Base):
    __tablename__ = "lotoia_client_generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("lotoia_clients.id"), nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    formato: Mapped[int] = mapped_column(Integer, nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    jogos: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    generation_event_id: Mapped[int | None] = mapped_column(ForeignKey("generation_events.id"), nullable=True)
    concurso_alvo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    channel: Mapped[str] = mapped_column(String(20), default="whatsapp", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    __table_args__ = (
        Index("ix_lotoia_client_generations_client_id", "client_id"),
        Index("ix_lotoia_client_generations_phone", "phone"),
        Index("ix_lotoia_client_generations_created_at", "created_at"),
        Index("ix_lotoia_client_generations_generation_event_id", "generation_event_id"),
        Index("ix_lotoia_client_generations_concurso_alvo", "concurso_alvo"),
        Index("idx_generations_concurso", "client_id", "concurso_alvo"),
    )


class LotoiaClientConferenceResult(Base):
    __tablename__ = "lotoia_client_conference_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("lotoia_clients.id"), nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    contest_number: Mapped[int] = mapped_column(Integer, nullable=False)
    game_index: Mapped[int] = mapped_column(Integer, nullable=False)
    numbers: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    hits: Mapped[int] = mapped_column(Integer, nullable=False)
    premio_status: Mapped[str] = mapped_column(String, default="nao_premiado", nullable=False)
    notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    __table_args__ = (
        UniqueConstraint("client_id", "contest_number", "game_index", name="uq_lotoia_client_conference_client_contest_game"),
        Index("ix_lotoia_client_conference_results_client_id", "client_id"),
        Index("ix_lotoia_client_conference_results_contest_number", "contest_number"),
        Index("ix_lotoia_client_conference_results_notified", "notified"),
        Index("ix_lotoia_client_conference_results_hits", "hits"),
    )


class InstitutionalUser(Base):
    __tablename__ = "institutional_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="user", nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    __table_args__ = (
        Index("ix_institutional_users_email", "email"),
        Index("ix_institutional_users_status", "status"),
        Index("ix_institutional_users_role", "role"),
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("institutional_users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    runtime_origin: Mapped[str] = mapped_column(String, default="unknown", nullable=False)
    ip_hash: Mapped[str] = mapped_column(String, default="", nullable=False)
    user_agent: Mapped[str] = mapped_column(String, default="", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    __table_args__ = (
        Index("ix_auth_sessions_session_id", "session_id"),
        Index("ix_auth_sessions_user_id", "user_id"),
        Index("ix_auth_sessions_status", "status"),
    )


class AuthEvent(Base):
    __tablename__ = "auth_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("institutional_users.id"), nullable=False)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    runtime_origin: Mapped[str] = mapped_column(String, default="unknown", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    __table_args__ = (
        Index("ix_auth_events_user_id", "user_id"),
        Index("ix_auth_events_session_id", "session_id"),
        Index("ix_auth_events_event_type", "event_type"),
    )


class AccessEvent(Base):
    __tablename__ = "access_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("institutional_users.id"), nullable=False)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    feature_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="user", nullable=False)
    allowed: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    runtime_origin: Mapped[str] = mapped_column(String, default="unknown", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    __table_args__ = (
        Index("ix_access_events_user_id", "user_id"),
        Index("ix_access_events_session_id", "session_id"),
        Index("ix_access_events_feature_name", "feature_name"),
        Index("ix_access_events_allowed", "allowed"),
    )


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feature_name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    role_scope: Mapped[str] = mapped_column(String, default="user", nullable=False)
    max_uses_per_session: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    __table_args__ = (
        Index("ix_feature_flags_feature_name", "feature_name"),
        Index("ix_feature_flags_enabled", "enabled"),
        Index("ix_feature_flags_role_scope", "role_scope"),
    )


class FeatureUsageEvent(Base):
    __tablename__ = "feature_usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("institutional_users.id"), nullable=False)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    feature_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="user", nullable=False)
    allowed: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    runtime_origin: Mapped[str] = mapped_column(String, default="unknown", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    __table_args__ = (
        Index("ix_feature_usage_events_user_id", "user_id"),
        Index("ix_feature_usage_events_session_id", "session_id"),
        Index("ix_feature_usage_events_feature_name", "feature_name"),
        Index("ix_feature_usage_events_allowed", "allowed"),
    )


class GenerationEvent(Base):
    __tablename__ = "generation_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True)
    first_name: Mapped[str] = mapped_column(String, default="", nullable=False)
    whatsapp: Mapped[str] = mapped_column(String, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    generated_games: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    ml_enabled: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    ranking_score: Mapped[float] = mapped_column(Float, nullable=False)
    execution_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    channel: Mapped[str] = mapped_column(String(20), default="whatsapp", nullable=False)
    __table_args__ = (
        Index("ix_generation_events_created_at", "created_at"),
        Index("ix_generation_events_lead_id", "lead_id"),
        Index("ix_generation_events_first_name", "first_name"),
        Index("ix_generation_events_whatsapp", "whatsapp"),
        Index("ix_generation_events_ml_enabled", "ml_enabled"),
    )


class MlUsageEvent(Base):
    __tablename__ = "ml_usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), nullable=False)
    generation_event_id: Mapped[int] = mapped_column(ForeignKey("generation_events.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String, default="public_api", nullable=False)
    strategy: Mapped[str] = mapped_column(String, default="", nullable=False)
    execution_time_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    __table_args__ = (
        Index("ix_ml_usage_events_created_at", "created_at"),
        Index("ix_ml_usage_events_lead_id", "lead_id"),
        Index("ix_ml_usage_events_generation_event_id", "generation_event_id"),
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


class ReportEvent(Base):
    __tablename__ = "report_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True)
    generation_event_id: Mapped[int | None] = mapped_column(ForeignKey("generation_events.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    report_type: Mapped[str] = mapped_column(String, default="user_report", nullable=False)
    generation_origin: Mapped[str] = mapped_column(String, default="", nullable=False)
    runtime_origin: Mapped[str] = mapped_column(String, default="", nullable=False)
    strategy_profile: Mapped[str] = mapped_column(String, default="", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    __table_args__ = (
        Index("ix_report_events_created_at", "created_at"),
        Index("ix_report_events_lead_id", "lead_id"),
        Index("ix_report_events_generation_event_id", "generation_event_id"),
    )


class ExpansionEvent(Base):
    __tablename__ = "expansion_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True)
    generation_event_id: Mapped[int | None] = mapped_column(ForeignKey("generation_events.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    origin: Mapped[str] = mapped_column(String, default="expanded", nullable=False)
    expansion_type: Mapped[str] = mapped_column(String, default="expanded", nullable=False)
    expansion_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    runtime_origin: Mapped[str] = mapped_column(String, default="", nullable=False)
    strategy_profile: Mapped[str] = mapped_column(String, default="", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    __table_args__ = (
        Index("ix_expansion_events_created_at", "created_at"),
        Index("ix_expansion_events_lead_id", "lead_id"),
        Index("ix_expansion_events_generation_event_id", "generation_event_id"),
        Index("ix_expansion_events_expansion_type", "expansion_type"),
    )


class InstitutionalValidatedExpansion(Base):
    __tablename__ = "institutional_validated_expansions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expansion_event_id: Mapped[int | None] = mapped_column(ForeignKey("expansion_events.id"), nullable=True)
    generation_event_id: Mapped[int | None] = mapped_column(ForeignKey("generation_events.id"), nullable=True)
    contest_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String, default="PENDING", nullable=False)
    profile_type: Mapped[str] = mapped_column(String, default="", nullable=False)
    scientific_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    diversity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    overlap_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recurrence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    proximity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    efficiency_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    premium_rank: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_validated_expansions_created_at", "created_at"),
        Index("ix_validated_expansions_status", "status"),
        Index("ix_validated_expansions_contest_id", "contest_id"),
        Index("ix_validated_expansions_generation_event_id", "generation_event_id"),
        Index("ix_validated_expansions_profile_type", "profile_type"),
    )


class ReconciliationEvent(Base):
    __tablename__ = "reconciliation_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True)
    generation_event_id: Mapped[int | None] = mapped_column(ForeignKey("generation_events.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    reconciliation_type: Mapped[str] = mapped_column(String, default="operational", nullable=False)
    hits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matched_numbers: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    runtime_origin: Mapped[str] = mapped_column(String, default="", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    __table_args__ = (
        Index("ix_reconciliation_events_created_at", "created_at"),
        Index("ix_reconciliation_events_lead_id", "lead_id"),
        Index("ix_reconciliation_events_generation_event_id", "generation_event_id"),
        Index("ix_reconciliation_events_reconciliation_type", "reconciliation_type"),
    )


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[str] = mapped_column(String, nullable=False)
    workflow_name: Mapped[str] = mapped_column(String, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String, default="", nullable=False)
    stage: Mapped[str] = mapped_column(String, default="", nullable=False)
    source: Mapped[str] = mapped_column(String, default="manual", nullable=False)
    status: Mapped[str] = mapped_column(String, default="running", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str] = mapped_column(String, default="", nullable=False)
    __table_args__ = (
        Index("ix_workflow_events_workflow_id", "workflow_id"),
        Index("ix_workflow_events_workflow_name", "workflow_name"),
        Index("ix_workflow_events_status", "status"),
        Index("ix_workflow_events_started_at", "started_at"),
    )


class ResetEvent(Base):
    __tablename__ = "reset_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reset_type: Mapped[str] = mapped_column(String, default="operational", nullable=False)
    triggered_by: Mapped[str] = mapped_column(String, default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    affected_tables: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String, default="completed", nullable=False)
    notes: Mapped[str] = mapped_column(String, default="", nullable=False)


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


class LotofacilOfficialHistory(Base):
    __tablename__ = "lotofacil_official_history"

    contest_number: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    draw_date: Mapped[str] = mapped_column(String, default="", nullable=False)
    numbers: Mapped[str] = mapped_column(String, default="", nullable=False)
    numbers_signature: Mapped[str] = mapped_column(String, default="", nullable=False)
    source: Mapped[str] = mapped_column(String, default="imported_contests", nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_valid: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    metadata_json: Mapped[str] = mapped_column(String, default="{}", nullable=False)

    __table_args__ = (
        Index("ix_lotofacil_official_history_created_at", "created_at"),
        Index("ix_lotofacil_official_history_imported_at", "imported_at"),
        Index("ix_lotofacil_official_history_source", "source"),
    )


class GeneratedGame(Base):
    __tablename__ = "generated_games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    generation_event_id: Mapped[int] = mapped_column(Integer, nullable=False)
    lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
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


class InstitutionalOutputSignature(Base):
    __tablename__ = "institutional_output_signatures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String, nullable=False)
    generation_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    game_signature: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_institutional_output_signatures_batch_id", "batch_id"),
        Index("ix_institutional_output_signatures_generation_event_id", "generation_event_id"),
        Index("ux_institutional_output_signatures_batch_signature", "batch_id", "game_signature", unique=True),
    )


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


class MlDiagnosticDecision(Base):
    __tablename__ = "ml_diagnostic_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_type: Mapped[str] = mapped_column(String, nullable=False)
    dezena: Mapped[int] = mapped_column(Integer, nullable=False)
    ml_proposal: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    adm_decision: Mapped[str] = mapped_column(String, nullable=False)
    adm_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    verdict_type: Mapped[str] = mapped_column(String, default="", nullable=False)
    status: Mapped[str] = mapped_column(String, default="", nullable=False)
    verdict_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    missing_evidence: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    adr_candidate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    adm_user: Mapped[str] = mapped_column(String, default="", nullable=False)
    reconciliation_run_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_ml_diagnostic_decisions_alert_type", "alert_type"),
        Index("ix_ml_diagnostic_decisions_reconciliation_run_id", "reconciliation_run_id"),
        Index("ix_ml_diagnostic_decisions_created_at", "created_at"),
        Index(
            "ix_ml_diagnostic_decisions_run_alert_dezena",
            "reconciliation_run_id",
            "alert_type",
            "dezena",
        ),
    )


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    workflow_name: Mapped[str] = mapped_column(String, nullable=False)
    trigger: Mapped[str] = mapped_column(String, default="manual", nullable=False)
    status: Mapped[str] = mapped_column(String, default="running", nullable=False)
    retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    telemetry_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str] = mapped_column(String, default="", nullable=False)


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[str] = mapped_column(String, nullable=False)
    step_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="running", nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str] = mapped_column(String, default="", nullable=False)


class RuntimeExecution(Base):
    __tablename__ = "runtime_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    flow_name: Mapped[str] = mapped_column(String, nullable=False)
    stage: Mapped[str] = mapped_column(String, default="", nullable=False)
    status: Mapped[str] = mapped_column(String, default="running", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class RuntimeSpan(Base):
    __tablename__ = "runtime_spans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String, nullable=False)
    trace_id: Mapped[str] = mapped_column(String, nullable=False)
    span_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    parent_span_id: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    stage: Mapped[str] = mapped_column(String, default="", nullable=False)
    status: Mapped[str] = mapped_column(String, default="running", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    attributes_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class RuntimeMetric(Base):
    __tablename__ = "runtime_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    metric_type: Mapped[str] = mapped_column(String, nullable=False)
    labels_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class RuntimeLineage(Base):
    __tablename__ = "runtime_lineage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class RuntimeSnapshot(Base):
    __tablename__ = "runtime_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String, nullable=False)
    snapshot_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    snapshot_type: Mapped[str] = mapped_column(String, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class InstitutionalMemorySnapshot(Base):
    __tablename__ = "institutional_memory_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    memory_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    execution_id: Mapped[str] = mapped_column(String, nullable=False)
    snapshot_type: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    lineage_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class InstitutionalMemoryState(Base):
    __tablename__ = "institutional_memory_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    memory_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    execution_id: Mapped[str] = mapped_column(String, nullable=False)
    state_type: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class InstitutionalMemoryLineage(Base):
    __tablename__ = "institutional_memory_lineage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String, nullable=False)
    memory_id: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class InstitutionalMemoryReplay(Base):
    __tablename__ = "institutional_memory_replay"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    replay_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    execution_id: Mapped[str] = mapped_column(String, nullable=False)
    replay_type: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    request_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


def database_url(path: Path = DEFAULT_DATABASE_PATH) -> str:
    return _resolve_institutional_database_url(path)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except Exception:
        return default


@lru_cache(maxsize=8)
def _build_engine(resolved_url: str):
    is_sqlite = resolved_url.startswith("sqlite:///")
    connect_args: dict[str, Any] = {}
    engine_kwargs: dict[str, Any] = {"future": True, "connect_args": connect_args}

    if not is_sqlite:
        connect_args["connect_timeout"] = _env_int("LOTOIA_DATABASE_CONNECT_TIMEOUT_SECONDS", 5)
        engine_kwargs.update(
            {
                "pool_pre_ping": True,
                "pool_recycle": _env_int("LOTOIA_DATABASE_POOL_RECYCLE_SECONDS", 120),
                "pool_size": _env_int("LOTOIA_DATABASE_POOL_SIZE", 1),
                "max_overflow": _env_int("LOTOIA_DATABASE_MAX_OVERFLOW", 0),
                "pool_timeout": _env_int("LOTOIA_DATABASE_POOL_TIMEOUT_SECONDS", 10),
                "pool_use_lifo": True,
            }
        )
    else:
        engine_kwargs.update({"pool_pre_ping": False, "pool_recycle": -1})

    engine = create_engine(resolved_url, **engine_kwargs)

    if is_sqlite:
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


@lru_cache(maxsize=8)
def _session_factory(resolved_url: str):
    return sessionmaker(bind=_build_engine(resolved_url), expire_on_commit=False, future=True)


def get_engine(path: Path = DEFAULT_DATABASE_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    resolved_url = database_url(path)
    return _build_engine(resolved_url)


def create_database(path: Path = DEFAULT_DATABASE_PATH) -> None:
    engine = get_engine(path)
    Base.metadata.create_all(engine)
    if engine.url.get_backend_name() != "sqlite":
        applied_migrations: list[str] = []
        with engine.begin() as connection:
            inspector = inspect(connection)
            lead_columns = {column["name"] for column in inspector.get_columns("leads")}
            for column_sql, column_name in (
                ("ALTER TABLE leads ADD COLUMN source TEXT NOT NULL DEFAULT 'public'", "source"),
                ("ALTER TABLE leads ADD COLUMN ip_hash TEXT NOT NULL DEFAULT ''", "ip_hash"),
                ("ALTER TABLE leads ADD COLUMN user_agent TEXT NOT NULL DEFAULT ''", "user_agent"),
            ):
                if column_name not in lead_columns:
                    connection.exec_driver_sql(column_sql)
                    applied_migrations.append(f"leads.{column_name}")
            generation_event_columns = {
                column["name"]
                for column in inspector.get_columns("generation_events")
            }
            for column_sql, column_name in (
                ("ALTER TABLE generation_events ADD COLUMN lead_id INTEGER", "lead_id"),
                ("ALTER TABLE generation_events ADD COLUMN first_name TEXT NOT NULL DEFAULT ''", "first_name"),
                ("ALTER TABLE generation_events ADD COLUMN whatsapp TEXT NOT NULL DEFAULT ''", "whatsapp"),
                ("ALTER TABLE generation_events ADD COLUMN generated_games JSON NOT NULL DEFAULT '[]'", "generated_games"),
                ("ALTER TABLE generation_events ADD COLUMN context_json JSON NOT NULL DEFAULT '{}'", "context_json"),
            ):
                if column_name not in generation_event_columns:
                    connection.exec_driver_sql(column_sql)
                    applied_migrations.append(f"generation_events.{column_name}")
            try:
                connection.exec_driver_sql("ALTER TABLE generated_games ALTER COLUMN lead_id DROP NOT NULL")
            except Exception:
                pass
            ml_diag_columns = {
                column["name"]
                for column in inspector.get_columns("ml_diagnostic_decisions")
            }
            for column_sql, column_name in (
                ("ALTER TABLE ml_diagnostic_decisions ADD COLUMN verdict_type TEXT NOT NULL DEFAULT ''", "verdict_type"),
                ("ALTER TABLE ml_diagnostic_decisions ADD COLUMN status TEXT NOT NULL DEFAULT ''", "status"),
                ("ALTER TABLE ml_diagnostic_decisions ADD COLUMN verdict_reason TEXT", "verdict_reason"),
                ("ALTER TABLE ml_diagnostic_decisions ADD COLUMN missing_evidence JSON NOT NULL DEFAULT '[]'", "missing_evidence"),
                ("ALTER TABLE ml_diagnostic_decisions ADD COLUMN adr_candidate BOOLEAN NOT NULL DEFAULT FALSE", "adr_candidate"),
            ):
                if column_name not in ml_diag_columns:
                    connection.exec_driver_sql(column_sql)
                    applied_migrations.append(f"ml_diagnostic_decisions.{column_name}")
            client_generation_columns = {
                column["name"]
                for column in inspector.get_columns("lotoia_client_generations")
            }
            if "concurso_alvo" not in client_generation_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE lotoia_client_generations ADD COLUMN concurso_alvo INTEGER"
                )
                applied_migrations.append("lotoia_client_generations.concurso_alvo")
            connection.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS idx_generations_concurso "
                "ON lotoia_client_generations(client_id, concurso_alvo)"
            )
            lotoia_client_columns = {
                column["name"] for column in inspector.get_columns("lotoia_clients")
            }
            for column_sql, column_name in (
                ("ALTER TABLE lotoia_clients ADD COLUMN messenger_psid VARCHAR(64) UNIQUE", "messenger_psid"),
                ("ALTER TABLE lotoia_clients ADD COLUMN channel VARCHAR(20) NOT NULL DEFAULT 'whatsapp'", "channel"),
            ):
                if column_name not in lotoia_client_columns:
                    connection.exec_driver_sql(column_sql)
                    applied_migrations.append(f"lotoia_clients.{column_name}")
            if "channel" not in client_generation_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE lotoia_client_generations ADD COLUMN channel VARCHAR(20) NOT NULL DEFAULT 'whatsapp'"
                )
                applied_migrations.append("lotoia_client_generations.channel")
            if "channel" not in generation_event_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE generation_events ADD COLUMN channel VARCHAR(20) NOT NULL DEFAULT 'whatsapp'"
                )
                applied_migrations.append("generation_events.channel")
            if "messenger_psid" not in lead_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE leads ADD COLUMN messenger_psid VARCHAR(64)"
                )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS idx_leads_messenger_psid ON leads(messenger_psid)"
                )
                applied_migrations.append("leads.messenger_psid")
            if "facebook_name" not in lead_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE leads ADD COLUMN facebook_name VARCHAR(120)"
                )
                applied_migrations.append("leads.facebook_name")
            connection.exec_driver_sql(
                """
                CREATE TABLE IF NOT EXISTS messenger_conversation_state (
                    psid VARCHAR(64) PRIMARY KEY,
                    state VARCHAR(40) NOT NULL DEFAULT 'initial',
                    free_checks_used INTEGER NOT NULL DEFAULT 0,
                    last_interaction TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            applied_migrations.append("messenger_conversation_state")
            connection.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS idx_clients_messenger_psid ON lotoia_clients(messenger_psid)"
            )
        if applied_migrations:
            logger.info(
                "Institutional schema migration applied on %s: %s",
                engine.url.get_backend_name(),
                ", ".join(applied_migrations),
            )
    if engine.url.get_backend_name() != "sqlite":
        return
    applied_migrations: list[str] = []
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
            CREATE TABLE IF NOT EXISTS institutional_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_login_at TIMESTAMP,
                metadata_json JSON NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS auth_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'active',
                runtime_origin TEXT NOT NULL DEFAULT 'unknown',
                ip_hash TEXT NOT NULL DEFAULT '',
                user_agent TEXT NOT NULL DEFAULT '',
                payload JSON NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS auth_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                runtime_origin TEXT NOT NULL DEFAULT 'unknown',
                payload JSON NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS access_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                allowed INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                runtime_origin TEXT NOT NULL DEFAULT 'unknown',
                payload JSON NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS access_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                allowed INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                runtime_origin TEXT NOT NULL DEFAULT 'unknown',
                payload JSON NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS feature_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_name TEXT NOT NULL UNIQUE,
                enabled INTEGER NOT NULL DEFAULT 0,
                role_scope TEXT NOT NULL DEFAULT 'user',
                max_uses_per_session INTEGER,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                payload JSON NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS feature_usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                allowed INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                runtime_origin TEXT NOT NULL DEFAULT 'unknown',
                payload JSON NOT NULL DEFAULT '{}'
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
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS reconciliation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                generation_event_id INTEGER,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reconciliation_type TEXT NOT NULL DEFAULT 'operational',
                hits INTEGER NOT NULL DEFAULT 0,
                matched_numbers JSON NOT NULL DEFAULT '[]',
                runtime_origin TEXT NOT NULL DEFAULT '',
                payload JSON NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS workflow_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL UNIQUE,
                workflow_name TEXT NOT NULL,
                trigger TEXT NOT NULL DEFAULT 'manual',
                status TEXT NOT NULL DEFAULT 'running',
                retries INTEGER NOT NULL DEFAULT 0,
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                duration_ms REAL,
                context_json JSON NOT NULL DEFAULT '{}',
                telemetry_json JSON NOT NULL DEFAULT '{}',
                error_message TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS workflow_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                workflow_name TEXT NOT NULL,
                correlation_id TEXT NOT NULL DEFAULT '',
                stage TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'manual',
                status TEXT NOT NULL DEFAULT 'running',
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                duration_ms REAL,
                payload JSON NOT NULL DEFAULT '{}',
                error_message TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS reset_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reset_type TEXT NOT NULL DEFAULT 'operational',
                triggered_by TEXT NOT NULL DEFAULT 'system',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                affected_tables JSON NOT NULL DEFAULT '[]',
                payload JSON NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'completed',
                notes TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS workflow_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'running',
                attempt INTEGER NOT NULL DEFAULT 1,
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                duration_ms REAL,
                payload_json JSON NOT NULL DEFAULT '{}',
                error_message TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS runtime_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL UNIQUE,
                flow_name TEXT NOT NULL,
                stage TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'running',
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                duration_ms REAL,
                context_json JSON NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS runtime_spans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                span_id TEXT NOT NULL UNIQUE,
                parent_span_id TEXT,
                name TEXT NOT NULL,
                stage TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'running',
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                duration_ms REAL,
                attributes_json JSON NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS runtime_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                name TEXT NOT NULL,
                value REAL NOT NULL,
                metric_type TEXT NOT NULL,
                labels_json JSON NOT NULL DEFAULT '{}',
                metadata_json JSON NOT NULL DEFAULT '{}',
                observed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS runtime_lineage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json JSON NOT NULL DEFAULT '{}',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS runtime_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                snapshot_id TEXT NOT NULL UNIQUE,
                snapshot_type TEXT NOT NULL,
                payload_json JSON NOT NULL DEFAULT '{}',
                metadata_json JSON NOT NULL DEFAULT '{}',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS institutional_memory_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id TEXT NOT NULL UNIQUE,
                execution_id TEXT NOT NULL,
                snapshot_type TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                state_json JSON NOT NULL DEFAULT '{}',
                metadata_json JSON NOT NULL DEFAULT '{}',
                lineage_json JSON NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS institutional_memory_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id TEXT NOT NULL UNIQUE,
                execution_id TEXT NOT NULL,
                state_type TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                state_json JSON NOT NULL DEFAULT '{}',
                metadata_json JSON NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS institutional_memory_lineage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                memory_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                payload_json JSON NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS institutional_memory_replay (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                replay_id TEXT NOT NULL UNIQUE,
                execution_id TEXT NOT NULL,
                replay_type TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                request_json JSON NOT NULL DEFAULT '{}',
                result_json JSON NOT NULL DEFAULT '{}'
            )
            """
        )
        generated_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(generated_games)").fetchall()
        }
        generation_event_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(generation_events)").fetchall()
        }
        if "lead_id" not in generation_event_columns:
            connection.exec_driver_sql("ALTER TABLE generation_events ADD COLUMN lead_id INTEGER")
            applied_migrations.append("generation_events.lead_id")
        if "first_name" not in generation_event_columns:
            connection.exec_driver_sql("ALTER TABLE generation_events ADD COLUMN first_name TEXT NOT NULL DEFAULT ''")
            applied_migrations.append("generation_events.first_name")
        if "whatsapp" not in generation_event_columns:
            connection.exec_driver_sql("ALTER TABLE generation_events ADD COLUMN whatsapp TEXT NOT NULL DEFAULT ''")
            applied_migrations.append("generation_events.whatsapp")
        if "generated_games" not in generation_event_columns:
            connection.exec_driver_sql("ALTER TABLE generation_events ADD COLUMN generated_games JSON NOT NULL DEFAULT '[]'")
            applied_migrations.append("generation_events.generated_games")
        if "context_json" not in generation_event_columns:
            connection.exec_driver_sql("ALTER TABLE generation_events ADD COLUMN context_json JSON NOT NULL DEFAULT '{}'")
            applied_migrations.append("generation_events.context_json")
        for column_sql, column_name in (
            ("ALTER TABLE generated_games ADD COLUMN target_contest INTEGER", "target_contest"),
            ("ALTER TABLE generated_games ADD COLUMN origin TEXT NOT NULL DEFAULT 'dashboard'", "origin"),
            ("ALTER TABLE generated_games ADD COLUMN generation_mode TEXT NOT NULL DEFAULT ''", "generation_mode"),
            ("ALTER TABLE generated_games ADD COLUMN context_json JSON NOT NULL DEFAULT '{}'", "context_json"),
        ):
            if column_name not in generated_columns:
                connection.exec_driver_sql(column_sql)
                applied_migrations.append(f"generated_games.{column_name}")
        reconciliation_run_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(reconciliation_runs)").fetchall()
        }
        if "payload" not in reconciliation_run_columns:
            connection.exec_driver_sql("ALTER TABLE reconciliation_runs ADD COLUMN payload JSON NOT NULL DEFAULT '{}'")
            applied_migrations.append("reconciliation_runs.payload")
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
        reconciliation_event_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(reconciliation_events)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE reconciliation_events ADD COLUMN lead_id INTEGER", "lead_id"),
            ("ALTER TABLE reconciliation_events ADD COLUMN generation_event_id INTEGER", "generation_event_id"),
            ("ALTER TABLE reconciliation_events ADD COLUMN reconciliation_type TEXT NOT NULL DEFAULT 'operational'", "reconciliation_type"),
            ("ALTER TABLE reconciliation_events ADD COLUMN hits INTEGER NOT NULL DEFAULT 0", "hits"),
            ("ALTER TABLE reconciliation_events ADD COLUMN matched_numbers JSON NOT NULL DEFAULT '[]'", "matched_numbers"),
            ("ALTER TABLE reconciliation_events ADD COLUMN runtime_origin TEXT NOT NULL DEFAULT ''", "runtime_origin"),
            ("ALTER TABLE reconciliation_events ADD COLUMN payload JSON NOT NULL DEFAULT '{}'", "payload"),
        ):
            if column_name not in reconciliation_event_columns:
                connection.exec_driver_sql(column_sql)
        expansion_event_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(expansion_events)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE expansion_events ADD COLUMN lead_id INTEGER", "lead_id"),
            ("ALTER TABLE expansion_events ADD COLUMN generation_event_id INTEGER", "generation_event_id"),
            ("ALTER TABLE expansion_events ADD COLUMN origin TEXT NOT NULL DEFAULT 'expanded'", "origin"),
            ("ALTER TABLE expansion_events ADD COLUMN expansion_type TEXT NOT NULL DEFAULT 'expanded'", "expansion_type"),
            ("ALTER TABLE expansion_events ADD COLUMN expansion_size INTEGER NOT NULL DEFAULT 0", "expansion_size"),
            ("ALTER TABLE expansion_events ADD COLUMN runtime_origin TEXT NOT NULL DEFAULT ''", "runtime_origin"),
            ("ALTER TABLE expansion_events ADD COLUMN strategy_profile TEXT NOT NULL DEFAULT ''", "strategy_profile"),
            ("ALTER TABLE expansion_events ADD COLUMN payload JSON NOT NULL DEFAULT '{}'", "payload"),
        ):
            if column_name not in expansion_event_columns:
                connection.exec_driver_sql(column_sql)
        workflow_run_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(workflow_runs)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE workflow_runs ADD COLUMN trigger TEXT NOT NULL DEFAULT 'manual'", "trigger"),
            ("ALTER TABLE workflow_runs ADD COLUMN status TEXT NOT NULL DEFAULT 'running'", "status"),
            ("ALTER TABLE workflow_runs ADD COLUMN retries INTEGER NOT NULL DEFAULT 0", "retries"),
            ("ALTER TABLE workflow_runs ADD COLUMN finished_at TIMESTAMP", "finished_at"),
            ("ALTER TABLE workflow_runs ADD COLUMN duration_ms REAL", "duration_ms"),
            ("ALTER TABLE workflow_runs ADD COLUMN context_json JSON NOT NULL DEFAULT '{}'", "context_json"),
            ("ALTER TABLE workflow_runs ADD COLUMN telemetry_json JSON NOT NULL DEFAULT '{}'", "telemetry_json"),
            ("ALTER TABLE workflow_runs ADD COLUMN error_message TEXT NOT NULL DEFAULT ''", "error_message"),
        ):
            if column_name not in workflow_run_columns:
                connection.exec_driver_sql(column_sql)
        workflow_event_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(workflow_events)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE workflow_events ADD COLUMN workflow_id TEXT NOT NULL DEFAULT ''", "workflow_id"),
            ("ALTER TABLE workflow_events ADD COLUMN workflow_name TEXT NOT NULL DEFAULT ''", "workflow_name"),
            ("ALTER TABLE workflow_events ADD COLUMN correlation_id TEXT NOT NULL DEFAULT ''", "correlation_id"),
            ("ALTER TABLE workflow_events ADD COLUMN stage TEXT NOT NULL DEFAULT ''", "stage"),
            ("ALTER TABLE workflow_events ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'", "source"),
            ("ALTER TABLE workflow_events ADD COLUMN status TEXT NOT NULL DEFAULT 'running'", "status"),
            ("ALTER TABLE workflow_events ADD COLUMN finished_at TIMESTAMP", "finished_at"),
            ("ALTER TABLE workflow_events ADD COLUMN duration_ms REAL", "duration_ms"),
            ("ALTER TABLE workflow_events ADD COLUMN payload JSON NOT NULL DEFAULT '{}'", "payload"),
            ("ALTER TABLE workflow_events ADD COLUMN error_message TEXT NOT NULL DEFAULT ''", "error_message"),
        ):
            if column_name not in workflow_event_columns:
                connection.exec_driver_sql(column_sql)
        reset_event_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(reset_events)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE reset_events ADD COLUMN reset_type TEXT NOT NULL DEFAULT 'operational'", "reset_type"),
            ("ALTER TABLE reset_events ADD COLUMN triggered_by TEXT NOT NULL DEFAULT 'system'", "triggered_by"),
            ("ALTER TABLE reset_events ADD COLUMN affected_tables JSON NOT NULL DEFAULT '[]'", "affected_tables"),
            ("ALTER TABLE reset_events ADD COLUMN payload JSON NOT NULL DEFAULT '{}'", "payload"),
            ("ALTER TABLE reset_events ADD COLUMN status TEXT NOT NULL DEFAULT 'completed'", "status"),
            ("ALTER TABLE reset_events ADD COLUMN notes TEXT NOT NULL DEFAULT ''", "notes"),
        ):
            if column_name not in reset_event_columns:
                connection.exec_driver_sql(column_sql)
        workflow_step_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(workflow_steps)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE workflow_steps ADD COLUMN status TEXT NOT NULL DEFAULT 'running'", "status"),
            ("ALTER TABLE workflow_steps ADD COLUMN attempt INTEGER NOT NULL DEFAULT 1", "attempt"),
            ("ALTER TABLE workflow_steps ADD COLUMN finished_at TIMESTAMP", "finished_at"),
            ("ALTER TABLE workflow_steps ADD COLUMN duration_ms REAL", "duration_ms"),
            ("ALTER TABLE workflow_steps ADD COLUMN payload_json JSON NOT NULL DEFAULT '{}'", "payload_json"),
            ("ALTER TABLE workflow_steps ADD COLUMN error_message TEXT NOT NULL DEFAULT ''", "error_message"),
        ):
            if column_name not in workflow_step_columns:
                connection.exec_driver_sql(column_sql)
        runtime_execution_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(runtime_executions)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE runtime_executions ADD COLUMN stage TEXT NOT NULL DEFAULT ''", "stage"),
            ("ALTER TABLE runtime_executions ADD COLUMN status TEXT NOT NULL DEFAULT 'running'", "status"),
            ("ALTER TABLE runtime_executions ADD COLUMN finished_at TIMESTAMP", "finished_at"),
            ("ALTER TABLE runtime_executions ADD COLUMN duration_ms REAL", "duration_ms"),
            ("ALTER TABLE runtime_executions ADD COLUMN context_json JSON NOT NULL DEFAULT '{}'", "context_json"),
        ):
            if column_name not in runtime_execution_columns:
                connection.exec_driver_sql(column_sql)
        runtime_span_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(runtime_spans)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE runtime_spans ADD COLUMN stage TEXT NOT NULL DEFAULT ''", "stage"),
            ("ALTER TABLE runtime_spans ADD COLUMN status TEXT NOT NULL DEFAULT 'running'", "status"),
            ("ALTER TABLE runtime_spans ADD COLUMN finished_at TIMESTAMP", "finished_at"),
            ("ALTER TABLE runtime_spans ADD COLUMN duration_ms REAL", "duration_ms"),
            ("ALTER TABLE runtime_spans ADD COLUMN attributes_json JSON NOT NULL DEFAULT '{}'", "attributes_json"),
        ):
            if column_name not in runtime_span_columns:
                connection.exec_driver_sql(column_sql)
        runtime_metric_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(runtime_metrics)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE runtime_metrics ADD COLUMN labels_json JSON NOT NULL DEFAULT '{}'", "labels_json"),
            ("ALTER TABLE runtime_metrics ADD COLUMN metadata_json JSON NOT NULL DEFAULT '{}'", "metadata_json"),
            ("ALTER TABLE runtime_metrics ADD COLUMN observed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP", "observed_at"),
        ):
            if column_name not in runtime_metric_columns:
                connection.exec_driver_sql(column_sql)
        runtime_lineage_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(runtime_lineage)").fetchall()
        }
        if "payload_json" not in runtime_lineage_columns:
            connection.exec_driver_sql("ALTER TABLE runtime_lineage ADD COLUMN payload_json JSON NOT NULL DEFAULT '{}'")
        runtime_snapshot_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(runtime_snapshots)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE runtime_snapshots ADD COLUMN payload_json JSON NOT NULL DEFAULT '{}'", "payload_json"),
            ("ALTER TABLE runtime_snapshots ADD COLUMN metadata_json JSON NOT NULL DEFAULT '{}'", "metadata_json"),
            ("ALTER TABLE runtime_snapshots ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP", "created_at"),
        ):
            if column_name not in runtime_snapshot_columns:
                connection.exec_driver_sql(column_sql)
        institutional_memory_snapshot_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(institutional_memory_snapshots)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE institutional_memory_snapshots ADD COLUMN state_json JSON NOT NULL DEFAULT '{}'", "state_json"),
            ("ALTER TABLE institutional_memory_snapshots ADD COLUMN metadata_json JSON NOT NULL DEFAULT '{}'", "metadata_json"),
            ("ALTER TABLE institutional_memory_snapshots ADD COLUMN lineage_json JSON NOT NULL DEFAULT '{}'", "lineage_json"),
            ("ALTER TABLE institutional_memory_snapshots ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP", "created_at"),
        ):
            if column_name not in institutional_memory_snapshot_columns:
                connection.exec_driver_sql(column_sql)
        institutional_memory_state_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(institutional_memory_states)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE institutional_memory_states ADD COLUMN state_json JSON NOT NULL DEFAULT '{}'", "state_json"),
            ("ALTER TABLE institutional_memory_states ADD COLUMN metadata_json JSON NOT NULL DEFAULT '{}'", "metadata_json"),
            ("ALTER TABLE institutional_memory_states ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP", "created_at"),
        ):
            if column_name not in institutional_memory_state_columns:
                connection.exec_driver_sql(column_sql)
        institutional_memory_lineage_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(institutional_memory_lineage)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE institutional_memory_lineage ADD COLUMN payload_json JSON NOT NULL DEFAULT '{}'", "payload_json"),
            ("ALTER TABLE institutional_memory_lineage ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP", "created_at"),
        ):
            if column_name not in institutional_memory_lineage_columns:
                connection.exec_driver_sql(column_sql)
        institutional_memory_replay_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(institutional_memory_replay)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE institutional_memory_replay ADD COLUMN request_json JSON NOT NULL DEFAULT '{}'", "request_json"),
            ("ALTER TABLE institutional_memory_replay ADD COLUMN result_json JSON NOT NULL DEFAULT '{}'", "result_json"),
            ("ALTER TABLE institutional_memory_replay ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP", "created_at"),
        ):
            if column_name not in institutional_memory_replay_columns:
                connection.exec_driver_sql(column_sql)
        columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(imported_contests)").fetchall()
        }
        if "metadata_json" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE imported_contests ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'"
            )
            applied_migrations.append("imported_contests.metadata_json")
        lead_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(leads)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE leads ADD COLUMN source TEXT NOT NULL DEFAULT 'public'", "source"),
            ("ALTER TABLE leads ADD COLUMN ip_hash TEXT NOT NULL DEFAULT ''", "ip_hash"),
            ("ALTER TABLE leads ADD COLUMN user_agent TEXT NOT NULL DEFAULT ''", "user_agent"),
        ):
            if column_name not in lead_columns:
                connection.exec_driver_sql(column_sql)
                applied_migrations.append(f"leads.{column_name}")
        ml_diag_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(ml_diagnostic_decisions)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE ml_diagnostic_decisions ADD COLUMN verdict_type TEXT NOT NULL DEFAULT ''", "verdict_type"),
            ("ALTER TABLE ml_diagnostic_decisions ADD COLUMN status TEXT NOT NULL DEFAULT ''", "status"),
            ("ALTER TABLE ml_diagnostic_decisions ADD COLUMN verdict_reason TEXT", "verdict_reason"),
            ("ALTER TABLE ml_diagnostic_decisions ADD COLUMN missing_evidence JSON NOT NULL DEFAULT '[]'", "missing_evidence"),
            ("ALTER TABLE ml_diagnostic_decisions ADD COLUMN adr_candidate INTEGER NOT NULL DEFAULT 0", "adr_candidate"),
        ):
            if column_name not in ml_diag_columns:
                connection.exec_driver_sql(column_sql)
                applied_migrations.append(f"ml_diagnostic_decisions.{column_name}")
        client_generation_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(lotoia_client_generations)").fetchall()
        }
        if "concurso_alvo" not in client_generation_columns:
            connection.exec_driver_sql(
                "ALTER TABLE lotoia_client_generations ADD COLUMN concurso_alvo INTEGER"
            )
            applied_migrations.append("lotoia_client_generations.concurso_alvo")
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_generations_concurso "
            "ON lotoia_client_generations(client_id, concurso_alvo)"
        )
        if "channel" not in client_generation_columns:
            connection.exec_driver_sql(
                "ALTER TABLE lotoia_client_generations ADD COLUMN channel TEXT NOT NULL DEFAULT 'whatsapp'"
            )
            applied_migrations.append("lotoia_client_generations.channel")
        lotoia_client_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(lotoia_clients)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE lotoia_clients ADD COLUMN messenger_psid TEXT", "messenger_psid"),
            ("ALTER TABLE lotoia_clients ADD COLUMN channel TEXT NOT NULL DEFAULT 'whatsapp'", "channel"),
        ):
            if column_name not in lotoia_client_columns:
                connection.exec_driver_sql(column_sql)
                applied_migrations.append(f"lotoia_clients.{column_name}")
        generation_event_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(generation_events)").fetchall()
        }
        if "channel" not in generation_event_columns:
            connection.exec_driver_sql(
                "ALTER TABLE generation_events ADD COLUMN channel TEXT NOT NULL DEFAULT 'whatsapp'"
            )
            applied_migrations.append("generation_events.channel")
        if "messenger_psid" not in lead_columns:
            connection.exec_driver_sql("ALTER TABLE leads ADD COLUMN messenger_psid TEXT")
            applied_migrations.append("leads.messenger_psid")
        if "facebook_name" not in lead_columns:
            connection.exec_driver_sql("ALTER TABLE leads ADD COLUMN facebook_name TEXT")
            applied_migrations.append("leads.facebook_name")
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS messenger_conversation_state (
                psid TEXT PRIMARY KEY,
                state TEXT NOT NULL DEFAULT 'initial',
                free_checks_used INTEGER NOT NULL DEFAULT 0,
                last_interaction TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        applied_migrations.append("messenger_conversation_state")
    if applied_migrations:
        logger.info(
            "Institutional schema migration applied on %s: %s",
            engine.url.get_backend_name(),
            ", ".join(applied_migrations),
        )


def bootstrap_institutional_database(path: Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """Create or migrate the institutional schema for the active backend."""
    try:
        from .adapter import resolve_institutional_adapter
    except Exception:
        resolved_url = database_url(path)
        backend = "postgresql" if resolved_url.startswith(("postgresql://", "postgresql+psycopg://", "postgres://")) else "sqlite"
    else:
        adapter = resolve_institutional_adapter(path)
        resolved_url = adapter.database_url
        backend = adapter.backend
    create_database(path)
    return {"database_url": resolved_url, "backend": backend}


def get_session(path: Path = DEFAULT_DATABASE_PATH) -> Session:
    resolved_url = database_url(path)
    engine = get_engine(path)
    if engine.url.get_backend_name() == "sqlite" or os.getenv("LOTOIA_BOOTSTRAP_SCHEMA_ON_SESSION", "").strip().lower() in {"1", "true", "yes", "on"}:
        create_database(path)
    return _session_factory(resolved_url)()
