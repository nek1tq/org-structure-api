from fastapi import APIRouter, Path, Query, Response, status

from app.api.deps import DepartmentServiceDep, EmployeeServiceDep
from app.core.config import get_settings
from app.schemas.department import (
    DeleteMode,
    DepartmentCreate,
    DepartmentResponse,
    DepartmentTree,
    DepartmentUpdate,
    EmployeeSort,
)
from app.schemas.employee import EmployeeCreate, EmployeeResponse

router = APIRouter(prefix="/departments", tags=["departments"])
settings = get_settings()


@router.post(
    "/",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a department",
)
async def create_department(
    payload: DepartmentCreate,
    service: DepartmentServiceDep,
) -> DepartmentResponse:
    department = await service.create(name=payload.name, parent_id=payload.parent_id)
    return DepartmentResponse.model_validate(department)


@router.get(
    "/{department_id}",
    response_model=DepartmentTree,
    summary="Get department details with employees and nested subtree",
)
async def get_department(
    service: DepartmentServiceDep,
    department_id: int = Path(..., ge=1),
    depth: int = Query(
        default=settings.default_tree_depth,
        ge=0,
        le=settings.max_tree_depth,
        description="Subtree depth (0 = just this department, max 5)",
    ),
    include_employees: bool = Query(default=True),
    employee_sort: EmployeeSort = Query(default=EmployeeSort.created_at),
) -> DepartmentTree:
    return await service.get_tree(
        department_id,
        depth=depth,
        include_employees=include_employees,
        employee_sort=employee_sort,
    )


@router.patch(
    "/{department_id}",
    response_model=DepartmentResponse,
    summary="Rename or move a department",
)
async def update_department(
    payload: DepartmentUpdate,
    service: DepartmentServiceDep,
    department_id: int = Path(..., ge=1),
) -> DepartmentResponse:
    parent_id_provided = "parent_id" in payload.model_fields_set
    department = await service.update(
        department_id,
        name=payload.name,
        parent_id_provided=parent_id_provided,
        parent_id=payload.parent_id,
    )
    return DepartmentResponse.model_validate(department)


@router.delete(
    "/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a department (cascade or reassign employees)",
)
async def delete_department(
    service: DepartmentServiceDep,
    department_id: int = Path(..., ge=1),
    mode: DeleteMode = Query(..., description="cascade or reassign"),
    reassign_to_department_id: int | None = Query(default=None, ge=1),
) -> Response:
    await service.delete(
        department_id,
        mode=mode,
        reassign_to_department_id=reassign_to_department_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{department_id}/employees/",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an employee in a department",
)
async def create_employee(
    payload: EmployeeCreate,
    service: EmployeeServiceDep,
    department_id: int = Path(..., ge=1),
) -> EmployeeResponse:
    employee = await service.create_in_department(
        department_id,
        full_name=payload.full_name,
        position=payload.position,
        hired_at=payload.hired_at,
    )
    return EmployeeResponse.model_validate(employee)
