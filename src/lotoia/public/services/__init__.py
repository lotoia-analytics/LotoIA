from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "LeadCaptureRequest",
    "LeadCaptureService",
    "hash_ip",
    "normalize_whatsapp",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "LeadCaptureRequest": ("lotoia.public.services.lead_capture_service", "LeadCaptureRequest"),
    "LeadCaptureService": ("lotoia.public.services.lead_capture_service", "LeadCaptureService"),
    "hash_ip": ("lotoia.public.services.lead_capture_service", "hash_ip"),
    "normalize_whatsapp": ("lotoia.public.services.lead_capture_service", "normalize_whatsapp"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value

