from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.database.database import (
    AccessEvent,
    AuthEvent,
    AuthSession,
    FeatureFlag,
    FeatureUsageEvent,
    InstitutionalUser,
    CheckEvent,
    ExpansionEvent,
    GenerationEvent,
    Lead,
    MlUsageEvent,
    ReportEvent,
    ReconciliationEvent,
    ResetEvent,
    get_session,
)
from lotoia.public.persistence.repositories import (
    CheckEventRepository,
    ExpansionEventRepository,
    GenerationEventRepository,
    LeadRepository,
    MlUsageEventRepository,
    ReportEventRepository,
    ReconciliationEventRepository,
)

_INSTITUTIONAL_DATABASE_ENV_VARS = ("DATABASE_URL", "LOTOIA_DATABASE_URL", "STREAMLIT_DATABASE_URL")
_INSTITUTIONAL_DATABASE_POOLER_ENV_VARS = (
    "LOTOIA_DATABASE_POOLER_URL",
    "STREAMLIT_DATABASE_POOLER_URL",
)
_DEFAULT_SUPABASE_POOLER_HOST = "aws-1-us-west-1.pooler.supabase.com"


def _read_database_url_from_env() -> tuple[str, str]:
    for env_name in _INSTITUTIONAL_DATABASE_ENV_VARS:
        env_value = os.getenv(env_name, "").strip()
        if env_value:
            return env_value, env_name
    return "", ""


def _read_pooler_database_url_from_env() -> tuple[str, str]:
    for env_name in _INSTITUTIONAL_DATABASE_POOLER_ENV_VARS:
        env_value = os.getenv(env_name, "").strip()
        if env_value:
            return env_value, env_name
    return "", ""


def _extract_supabase_project_ref(database_url: str) -> str:
    parsed = urlparse(database_url)
    host = (parsed.hostname or "").lower()
    if host.endswith(".supabase.co") and host != "supabase.co":
        return host.removesuffix(".supabase.co")
    username = parsed.username or ""
    if "." in username:
        return username.split(".", 1)[1].strip()
    return ""


def _build_supabase_pooler_username(database_url: str) -> str:
    project_ref = os.getenv("LOTOIA_SUPABASE_PROJECT_REF", "").strip()
    if not project_ref:
        project_ref = _extract_supabase_project_ref(database_url)
    if project_ref:
        return f"postgres.{project_ref}"
    return "postgres"


def _rewrite_supabase_url_to_pooler(database_url: str) -> str:
    parsed = urlparse(database_url)
    host = (parsed.hostname or "").lower()
    if "supabase.co" not in host and "pooler" not in host:
        return database_url
    pooler_host = os.getenv("LOTOIA_SUPABASE_POOLER_HOST", _DEFAULT_SUPABASE_POOLER_HOST).strip() or _DEFAULT_SUPABASE_POOLER_HOST
    port = parsed.port or 5432
    username = _build_supabase_pooler_username(database_url)
    password = parsed.password or ""
    netloc = username
    if password:
        netloc += f":{password}"
    netloc += f"@{pooler_host}:{port}"
    query = parse_qsl(parsed.query, keep_blank_values=True)
    query_keys = {key for key, _ in query}
    if "sslmode" not in query_keys:
        query.append(("sslmode", "require"))
    return urlunparse((parsed.scheme, netloc, parsed.path or "", parsed.params, urlencode(query), parsed.fragment))


