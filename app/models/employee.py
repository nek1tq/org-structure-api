from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.department import Department


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(
            "length(full_name) BETWEEN 1 AND 200", name="full_name_length"
        ),
        CheckConstraint(
            "length(position) BETWEEN 1 AND 200", name="position_length"
        ),
        Index("ix_employees_department_id", "department_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str] = mapped_column(String(200), nullable=False)
    hired_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    department: Mapped[Department] = relationship(
        "Department", back_populates="employees"
    )

    def __repr__(self) -> str:
        return (
            f"<Employee id={self.id} full_name={self.full_name!r} "
            f"department_id={self.department_id}>"
        )
