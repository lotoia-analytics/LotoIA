from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.public.persistence import LeadRepository, initialize_public_persistence

MAX_WHATSAPP_DIGITS = 15
MIN_WHATSAPP_DIGITS = 8


class LeadCaptureRequest(BaseModel):
    first_name: str = Field(min_length=2, max_length=80)
    whatsapp: str = Field(min_length=8, max_length=32)
    source: str = Field(default="public_api", min_length=1, max_length=80)

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, value: str) -> str:
        cleaned = _sanitize_first_name(value)
        if len(cleaned) < 2:
            raise ValueError("first_name must contain at least 2 characters.")
        return cleaned

    @field_validator("whatsapp")
    @classmethod
    def validate_whatsapp(cls, value: str) -> str:
        return normalize_whatsapp(value)

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("source cannot be empty.")
        return cleaned


@dataclass(frozen=True)
class LeadCaptureResult:
    lead: dict[str, Any]
    created: bool
    normalized_whatsapp: str
    ip_hash: str


class LeadCaptureService:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path
        initialize_public_persistence(db_path)
        self.repository = LeadRepository(db_path)

    def capture(
        self,
        payload: LeadCaptureRequest,
        *,
        ip_address: str = "",
        user_agent: str = "",
    ) -> LeadCaptureResult:
        normalized_whatsapp = normalize_whatsapp(payload.whatsapp)
        ip_hash = hash_ip(ip_address)
        existing = self._find_existing(payload.first_name, normalized_whatsapp)
        if existing:
            return LeadCaptureResult(
                lead=existing,
                created=False,
                normalized_whatsapp=normalized_whatsapp,
                ip_hash=ip_hash,
            )

        lead = self.repository.insert(
            first_name=payload.first_name,
            whatsapp=normalized_whatsapp,
            source=payload.source,
            ip_hash=ip_hash,
            user_agent=user_agent,
        )
        return LeadCaptureResult(
            lead=lead,
            created=True,
            normalized_whatsapp=normalized_whatsapp,
            ip_hash=ip_hash,
        )

    def _find_existing(self, first_name: str, whatsapp: str) -> dict[str, Any] | None:
        return self.repository.find_by_first_name_and_whatsapp(first_name, whatsapp)


def normalize_whatsapp(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        raise ValueError("whatsapp is required.")
    if len(digits) < MIN_WHATSAPP_DIGITS:
        raise ValueError("whatsapp must contain at least 8 digits.")
    if len(digits) > MAX_WHATSAPP_DIGITS:
        raise ValueError("whatsapp must contain at most 15 digits.")
    return digits


def hash_ip(ip_address: str) -> str:
    if not ip_address:
        return ""
    return hashlib.sha256(ip_address.encode("utf-8")).hexdigest()


def _sanitize_first_name(value: str) -> str:
    cleaned = " ".join((value or "").strip().split())
    if not cleaned:
        raise ValueError("first_name is required.")
    return cleaned
