"""Mandatory authentication gate for the institutional ADM panel."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import streamlit as st

from lotoia.authentication import AuthenticationService, LoginRequest
from lotoia.governance.cloud_runtime_policy import is_auth_required

SESSION_USER_KEY = "institutional_auth_user"
SESSION_SESSION_ID_KEY = "institutional_auth_session_id"
RUNTIME_ORIGIN = "railway_cloud"


def _bootstrap_admin_if_configured(service: AuthenticationService) -> None:
    email = os.getenv("LOTOIA_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("LOTOIA_ADMIN_PASSWORD", "").strip()
    if not email or not password:
        return
    snapshot = service.adapter.fetch_latest_auth_snapshot()
    if int(snapshot.get("institutional_users", 0) or 0) > 0:
        return
    service.register_user(
        email=email,
        password=password,
        role="admin",
        metadata_json={"source": "cloud_bootstrap", "runtime_origin": RUNTIME_ORIGIN},
    )


def _current_user() -> dict[str, Any] | None:
    user = st.session_state.get(SESSION_USER_KEY)
    return user if isinstance(user, dict) else None


def _current_session_id() -> str:
    return str(st.session_state.get(SESSION_SESSION_ID_KEY, "") or "")


def _set_authenticated_user(*, user_id: int, email: str, role: str, session_id: str) -> None:
    st.session_state[SESSION_USER_KEY] = {
        "id": int(user_id),
        "email": str(email),
        "role": str(role),
        "status": "active",
    }
    st.session_state[SESSION_SESSION_ID_KEY] = str(session_id)


def _clear_authenticated_user() -> None:
    st.session_state.pop(SESSION_USER_KEY, None)
    st.session_state.pop(SESSION_SESSION_ID_KEY, None)


def _render_login_page(db_path: Path) -> None:
    st.title("LotoIA — Acesso Institucional")
    st.caption("Painel ADM protegido. Autenticação obrigatória em runtime cloud.")
    service = AuthenticationService(db_path)
    _bootstrap_admin_if_configured(service)

    with st.form("institutional_login_form", clear_on_submit=False):
        email = st.text_input("E-mail institucional")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar", type="primary", use_container_width=True)

    if not submitted:
        return

    try:
        result = service.login(
            LoginRequest(email=email, password=password),
            runtime_origin=RUNTIME_ORIGIN,
            user_agent="streamlit_institutional_panel",
            payload={"source": "institutional_auth_gate"},
        )
    except ValueError:
        st.error("Credenciais inválidas ou usuário inativo.")
        return

    _set_authenticated_user(
        user_id=result.user.id,
        email=result.user.email,
        role=result.user.role,
        session_id=result.session_id,
    )
    st.rerun()


def _render_logout_control(db_path: Path) -> None:
    user = _current_user()
    if user is None:
        return
    st.sidebar.caption(f"Usuário: {user.get('email', '-')}")
    st.sidebar.caption(f"Perfil: {user.get('role', '-')}")
    if st.sidebar.button("Sair", key="institutional_logout_button"):
        service = AuthenticationService(db_path)
        session_id = _current_session_id()
        if session_id:
            service.logout(
                user_id=int(user["id"]),
                session_id=session_id,
                runtime_origin=RUNTIME_ORIGIN,
                payload={"source": "institutional_auth_gate"},
            )
        _clear_authenticated_user()
        st.rerun()


def require_institutional_login(db_path: Path) -> dict[str, Any] | None:
    """Return authenticated user or stop rendering with login page."""
    if not is_auth_required():
        return None

    user = _current_user()
    if user is None:
        _render_login_page(db_path)
        st.stop()
        return None

    _render_logout_control(db_path)
    return user
