from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.services.department import DepartmentService
from app.services.employee import EmployeeService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_department_service(session: SessionDep) -> AsyncIterator[DepartmentService]:
    yield DepartmentService(session)


async def get_employee_service(session: SessionDep) -> AsyncIterator[EmployeeService]:
    yield EmployeeService(session)


DepartmentServiceDep = Annotated[DepartmentService, Depends(get_department_service)]
EmployeeServiceDep = Annotated[EmployeeService, Depends(get_employee_service)]
