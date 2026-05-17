from __future__ import annotations

import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.employee import Employee
from app.repositories.department import DepartmentRepository
from app.repositories.employee import EmployeeRepository

logger = logging.getLogger(__name__)


class EmployeeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.departments = DepartmentRepository(session)
        self.employees = EmployeeRepository(session)

    async def create_in_department(
        self,
        department_id: int,
        *,
        full_name: str,
        position: str,
        hired_at: date | None,
    ) -> Employee:
        if not await self.departments.exists(department_id):
            raise NotFoundError(f"Department {department_id} not found")

        employee = await self.employees.create(
            department_id=department_id,
            full_name=full_name,
            position=position,
            hired_at=hired_at,
        )
        await self.session.commit()
        logger.info(
            "Created employee id=%s full_name=%r department_id=%s",
            employee.id, employee.full_name, department_id,
        )
        return employee
