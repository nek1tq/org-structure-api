from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _strip_and_check(value: str, field: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field} must not be empty or whitespace-only")
    return stripped


class EmployeeBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    position: str = Field(..., min_length=1, max_length=200)
    hired_at: date | None = None

    @field_validator("full_name")
    @classmethod
    def _validate_full_name(cls, v: str) -> str:
        return _strip_and_check(v, "full_name")

    @field_validator("position")
    @classmethod
    def _validate_position(cls, v: str) -> str:
        return _strip_and_check(v, "position")


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeResponse(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    created_at: datetime
