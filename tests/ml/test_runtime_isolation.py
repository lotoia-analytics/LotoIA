from __future__ import annotations

from lotoia.ml import describe_ml_runtime_isolation, get_isolated_ml_runtime_state


def test_ml_runtime_isolation_contract_exposes_separated_layers() -> None:
    contract = describe_ml_runtime_isolation()

    payload = contract.as_dict()
    assert payload["analytics_runtime"] == "statistical"
    assert payload["ml_runtime"] == "isolated"
    assert payload["inference_runtime"] == "governed"
    assert "ml_runtime_status" in payload["runtime_state"]


def test_ml_runtime_isolation_state_includes_heartbeat() -> None:
    state = get_isolated_ml_runtime_state()

    assert state["contract"]["ml_runtime"] == "isolated"
    assert state["heartbeat"]["status"] in {"idle", "active", "degraded"}
