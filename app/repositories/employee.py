from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee


class EmployeeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        department_id: int,
        full_name: str,
        position: str,
        hired_at: date | None,
    ) -> Employee:
        employee = Employee(
            department_id=department_id,
            full_name=full_name,
            position=position,
            hired_at=hired_at,
        )
        self.session.add(employee)
        await self.session.flush()
        await self.session.refresh(employee)
        return employee

    async def list_by_department(
        self, department_id: int, *, sort_by: str = "created_at"
    ) -> list[Employee]:
        order_column = (
            Employee.full_name if sort_by == "full_name" else Employee.created_at
        )
        result = await self.session.execute(
            select(Employee)
            .where(Employee.department_id == department_id)
            .order_by(order_column, Employee.id)
        )
        return list(result.scalars().all())
