from __future__ import annotations

from lotoia.public.services import normalize_whatsapp


def canonical_brazil_phone(phone: str) -> str:
    """Prefer E.164-style storage for Brazilian mobiles when possible."""
    normalized = normalize_whatsapp(phone)
    if normalized.startswith("55"):
        return normalized
    if len(normalized) in (10, 11):
        return f"55{normalized}"
    return normalized


def phone_lookup_candidates(phone: str) -> list[str]:
    """Return normalized phone variants for Brazil (with and without country code)."""
    raw = str(phone or "").strip()
    if raw.startswith("m:"):
        return [raw]
    normalized = normalize_whatsapp(phone)
    candidates = [normalized, canonical_brazil_phone(normalized)]
    if normalized.startswith("55") and len(normalized) > 11:
        candidates.append(normalized[2:])
    elif len(normalized) in (10, 11):
        candidates.append(f"55{normalized}")
    return list(dict.fromkeys(candidate for candidate in candidates if candidate))
