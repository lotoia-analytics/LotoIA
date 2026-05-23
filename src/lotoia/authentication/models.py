from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=256)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned:
            raise ValueError("email must be valid.")
        return cleaned


@dataclass(frozen=True)
class InstitutionalUserIdentity:
    id: int
    email: str
    role: str
    status: str


@dataclass(frozen=True)
class AuthenticationResult:
    user: InstitutionalUserIdentity
    session_id: str
    created: bool
    backend_snapshot: dict[str, object]


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    feature_name: str
    role: str
    session_id: str
    snapshot: dict[str, object]


@dataclass(frozen=True)
class FeaturePolicyDecision:
    allowed: bool
    feature_name: str
    role: str
    limit: int | None
    usage_count: int
    session_id: str
    snapshot: dict[str, object]
