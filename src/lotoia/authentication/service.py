from __future__ import annotations

import hashlib
import hmac
import secrets
from pathlib import Path
from typing import Any

from lotoia.database.adapter import InstitutionalDatabaseAdapter, resolve_institutional_adapter
from lotoia.database.database import DEFAULT_DATABASE_PATH, get_session, InstitutionalUser
from lotoia.authentication.models import AccessDecision, AuthenticationResult, InstitutionalUserIdentity, LoginRequest

ROLE_FEATURE_ACCESS: dict[str, set[str]] = {
    "admin": {"ml", "expansion", "reports", "reconciliation", "workflow", "governance", "observability", "analytics"},
    "operator": {"generation", "check", "reports", "reconciliation", "workflow", "analytics"},
    "premium": {"generation", "check", "ml", "reports", "expansion", "reconciliation", "analytics"},
    "basic": {"generation", "check", "reports", "analytics"},
    "user": {"generation", "check", "reports", "analytics"},
}


def _hash_password(password: str, salt: str | None = None) -> str:
    salt_value = salt or secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_value.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt_value}${derived.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt, digest = stored_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    expected = _hash_password(password, salt=salt)
    return hmac.compare_digest(expected, stored_hash)


class AuthenticationService:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path
        self.adapter: InstitutionalDatabaseAdapter = resolve_institutional_adapter(db_path)

    def register_user(
        self,
        *,
        email: str,
        password: str,
        role: str = "user",
        metadata_json: dict[str, Any] | None = None,
    ) -> AuthenticationResult:
        normalized_email = LoginRequest(email=email, password=password).email
        existing = self._find_user(normalized_email)
        if existing is not None:
            identity = InstitutionalUserIdentity(
                id=int(existing["id"]),
                email=str(existing["email"]),
                role=str(existing["role"]),
                status=str(existing["status"]),
            )
            return AuthenticationResult(
                user=identity,
                session_id="",
                created=False,
                backend_snapshot=self.adapter.fetch_latest_auth_snapshot(),
            )

        user = self.adapter.save_institutional_user(
            email=normalized_email,
            password_hash=_hash_password(password),
            role=role,
            status="active",
            metadata_json=metadata_json or {},
        )
        identity = InstitutionalUserIdentity(
            id=int(user["id"]),
            email=str(user["email"]),
            role=str(user["role"]),
            status=str(user["status"]),
        )
        return AuthenticationResult(
            user=identity,
            session_id="",
            created=True,
            backend_snapshot=self.adapter.fetch_latest_auth_snapshot(),
        )

    def login(
        self,
        request: LoginRequest,
        *,
        runtime_origin: str = "streamlit_cloud",
        ip_hash: str = "",
        user_agent: str = "",
        payload: dict[str, Any] | None = None,
    ) -> AuthenticationResult:
        normalized_email = request.email
        user = self._find_user(normalized_email)
        if user is None:
            raise ValueError("invalid credentials")
        if str(user["status"]).lower() != "active":
            raise ValueError("user is not active")
        if not _verify_password(request.password, str(user["password_hash"])):
            raise ValueError("invalid credentials")

        session_id = secrets.token_urlsafe(24)
        self.adapter.save_login_event(
            user_id=int(user["id"]),
            session_id=session_id,
            runtime_origin=runtime_origin,
            ip_hash=ip_hash,
            user_agent=user_agent,
            payload=payload or {},
        )
        identity = InstitutionalUserIdentity(
            id=int(user["id"]),
            email=str(user["email"]),
            role=str(user["role"]),
            status=str(user["status"]),
        )
        return AuthenticationResult(
            user=identity,
            session_id=session_id,
            created=False,
            backend_snapshot=self.adapter.fetch_latest_auth_snapshot(),
        )

    def logout(
        self,
        *,
        user_id: int,
        session_id: str,
        runtime_origin: str = "streamlit_cloud",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.adapter.save_logout_event(
            user_id=user_id,
            session_id=session_id,
            runtime_origin=runtime_origin,
            payload=payload or {},
        )

    def change_role(
        self,
        *,
        user_id: int,
        role: str,
        session_id: str = "",
        runtime_origin: str = "streamlit_cloud",
        reason: str = "",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_role = self._normalize_role(role)
        return self.adapter.save_role_change_event(
            user_id=user_id,
            role=normalized_role,
            session_id=session_id,
            runtime_origin=runtime_origin,
            reason=reason,
            payload=payload or {},
        )

    def authorize_feature(
        self,
        *,
        user_id: int,
        session_id: str,
        feature_name: str,
        runtime_origin: str = "streamlit_cloud",
        payload: dict[str, Any] | None = None,
    ) -> AccessDecision:
        user = self._find_user_by_id(user_id)
        if user is None:
            raise ValueError("institutional user not found")
        role = str(user["role"]).lower()
        normalized_feature = self._normalize_feature(feature_name)
        allowed = normalized_feature in ROLE_FEATURE_ACCESS.get(role, set())
        self.adapter.save_access_event(
            user_id=user_id,
            session_id=session_id,
            feature_name=normalized_feature,
            role=role,
            allowed=allowed,
            runtime_origin=runtime_origin,
            payload=payload or {},
        )
        return AccessDecision(
            allowed=allowed,
            feature_name=normalized_feature,
            role=role,
            session_id=session_id,
            snapshot=self.adapter.fetch_latest_auth_snapshot(),
        )

    def _find_user(self, email: str) -> dict[str, Any] | None:
        with get_session(self.db_path) as session:
            row = session.query(InstitutionalUser).filter(InstitutionalUser.email == email).first()
            if row is None:
                return None
            return {column.name: getattr(row, column.name) for column in row.__table__.columns}

    def _find_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        with get_session(self.db_path) as session:
            row = session.get(InstitutionalUser, user_id)
            if row is None:
                return None
            return {column.name: getattr(row, column.name) for column in row.__table__.columns}

    @staticmethod
    def _normalize_role(role: str) -> str:
        cleaned = role.strip().lower()
        if cleaned not in ROLE_FEATURE_ACCESS:
            raise ValueError(f"unsupported role: {role}")
        return cleaned

    @staticmethod
    def _normalize_feature(feature_name: str) -> str:
        cleaned = feature_name.strip().lower()
        if not cleaned:
            raise ValueError("feature_name is required.")
        return cleaned
