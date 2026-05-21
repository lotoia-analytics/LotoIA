from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class PublicGenerationRequest(BaseModel):
    first_name: str
    whatsapp: str
    ml_enabled: bool = False

    @field_validator("first_name")
    @classmethod
    def _validate_first_name(cls, value: str) -> str:
        if len(value.strip()) < 2:
            raise ValueError("first_name must contain at least 2 characters")
        return value.strip()

    @field_validator("whatsapp")
    @classmethod
    def _validate_whatsapp(cls, value: str) -> str:
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) < 10 or len(digits) > 13:
            raise ValueError("whatsapp must contain 10 to 13 digits")
        return digits


class PublicCheckRequest(BaseModel):
    first_name: str
    whatsapp: str
    contest_id: int = Field(ge=1)
    numbers: list[int]

    @field_validator("first_name")
    @classmethod
    def _validate_first_name(cls, value: str) -> str:
        if len(value.strip()) < 2:
            raise ValueError("first_name must contain at least 2 characters")
        return value.strip()

    @field_validator("whatsapp")
    @classmethod
    def _validate_whatsapp(cls, value: str) -> str:
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) < 10 or len(digits) > 13:
            raise ValueError("whatsapp must contain 10 to 13 digits")
        return digits

    @field_validator("numbers")
    @classmethod
    def _validate_numbers(cls, value: list[int]) -> list[int]:
        numbers = sorted(set(int(number) for number in value))
        if len(numbers) != 15:
            raise ValueError("numbers must contain exactly 15 unique integers")
        if any(number < 1 or number > 25 for number in numbers):
            raise ValueError("numbers must be between 1 and 25")
        return numbers