@dataclass(frozen=True)
class InstitutionalDatabaseAdapter:
    """Resolve the institutional database backend and connection target."""

    path: Path = DEFAULT_DATABASE_PATH

    @property
    def database_url(self) -> str:
        pooler_url, _ = _read_pooler_database_url_from_env()
        if pooler_url:
            return pooler_url
        env_url, _ = _read_database_url_from_env()
        if env_url:
            return _rewrite_supabase_url_to_pooler(env_url)
        resolved = self.path if self.path.is_absolute() else self.path.resolve()
        return f"sqlite:///{resolved.as_posix()}"

    @property
    def backend(self) -> str:
        url = self.database_url.lower()
        if url.startswith("sqlite:///"):
            return "sqlite"
        if url.startswith("postgresql") or url.startswith("postgres://"):
            return "postgresql"
        return "unknown"

    @property
    def sqlite_path(self) -> Path:
        return self.path if self.path.is_absolute() else self.path.resolve()

    @property
    def is_shared_cloud_ready(self) -> bool:
        return self.backend == "postgresql"

    @property
    def database_source(self) -> str:
        pooler_url, pooler_env_name = _read_pooler_database_url_from_env()
        if pooler_url:
            return pooler_env_name
        _, env_name = _read_database_url_from_env()
        if env_name:
            return env_name
        return "sqlite_fallback"

    @property
    def database_host(self) -> str:
        parsed = urlparse(self.database_url)
        return parsed.hostname or ""

    @property
    def uses_pooler(self) -> bool:
        host = self.database_host.lower()
        return "pooler.supabase.com" in host or "pooler" in host

    def save_lead(self, **kwargs: Any) -> dict[str, Any]:
        repository = LeadRepository(self.sqlite_path)
        return repository.insert(**kwargs)

    def save_institutional_user(self, **kwargs: Any) -> dict[str, Any]:
        with get_session(self.sqlite_path) as session:
            user = InstitutionalUser(
                email=str(kwargs["email"]).strip().lower(),
                password_hash=str(kwargs["password_hash"]),
                role=str(kwargs.get("role", "user")),
                status=str(kwargs.get("status", "active")),
                metadata_json=dict(kwargs.get("metadata_json") or {}),
            )
            session.add(user)
            session.commit()
            return {column.name: getattr(user, column.name) for column in user.__table__.columns}

    def save_login_event(self, **kwargs: Any) -> dict[str, Any]:
        with get_session(self.sqlite_path) as session:
            event = AuthEvent(
                user_id=int(kwargs["user_id"]),
                session_id=str(kwargs["session_id"]),
                event_type="login",
                runtime_origin=str(kwargs.get("runtime_origin", "unknown")),
                payload=dict(kwargs.get("payload") or {}),
            )
            auth_session = AuthSession(
                session_id=str(kwargs["session_id"]),
                user_id=int(kwargs["user_id"]),
                status="active",
                runtime_origin=str(kwargs.get("runtime_origin", "unknown")),
                ip_hash=str(kwargs.get("ip_hash", "")),
                user_agent=str(kwargs.get("user_agent", "")),
                payload=dict(kwargs.get("payload") or {}),
            )
            user = session.get(InstitutionalUser, int(kwargs["user_id"]))
            if user is not None:
                user.last_login_at = event.created_at
            session.add_all([event, auth_session])
            session.commit()
            return {column.name: getattr(event, column.name) for column in event.__table__.columns}

    def save_logout_event(self, **kwargs: Any) -> dict[str, Any]:
        with get_session(self.sqlite_path) as session:
            event = AuthEvent(
                user_id=int(kwargs["user_id"]),
                session_id=str(kwargs["session_id"]),
                event_type="logout",
                runtime_origin=str(kwargs.get("runtime_origin", "unknown")),
                payload=dict(kwargs.get("payload") or {}),
            )
            auth_session = (
                session.query(AuthSession)
                .filter(AuthSession.session_id == str(kwargs["session_id"]))
                .order_by(AuthSession.created_at.desc(), AuthSession.id.desc())
                .first()
            )
            if auth_session is not None:
                auth_session.status = "ended"
                auth_session.ended_at = event.created_at
            session.add(event)
            session.commit()
            return {column.name: getattr(event, column.name) for column in event.__table__.columns}

    def save_role_change_event(self, **kwargs: Any) -> dict[str, Any]:
        with get_session(self.sqlite_path) as session:
            user = session.get(InstitutionalUser, int(kwargs["user_id"]))
            if user is None:
                raise ValueError("institutional user not found")
            previous_role = str(user.role)
            new_role = str(kwargs["role"])
            user.role = new_role
            event = AuthEvent(
                user_id=int(kwargs["user_id"]),
                session_id=str(kwargs.get("session_id", "")),
                event_type="role_change",
                runtime_origin=str(kwargs.get("runtime_origin", "unknown")),
                payload={
                    "previous_role": previous_role,
                    "new_role": new_role,
                    "reason": str(kwargs.get("reason", "")),
                    "payload": dict(kwargs.get("payload") or {}),
                },
            )
            session.add(event)
            session.commit()
            return {column.name: getattr(event, column.name) for column in event.__table__.columns}

    def save_access_event(self, **kwargs: Any) -> dict[str, Any]:
        with get_session(self.sqlite_path) as session:
            event = AccessEvent(
                user_id=int(kwargs["user_id"]),
                session_id=str(kwargs["session_id"]),
                feature_name=str(kwargs["feature_name"]),
                role=str(kwargs.get("role", "user")),
                allowed=int(bool(kwargs.get("allowed", False))),
                runtime_origin=str(kwargs.get("runtime_origin", "unknown")),
                payload=dict(kwargs.get("payload") or {}),
            )
            session.add(event)
            session.commit()
            return {column.name: getattr(event, column.name) for column in event.__table__.columns}

    def save_feature_flag(self, **kwargs: Any) -> dict[str, Any]:
        with get_session(self.sqlite_path) as session:
            feature_name = str(kwargs["feature_name"]).strip().lower()
            existing = session.query(FeatureFlag).filter(FeatureFlag.feature_name == feature_name).first()
            if existing is None:
                flag = FeatureFlag(
                    feature_name=feature_name,
                    enabled=int(bool(kwargs.get("enabled", False))),
                    role_scope=str(kwargs.get("role_scope", "user")).strip().lower(),
                    max_uses_per_session=kwargs.get("max_uses_per_session"),
                    payload=dict(kwargs.get("payload") or {}),
                )
                session.add(flag)
                session.commit()
                return {column.name: getattr(flag, column.name) for column in flag.__table__.columns}

            existing.enabled = int(bool(kwargs.get("enabled", existing.enabled)))
            existing.role_scope = str(kwargs.get("role_scope", existing.role_scope)).strip().lower()
            existing.max_uses_per_session = kwargs.get("max_uses_per_session", existing.max_uses_per_session)
            existing.payload = dict(kwargs.get("payload") or existing.payload or {})
            session.commit()
            return {column.name: getattr(existing, column.name) for column in existing.__table__.columns}

    def get_feature_flag(self, feature_name: str) -> dict[str, Any] | None:
        with get_session(self.sqlite_path) as session:
            row = session.query(FeatureFlag).filter(FeatureFlag.feature_name == feature_name.strip().lower()).first()
            if row is None:
                return None
            return {column.name: getattr(row, column.name) for column in row.__table__.columns}

    def save_feature_usage_event(self, **kwargs: Any) -> dict[str, Any]:
        with get_session(self.sqlite_path) as session:
            event = FeatureUsageEvent(
                user_id=int(kwargs["user_id"]),
                session_id=str(kwargs["session_id"]),
                feature_name=str(kwargs["feature_name"]),
                role=str(kwargs.get("role", "user")),
                allowed=int(bool(kwargs.get("allowed", False))),
                runtime_origin=str(kwargs.get("runtime_origin", "unknown")),
                payload=dict(kwargs.get("payload") or {}),
            )
            session.add(event)
            session.commit()
            return {column.name: getattr(event, column.name) for column in event.__table__.columns}

    def save_generation_event(self, **kwargs: Any) -> dict[str, Any]:
        repository = GenerationEventRepository(self.sqlite_path)
        return repository.insert(**kwargs)

    def save_check_event(self, **kwargs: Any) -> dict[str, Any]:
        repository = CheckEventRepository(self.sqlite_path)
        return repository.insert(**kwargs)

    def save_ml_usage_event(self, **kwargs: Any) -> dict[str, Any]:
        repository = MlUsageEventRepository(self.sqlite_path)
        return repository.insert(**kwargs)

    def save_report_event(self, **kwargs: Any) -> dict[str, Any]:
        repository = ReportEventRepository(self.sqlite_path)
        return repository.insert(**kwargs)

    def save_expansion_event(self, **kwargs: Any) -> dict[str, Any]:
        repository = ExpansionEventRepository(self.sqlite_path)
        return repository.insert(**kwargs)

    def save_reconciliation_event(self, **kwargs: Any) -> dict[str, Any]:
        repository = ReconciliationEventRepository(self.sqlite_path)
        return repository.insert(**kwargs)

    def save_reset_event(self, **kwargs: Any) -> dict[str, Any]:
        with get_session(self.sqlite_path) as session:
            event = ResetEvent(
                reset_type=str(kwargs.get("reset_type", "operational")),
                triggered_by=str(kwargs.get("triggered_by", "system")),
                affected_tables=list(kwargs.get("affected_tables") or []),
                payload=dict(kwargs.get("payload") or {}),
                status=str(kwargs.get("status", "completed")),
                notes=str(kwargs.get("notes", "")),
            )
            session.add(event)
            session.commit()
            return {column.name: getattr(event, column.name) for column in event.__table__.columns}

    def fetch_generation_events(self, lead_id: int | None = None) -> list[dict[str, Any]]:
        with get_session(self.sqlite_path) as session:
            query = session.query(GenerationEvent)
            if lead_id is not None:
                query = query.filter(GenerationEvent.lead_id == lead_id)
            rows = query.order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc()).all()
            return [
                {column.name: getattr(row, column.name) for column in row.__table__.columns}
                for row in rows
            ]

    def fetch_usage_metrics(self) -> dict[str, int]:
        with get_session(self.sqlite_path) as session:
            return {
                "leads": int(session.query(Lead).count()),
                "institutional_users": int(session.query(InstitutionalUser).count()),
                "auth_events": int(session.query(AuthEvent).count()),
                "auth_sessions": int(session.query(AuthSession).count()),
                "access_events": int(session.query(AccessEvent).count()),
                "feature_flags": int(session.query(FeatureFlag).count()),
                "feature_usage_events": int(session.query(FeatureUsageEvent).count()),
                "generation_events": int(session.query(GenerationEvent).count()),
                "ml_usage_events": int(session.query(MlUsageEvent).count()),
                "check_events": int(session.query(CheckEvent).count()),
                "report_events": int(session.query(ReportEvent).count()),
                "expansion_events": int(session.query(ExpansionEvent).count()),
                "reconciliation_events": int(session.query(ReconciliationEvent).count()),
                "reset_events": int(session.query(ResetEvent).count()),
            }

    def fetch_latest_usage_snapshot(self) -> dict[str, Any]:
        metrics = self.fetch_usage_metrics()
        return {
            **metrics,
            "backend": self.backend,
            "database_url": self.database_url,
            "sqlite_path": str(self.sqlite_path),
            "shared_cloud_ready": self.is_shared_cloud_ready,
        }

    def fetch_latest_auth_snapshot(self) -> dict[str, Any]:
        metrics = self.fetch_usage_metrics()
        return {
            "backend": self.backend,
            "database_url": self.database_url,
            "sqlite_path": str(self.sqlite_path),
            "shared_cloud_ready": self.is_shared_cloud_ready,
            "institutional_users": metrics["institutional_users"],
            "auth_events": metrics["auth_events"],
            "auth_sessions": metrics["auth_sessions"],
            "access_events": metrics["access_events"],
            "feature_flags": metrics["feature_flags"],
            "feature_usage_events": metrics["feature_usage_events"],
        }


class SQLiteInstitutionalAdapter(InstitutionalDatabaseAdapter):
    """SQLite-backed institutional adapter kept for local/runtime compatibility."""

    pass


class PostgresInstitutionalAdapter(InstitutionalDatabaseAdapter):
    """PostgreSQL-ready adapter placeholder for shared institutional persistence."""

    @property
    def is_shared_cloud_ready(self) -> bool:
        return True


def resolve_institutional_adapter(path: Path = DEFAULT_DATABASE_PATH) -> InstitutionalDatabaseAdapter:
    adapter = InstitutionalDatabaseAdapter(path)
    if adapter.backend == "postgresql":
        return PostgresInstitutionalAdapter(path)
    return SQLiteInstitutionalAdapter(path)
