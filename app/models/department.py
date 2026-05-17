from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee


class Department(Base, TimestampMixin):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("parent_id", "name", name="uq_departments_parent_id_name"),
        CheckConstraint("length(name) BETWEEN 1 AND 200", name="name_length"),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="no_self_parent"),
        Index("ix_departments_parent_id", "parent_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=True,
    )

    parent: Mapped[Department | None] = relationship(
        "Department",
        remote_side="Department.id",
        back_populates="children",
    )
    children: Mapped[list[Department]] = relationship(
        "Department",
        back_populates="parent",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    employees: Mapped[list[Employee]] = relationship(
        "Employee",
        back_populates="department",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Department id={self.id} name={self.name!r} parent_id={self.parent_id}>"
