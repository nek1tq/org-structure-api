from __future__ import annotations

from sqlalchemy import literal, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department


class DepartmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, department_id: int) -> Department | None:
        return await self.session.get(Department, department_id)

    async def exists(self, department_id: int) -> bool:
        result = await self.session.execute(
            select(Department.id).where(Department.id == department_id)
        )
        return result.scalar_one_or_none() is not None

    async def name_taken(
        self, parent_id: int | None, name: str, exclude_id: int | None = None
    ) -> bool:
        stmt = select(Department.id).where(
            Department.parent_id.is_(parent_id) if parent_id is None
            else Department.parent_id == parent_id,
            Department.name == name,
        )
        if exclude_id is not None:
            stmt = stmt.where(Department.id != exclude_id)
        result = await self.session.execute(stmt)
        return result.first() is not None

    async def has_children(self, department_id: int) -> bool:
        result = await self.session.execute(
            select(Department.id).where(Department.parent_id == department_id).limit(1)
        )
        return result.first() is not None

    async def is_descendant_of(self, candidate_id: int, ancestor_id: int) -> bool:
        """Return True if `candidate_id` is in the subtree rooted at `ancestor_id`."""
        if candidate_id == ancestor_id:
            return True

        descendants = (
            select(Department.id)
            .where(Department.id == ancestor_id)
            .cte(name="descendants", recursive=True)
        )
        descendants = descendants.union_all(
            select(Department.id).where(Department.parent_id == descendants.c.id)
        )
        result = await self.session.execute(
            select(descendants.c.id).where(descendants.c.id == candidate_id)
        )
        return result.first() is not None

    async def fetch_subtree(
        self, root_id: int, max_depth: int
    ) -> list[tuple[Department, int]]:
        """
        Return root and all descendants up to `max_depth` (root has level 0).
        max_depth=0 returns just the root.
        """
        base = (
            select(Department, literal(0).label("level"))
            .where(Department.id == root_id)
            .cte(name="subtree", recursive=True)
        )
        base_alias = base.alias("st")
        child = (
            select(Department, (base_alias.c.level + 1).label("level"))
            .join(base_alias, Department.parent_id == base_alias.c.id)
            .where(base_alias.c.level < max_depth)
        )
        subtree_cte = base.union_all(child)

        result = await self.session.execute(
            select(Department, subtree_cte.c.level)
            .join(subtree_cte, Department.id == subtree_cte.c.id)
            .order_by(subtree_cte.c.level, Department.id)
        )
        return list(result.all())

    async def create(
        self, *, name: str, parent_id: int | None
    ) -> Department:
        department = Department(name=name, parent_id=parent_id)
        self.session.add(department)
        await self.session.flush()
        await self.session.refresh(department)
        return department

    async def update_fields(
        self,
        department: Department,
        *,
        name: str | None = None,
        parent_id: int | None | type(...) = ...,
    ) -> Department:
        if name is not None:
            department.name = name
        if parent_id is not ...:
            department.parent_id = parent_id
        await self.session.flush()
        await self.session.refresh(department)
        return department

    async def delete(self, department: Department) -> None:
        await self.session.delete(department)
        await self.session.flush()

    async def reassign_employees(
        self, from_department_id: int, to_department_id: int
    ) -> int:
        from app.models.employee import Employee

        result = await self.session.execute(
            update(Employee)
            .where(Employee.department_id == from_department_id)
            .values(department_id=to_department_id)
        )
        return result.rowcount or 0
