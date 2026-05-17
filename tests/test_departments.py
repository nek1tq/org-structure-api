import pytest


@pytest.mark.asyncio
async def test_create_root_department(client):
    response = await client.post("/departments/", json={"name": "Engineering"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Engineering"
    assert body["parent_id"] is None
    assert body["id"] > 0
    assert "created_at" in body


@pytest.mark.asyncio
async def test_create_child_department(client):
    root = (await client.post("/departments/", json={"name": "Engineering"})).json()
    response = await client.post(
        "/departments/", json={"name": "Backend", "parent_id": root["id"]}
    )
    assert response.status_code == 201
    assert response.json()["parent_id"] == root["id"]


@pytest.mark.asyncio
async def test_create_in_nonexistent_parent_returns_404(client):
    response = await client.post(
        "/departments/", json={"name": "Backend", "parent_id": 9999}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_name_under_same_parent_returns_409(client):
    await client.post("/departments/", json={"name": "Engineering"})
    response = await client.post("/departments/", json={"name": "Engineering"})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_same_name_under_different_parents_is_allowed(client):
    e = (await client.post("/departments/", json={"name": "Engineering"})).json()
    s = (await client.post("/departments/", json={"name": "Sales"})).json()
    r1 = await client.post(
        "/departments/", json={"name": "Operations", "parent_id": e["id"]}
    )
    r2 = await client.post(
        "/departments/", json={"name": "Operations", "parent_id": s["id"]}
    )
    assert r1.status_code == 201
    assert r2.status_code == 201


@pytest.mark.asyncio
async def test_name_is_trimmed(client):
    response = await client.post("/departments/", json={"name": "  Engineering  "})
    assert response.status_code == 201
    assert response.json()["name"] == "Engineering"


@pytest.mark.asyncio
async def test_empty_name_rejected(client):
    response = await client.post("/departments/", json={"name": "   "})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_department_tree(client):
    eng = (await client.post("/departments/", json={"name": "Engineering"})).json()
    backend = (
        await client.post(
            "/departments/", json={"name": "Backend", "parent_id": eng["id"]}
        )
    ).json()
    await client.post(
        "/departments/", json={"name": "Python", "parent_id": backend["id"]}
    )

    response = await client.get(f"/departments/{eng['id']}?depth=2")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Engineering"
    assert len(body["children"]) == 1
    assert body["children"][0]["name"] == "Backend"
    assert len(body["children"][0]["children"]) == 1
    assert body["children"][0]["children"][0]["name"] == "Python"


@pytest.mark.asyncio
async def test_get_tree_respects_depth_limit(client):
    eng = (await client.post("/departments/", json={"name": "Engineering"})).json()
    backend = (
        await client.post(
            "/departments/", json={"name": "Backend", "parent_id": eng["id"]}
        )
    ).json()
    await client.post(
        "/departments/", json={"name": "Python", "parent_id": backend["id"]}
    )

    response = await client.get(f"/departments/{eng['id']}?depth=1")
    body = response.json()
    assert len(body["children"]) == 1
    assert body["children"][0]["children"] == []


@pytest.mark.asyncio
async def test_get_tree_excludes_employees_when_disabled(client):
    eng = (await client.post("/departments/", json={"name": "Engineering"})).json()
    await client.post(
        f"/departments/{eng['id']}/employees/",
        json={"full_name": "Alice", "position": "Engineer"},
    )

    response = await client.get(
        f"/departments/{eng['id']}?include_employees=false"
    )
    assert response.json()["employees"] == []


@pytest.mark.asyncio
async def test_rename_department(client):
    e = (await client.post("/departments/", json={"name": "Engineering"})).json()
    response = await client.patch(
        f"/departments/{e['id']}", json={"name": "R&D"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "R&D"


@pytest.mark.asyncio
async def test_move_department_cycle_rejected(client):
    a = (await client.post("/departments/", json={"name": "A"})).json()
    b = (await client.post("/departments/", json={"name": "B", "parent_id": a["id"]})).json()
    c = (await client.post("/departments/", json={"name": "C", "parent_id": b["id"]})).json()

    response = await client.patch(
        f"/departments/{a['id']}", json={"parent_id": c["id"]}
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_self_parent_rejected(client):
    a = (await client.post("/departments/", json={"name": "A"})).json()
    response = await client.patch(
        f"/departments/{a['id']}", json={"parent_id": a["id"]}
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_move_to_root(client):
    a = (await client.post("/departments/", json={"name": "A"})).json()
    b = (
        await client.post("/departments/", json={"name": "B", "parent_id": a["id"]})
    ).json()
    response = await client.patch(
        f"/departments/{b['id']}", json={"parent_id": None}
    )
    assert response.status_code == 200
    assert response.json()["parent_id"] is None


@pytest.mark.asyncio
async def test_cascade_delete(client):
    a = (await client.post("/departments/", json={"name": "A"})).json()
    b = (
        await client.post("/departments/", json={"name": "B", "parent_id": a["id"]})
    ).json()
    await client.post(
        f"/departments/{b['id']}/employees/",
        json={"full_name": "Alice", "position": "Engineer"},
    )

    response = await client.delete(f"/departments/{a['id']}?mode=cascade")
    assert response.status_code == 204

    assert (await client.get(f"/departments/{a['id']}")).status_code == 404
    assert (await client.get(f"/departments/{b['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_reassign_delete(client):
    a = (await client.post("/departments/", json={"name": "A"})).json()
    target = (await client.post("/departments/", json={"name": "Target"})).json()
    emp = (
        await client.post(
            f"/departments/{a['id']}/employees/",
            json={"full_name": "Alice", "position": "Engineer"},
        )
    ).json()

    response = await client.delete(
        f"/departments/{a['id']}?mode=reassign&reassign_to_department_id={target['id']}"
    )
    assert response.status_code == 204

    tree = (await client.get(f"/departments/{target['id']}")).json()
    assert any(e["id"] == emp["id"] for e in tree["employees"])


@pytest.mark.asyncio
async def test_reassign_requires_target(client):
    a = (await client.post("/departments/", json={"name": "A"})).json()
    response = await client.delete(f"/departments/{a['id']}?mode=reassign")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_reassign_rejected_when_has_children(client):
    a = (await client.post("/departments/", json={"name": "A"})).json()
    await client.post("/departments/", json={"name": "B", "parent_id": a["id"]})
    target = (await client.post("/departments/", json={"name": "Target"})).json()

    response = await client.delete(
        f"/departments/{a['id']}?mode=reassign&reassign_to_department_id={target['id']}"
    )
    assert response.status_code == 409
