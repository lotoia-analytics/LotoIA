from __future__ import annotations

import sys
import types

if "matplotlib" not in sys.modules:
    matplotlib = types.ModuleType("matplotlib")
    pyplot = types.ModuleType("matplotlib.pyplot")
    pyplot.subplots = lambda *args, **kwargs: (type("Fig", (), {"add_axes": lambda *a, **k: type("Ax", (), {"axis": lambda *a, **k: None, "text": lambda *a, **k: None, "table": lambda *a, **k: type("Tbl", (), {"auto_set_font_size": lambda *a, **k: None, "set_fontsize": lambda *a, **k: None, "scale": lambda *a, **k: None})()})(), "savefig": lambda *a, **k: None})(), type("Ax", (), {"axis": lambda *a, **k: None, "text": lambda *a, **k: None, "table": lambda *a, **k: None})())
    pyplot.close = lambda *args, **kwargs: None
    matplotlib.pyplot = pyplot  # type: ignore[attr-defined]
    sys.modules["matplotlib"] = matplotlib
    sys.modules["matplotlib.pyplot"] = pyplot

import dashboard.app as cloud_app
import dashboard.institutional_app as institutional_app
import dashboard.public_app as public_cloud_app


def test_streamlit_cloud_entrypoint_delegates_to_institutional_dashboard() -> None:
    assert callable(cloud_app.main)
    assert callable(public_cloud_app.main)
    assert callable(institutional_app.main)


def test_public_app_build_marker_identifies_public_surface() -> None:
    assert "public" in public_cloud_app.PUBLIC_APP_BUILD.lower()
    assert "m-plat-041" in public_cloud_app.PUBLIC_APP_BUILD.lower()


def test_public_app_has_explicit_institutional_delegate() -> None:
    assert callable(public_cloud_app.render_institutional_adm)


def test_institutional_app_has_auth_and_cloud_policy_hooks() -> None:
    assert hasattr(institutional_app, "main")
    from dashboard import institutional_auth
    from lotoia.governance import cloud_runtime_policy

    assert hasattr(institutional_auth, "require_institutional_login")
    assert hasattr(cloud_runtime_policy, "enforce_cloud_runtime_policy")
