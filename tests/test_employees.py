import pytest


@pytest.mark.asyncio
async def test_create_employee(client):
    dept = (await client.post("/departments/", json={"name": "Engineering"})).json()
    response = await client.post(
        f"/departments/{dept['id']}/employees/",
        json={"full_name": "Alice", "position": "Engineer"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["full_name"] == "Alice"
    assert body["position"] == "Engineer"
    assert body["department_id"] == dept["id"]


@pytest.mark.asyncio
async def test_create_employee_with_hired_at(client):
    dept = (await client.post("/departments/", json={"name": "Engineering"})).json()
    response = await client.post(
        f"/departments/{dept['id']}/employees/",
        json={"full_name": "Bob", "position": "Senior", "hired_at": "2024-01-15"},
    )
    assert response.status_code == 201
    assert response.json()["hired_at"] == "2024-01-15"


@pytest.mark.asyncio
async def test_create_employee_in_nonexistent_department(client):
    response = await client.post(
        "/departments/9999/employees/",
        json={"full_name": "Alice", "position": "Engineer"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_employee_empty_name_rejected(client):
    dept = (await client.post("/departments/", json={"name": "Engineering"})).json()
    response = await client.post(
        f"/departments/{dept['id']}/employees/",
        json={"full_name": "   ", "position": "Engineer"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_employees_sorted_by_full_name(client):
    dept = (await client.post("/departments/", json={"name": "Engineering"})).json()
    for name in ["Charlie", "Alice", "Bob"]:
        await client.post(
            f"/departments/{dept['id']}/employees/",
            json={"full_name": name, "position": "Eng"},
        )

    response = await client.get(
        f"/departments/{dept['id']}?employee_sort=full_name"
    )
    names = [e["full_name"] for e in response.json()["employees"]]
    assert names == ["Alice", "Bob", "Charlie"]
