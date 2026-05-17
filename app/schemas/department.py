from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.employee import EmployeeResponse


def _strip_name(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("name must not be empty or whitespace-only")
    return stripped


class DepartmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        return _strip_name(v)


class DepartmentCreate(DepartmentBase):
    parent_id: int | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    parent_id: int | None = None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _strip_name(v)


class DepartmentResponse(DepartmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: int | None
    created_at: datetime


class DepartmentTree(DepartmentResponse):
    employees: list[EmployeeResponse] = Field(default_factory=list)
    children: list[DepartmentTree] = Field(default_factory=list)


DepartmentTree.model_rebuild()


class DeleteMode(str, Enum):
    cascade = "cascade"
    reassign = "reassign"


class EmployeeSort(str, Enum):
    created_at = "created_at"
    full_name = "full_name"
