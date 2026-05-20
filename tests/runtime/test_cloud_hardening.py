from __future__ import annotations

import sys
import types
from pathlib import Path

import pandas as pd

if "matplotlib" not in sys.modules:
    matplotlib = types.ModuleType("matplotlib")
    pyplot = types.ModuleType("matplotlib.pyplot")
    pyplot.subplots = lambda *args, **kwargs: (type("Fig", (), {"add_axes": lambda *a, **k: type("Ax", (), {"axis": lambda *a, **k: None, "text": lambda *a, **k: None, "table": lambda *a, **k: type("Tbl", (), {"auto_set_font_size": lambda *a, **k: None, "set_fontsize": lambda *a, **k: None, "scale": lambda *a, **k: None})()})(), "savefig": lambda *a, **k: None})(), type("Ax", (), {"axis": lambda *a, **k: None, "text": lambda *a, **k: None, "table": lambda *a, **k: None})())
    pyplot.close = lambda *args, **kwargs: None
    matplotlib.pyplot = pyplot  # type: ignore[attr-defined]
    sys.modules["matplotlib"] = matplotlib
    sys.modules["matplotlib.pyplot"] = pyplot

import dashboard.admin_app as admin_app


def test_safe_input_helpers_apply_limits() -> None:
    assert admin_app._safe_int("9", 0, minimum=1, maximum=10) == 9
    assert admin_app._safe_int("invalid", 3) == 3
    assert admin_app._safe_float("4.5", 0.0, minimum=1.0, maximum=5.0) == 4.5
    assert admin_app._safe_text("  hello world  ", max_length=5) == "hello"


def test_safe_dataframe_and_download_helpers_handle_missing_data(tmp_path: Path) -> None:
    frame = admin_app._safe_dataframe(None, columns=["a", "b"])
    assert list(frame.columns) == ["a", "b"]

    missing = tmp_path / "missing.txt"
    assert admin_app._safe_download_bytes(missing) is None

    existing = tmp_path / "existing.csv"
    pd.DataFrame([{"a": 1}]).to_csv(existing, index=False)
    assert admin_app._safe_download_bytes(existing) is not None
