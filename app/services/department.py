from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.department import Department
from app.repositories.department import DepartmentRepository
from app.repositories.employee import EmployeeRepository
from app.schemas.department import (
    DeleteMode,
    DepartmentTree,
    EmployeeSort,
)
from app.schemas.employee import EmployeeResponse

logger = logging.getLogger(__name__)


class DepartmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.departments = DepartmentRepository(session)
        self.employees = EmployeeRepository(session)

    async def create(self, *, name: str, parent_id: int | None) -> Department:
        if parent_id is not None and not await self.departments.exists(parent_id):
            raise NotFoundError(f"Parent department {parent_id} not found")
        if await self.departments.name_taken(parent_id, name):
            raise ConflictError(
                f"Department named {name!r} already exists under parent {parent_id}"
            )
        department = await self.departments.create(name=name, parent_id=parent_id)
        await self.session.commit()
        logger.info(
            "Created department id=%s name=%r parent_id=%s",
            department.id, department.name, department.parent_id,
        )
        return department

    async def get(self, department_id: int) -> Department:
        department = await self.departments.get(department_id)
        if department is None:
            raise NotFoundError(f"Department {department_id} not found")
        return department

    async def get_tree(
        self,
        department_id: int,
        *,
        depth: int,
        include_employees: bool,
        employee_sort: EmployeeSort,
    ) -> DepartmentTree:
        rows = await self.departments.fetch_subtree(department_id, depth)
        if not rows:
            raise NotFoundError(f"Department {department_id} not found")

        nodes: dict[int, DepartmentTree] = {}
        for dept, _level in rows:
            node = DepartmentTree(
                id=dept.id,
                name=dept.name,
                parent_id=dept.parent_id,
                created_at=dept.created_at,
            )
            if include_employees:
                emps = await self.employees.list_by_department(
                    dept.id, sort_by=employee_sort.value
                )
                node.employees = [EmployeeResponse.model_validate(e) for e in emps]
            nodes[dept.id] = node

        root_id = rows[0][0].id
        for dept, _level in rows:
            if dept.id == root_id:
                continue
            parent_node = nodes.get(dept.parent_id) if dept.parent_id else None
            if parent_node is not None:
                parent_node.children.append(nodes[dept.id])

        return nodes[root_id]

    async def update(
        self,
        department_id: int,
        *,
        name: str | None,
        parent_id_provided: bool,
        parent_id: int | None,
    ) -> Department:
        department = await self.get(department_id)

        new_parent_id = department.parent_id
        if parent_id_provided:
            if parent_id == department_id:
                raise ConflictError("Department cannot be its own parent")
            if parent_id is not None:
                if not await self.departments.exists(parent_id):
                    raise NotFoundError(f"Parent department {parent_id} not found")
                if await self.departments.is_descendant_of(parent_id, department_id):
                    raise ConflictError(
                        "Cannot move department into its own subtree (cycle)"
                    )
            new_parent_id = parent_id

        new_name = name if name is not None else department.name
        if new_name != department.name or new_parent_id != department.parent_id:
            if await self.departments.name_taken(
                new_parent_id, new_name, exclude_id=department_id
            ):
                raise ConflictError(
                    f"Department named {new_name!r} already exists "
                    f"under parent {new_parent_id}"
                )

        updated = await self.departments.update_fields(
            department,
            name=name,
            parent_id=parent_id if parent_id_provided else ...,
        )
        await self.session.commit()
        logger.info(
            "Updated department id=%s name=%r parent_id=%s",
            updated.id, updated.name, updated.parent_id,
        )
        return updated

    async def delete(
        self,
        department_id: int,
        *,
        mode: DeleteMode,
        reassign_to_department_id: int | None,
    ) -> None:
        department = await self.get(department_id)

        if mode is DeleteMode.cascade:
            await self.departments.delete(department)
            await self.session.commit()
            logger.info("Cascade-deleted department id=%s", department_id)
            return

        if reassign_to_department_id is None:
            raise ValidationError(
                "reassign_to_department_id is required when mode=reassign"
            )
        if reassign_to_department_id == department_id:
            raise ConflictError("Cannot reassign employees to the department being deleted")
        if not await self.departments.exists(reassign_to_department_id):
            raise NotFoundError(
                f"Reassign target department {reassign_to_department_id} not found"
            )
        if await self.departments.has_children(department_id):
            raise ConflictError(
                "Cannot use reassign mode: department has child departments. "
                "Use mode=cascade or move children first."
            )

        moved = await self.departments.reassign_employees(
            department_id, reassign_to_department_id
        )
        await self.departments.delete(department)
        await self.session.commit()
        logger.info(
            "Reassigned %s employees from dept=%s to dept=%s, then deleted dept=%s",
            moved, department_id, reassign_to_department_id, department_id,
        )
