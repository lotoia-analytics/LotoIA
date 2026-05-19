from pydantic import BaseModel, Field, field_validator


class Draw(BaseModel):
    contest: int = Field(gt=0)
    date: str | None = None
    numbers: list[int] = Field(min_length=15, max_length=15)

    @field_validator("numbers")
    @classmethod
    def validate_numbers(cls, value: list[int]) -> list[int]:
        if len(set(value)) != 15:
            raise ValueError("Um concurso deve conter 15 dezenas unicas.")
        if any(number < 1 or number > 25 for number in value):
            raise ValueError("As dezenas devem estar entre 1 e 25.")
        return sorted(value)
