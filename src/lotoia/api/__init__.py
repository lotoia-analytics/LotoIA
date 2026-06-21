"""API LotoIA — endpoints e motor de calibração autônoma (M-AUTO-CALIB-001)."""

from lotoia.api.lotoia_calibration_api import (
    MISSION_ID,
    API_VERSION,
    build_external_agent_payload,
    evaluate_structural_sovereignty,
    is_lotoia_auto_calib_api_enabled,
    process_sovereign_payload_with_lotoia_api,
)

__all__ = [
    "API_VERSION",
    "MISSION_ID",
    "build_external_agent_payload",
    "evaluate_structural_sovereignty",
    "is_lotoia_auto_calib_api_enabled",
    "process_sovereign_payload_with_lotoia_api",
]
