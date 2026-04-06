import pytest
from sqlalchemy import select

from app.models.user_session import UserSession


async def _create_role(app_client, code: str = "planner", name: str = "排产员"):
    return await app_client.post(
        "/api/admin/roles",
        json={
            "code": code,
            "name": name,
            "description": "用于测试的自定义角色",
            "is_active": True,
        },
    )


@pytest.mark.asyncio
async def test_admin_user_list_contains_bootstrap_admin(app_client):
    resp = await app_client.get("/api/admin/users")

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert len(body["data"]["items"]) == 1
    assert body["data"]["items"][0]["username"] == "admin"
    assert body["data"]["items"][0]["roles"][0]["code"] == "admin"


@pytest.mark.asyncio
async def test_admin_can_create_user_and_query_detail(app_client):
    role_resp = await _create_role(app_client)
    assert role_resp.status_code == 200
    assert role_resp.json()["code"] == 0

    create_resp = await app_client.post(
        "/api/admin/users",
        json={
            "username": "planner",
            "display_name": "排产管理员",
            "password": "Planner123456",
            "role_codes": ["planner"],
            "is_active": True,
        },
    )

    assert create_resp.status_code == 200
    create_body = create_resp.json()
    assert create_body["code"] == 0
    assert create_body["data"]["username"] == "planner"
    assert create_body["data"]["roles"][0]["code"] == "planner"

    user_id = create_body["data"]["id"]
    detail_resp = await app_client.get(f"/api/admin/users/{user_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["data"]["display_name"] == "排产管理员"


@pytest.mark.asyncio
async def test_admin_create_user_requires_explicit_role_codes(app_client):
    resp = await app_client.post(
        "/api/admin/users",
        json={
            "username": "no-role-user",
            "display_name": "未分配角色用户",
            "password": "NoRole123456",
            "role_codes": [],
            "is_active": True,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] != 0
    assert "至少保留一个角色" in body["message"]


@pytest.mark.asyncio
async def test_admin_cannot_assign_inactive_role_when_creating_or_updating_user(app_client):
    role_resp = await _create_role(app_client, code="inactive-role", name="停用角色")
    assert role_resp.status_code == 200
    role_id = role_resp.json()["data"]["id"]

    disable_resp = await app_client.patch(f"/api/admin/roles/{role_id}/status", json={"is_active": False})
    assert disable_resp.status_code == 200
    assert disable_resp.json()["data"]["is_active"] is False

    create_resp = await app_client.post(
        "/api/admin/users",
        json={
            "username": "inactive-role-user",
            "display_name": "停用角色用户",
            "password": "Inactive123456",
            "role_codes": ["inactive-role"],
            "is_active": True,
        },
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["code"] != 0
    assert "角色已停用" in create_resp.json()["message"]

    planner_role_resp = await _create_role(app_client, code="planner-active", name="有效角色")
    assert planner_role_resp.status_code == 200
    create_active_user_resp = await app_client.post(
        "/api/admin/users",
        json={
            "username": "active-role-user",
            "display_name": "有效角色用户",
            "password": "Active123456",
            "role_codes": ["planner-active"],
            "is_active": True,
        },
    )
    assert create_active_user_resp.status_code == 200
    assert create_active_user_resp.json()["code"] == 0
    user_id = create_active_user_resp.json()["data"]["id"]

    update_resp = await app_client.put(
        f"/api/admin/users/{user_id}/roles",
        json={"role_codes": ["inactive-role"]},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["code"] != 0
    assert "角色已停用" in update_resp.json()["message"]


@pytest.mark.asyncio
async def test_admin_user_list_supports_filters_and_pagination(app_client):
    role_resp = await _create_role(app_client)
    assert role_resp.json()["code"] == 0

    for index in range(3):
        create_resp = await app_client.post(
            "/api/admin/users",
            json={
                "username": f"planner{index}",
                "display_name": f"计划员{index}",
                "password": "Planner123456",
                "role_codes": ["planner"],
                "is_active": index != 2,
            },
        )
        assert create_resp.json()["code"] == 0

    resp = await app_client.get(
        "/api/admin/users",
        params={"keyword": "plan", "role_code": "planner", "page_no": 1, "page_size": 2},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 3
    assert len(body["data"]["items"]) == 2

    inactive_resp = await app_client.get("/api/admin/users", params={"is_active": False, "role_code": "planner"})
    assert inactive_resp.status_code == 200
    inactive_body = inactive_resp.json()
    assert inactive_body["data"]["total"] == 1
    assert inactive_body["data"]["items"][0]["username"] == "planner2"


@pytest.mark.asyncio
async def test_admin_can_update_user_profile_status_password_and_roles(app_client):
    role_resp = await _create_role(app_client)
    assert role_resp.json()["code"] == 0

    create_resp = await app_client.post(
        "/api/admin/users",
        json={
            "username": "ops1",
            "display_name": "运营管理员",
            "password": "Ops123456",
            "role_codes": ["planner"],
            "is_active": True,
        },
    )
    user_id = create_resp.json()["data"]["id"]

    update_resp = await app_client.put(
        f"/api/admin/users/{user_id}",
        json={"username": "ops-updated", "display_name": "运营负责人"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["username"] == "ops-updated"

    disable_resp = await app_client.patch(f"/api/admin/users/{user_id}/status", json={"is_active": False})
    assert disable_resp.status_code == 200
    assert disable_resp.json()["data"]["is_active"] is False

    reset_resp = await app_client.post(
        f"/api/admin/users/{user_id}/reset-password",
        json={"new_password": "Reset123456"},
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["code"] == 0

    role_update_resp = await app_client.put(
        f"/api/admin/users/{user_id}/roles",
        json={"role_codes": ["admin", "planner"]},
    )
    assert role_update_resp.status_code == 200
    assert {item["code"] for item in role_update_resp.json()["data"]["roles"]} == {"admin", "planner"}


@pytest.mark.asyncio
async def test_admin_reset_password_revokes_existing_user_sessions(app_client, app_client_no_admin_token, db_session):
    role_resp = await _create_role(app_client, code="session-role", name="会话角色")
    assert role_resp.status_code == 200
    assert role_resp.json()["code"] == 0

    create_resp = await app_client.post(
        "/api/admin/users",
        json={
            "username": "session-reset-user",
            "display_name": "密码重置用户",
            "password": "BeforeReset123456",
            "role_codes": ["session-role"],
            "is_active": True,
        },
    )
    assert create_resp.status_code == 200
    user_id = create_resp.json()["data"]["id"]

    login_resp = await app_client_no_admin_token.post(
        "/api/auth/login",
        json={"username": "session-reset-user", "password": "BeforeReset123456"},
    )
    assert login_resp.status_code == 200

    before_reset_session = await app_client_no_admin_token.get("/api/auth/session")
    assert before_reset_session.status_code == 200
    assert before_reset_session.json()["data"]["authenticated"] is True

    reset_resp = await app_client.post(
        f"/api/admin/users/{user_id}/reset-password",
        json={"new_password": "AfterReset123456"},
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["code"] == 0

    sessions = (
        (
            await db_session.execute(
                select(UserSession).where(UserSession.user_id == user_id).order_by(UserSession.id.asc())
            )
        )
        .scalars()
        .all()
    )
    assert sessions
    assert all(item.revoked_at is not None for item in sessions)

    after_reset_session = await app_client_no_admin_token.get("/api/auth/session")
    assert after_reset_session.status_code == 200
    assert after_reset_session.json()["data"]["authenticated"] is False

    protected_resp = await app_client_no_admin_token.get("/api/admin/users")
    assert protected_resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_cannot_disable_current_user(app_client):
    resp = await app_client.patch("/api/admin/users/1/status", json={"is_active": False})

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] != 0
    assert "不能停用当前登录用户" in body["message"]


@pytest.mark.asyncio
async def test_admin_cannot_remove_own_admin_role(app_client):
    role_resp = await _create_role(app_client)
    assert role_resp.json()["code"] == 0

    resp = await app_client.put("/api/admin/users/1/roles", json={"role_codes": ["planner"]})

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] != 0
    assert "不能移除当前登录用户的管理员角色" in body["message"]


@pytest.mark.asyncio
async def test_role_crud_and_delete_guards(app_client):
    list_resp = await app_client.get("/api/admin/roles")
    assert list_resp.status_code == 200
    list_body = list_resp.json()
    assert list_body["code"] == 0
    assert list_body["data"]["items"][0]["code"] == "admin"
    assert list_body["data"]["items"][0]["permission_count"] > 0

    create_role_resp = await _create_role(app_client, code="ops", name="运营角色")
    assert create_role_resp.status_code == 200
    create_role_body = create_role_resp.json()
    assert create_role_body["code"] == 0
    role_id = create_role_body["data"]["id"]

    detail_resp = await app_client.get(f"/api/admin/roles/{role_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["data"]["code"] == "ops"

    update_resp = await app_client.put(
        f"/api/admin/roles/{role_id}",
        json={"name": "运营主管", "description": "负责运营维护"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["name"] == "运营主管"

    disable_resp = await app_client.patch(f"/api/admin/roles/{role_id}/status", json={"is_active": False})
    assert disable_resp.status_code == 200
    assert disable_resp.json()["data"]["is_active"] is False

    enable_resp = await app_client.patch(f"/api/admin/roles/{role_id}/status", json={"is_active": True})
    assert enable_resp.status_code == 200
    assert enable_resp.json()["data"]["is_active"] is True

    bind_user_resp = await app_client.post(
        "/api/admin/users",
        json={
            "username": "ops-role-user",
            "display_name": "运营值班",
            "password": "Role123456",
            "role_codes": ["ops"],
            "is_active": True,
        },
    )
    assert bind_user_resp.json()["code"] == 0

    delete_bound_resp = await app_client.delete(f"/api/admin/roles/{role_id}")
    assert delete_bound_resp.status_code == 200
    assert delete_bound_resp.json()["code"] != 0
    assert "当前角色仍有用户绑定" in delete_bound_resp.json()["message"]

    admin_role_id = list_body["data"]["items"][0]["id"]
    delete_admin_resp = await app_client.delete(f"/api/admin/roles/{admin_role_id}")
    assert delete_admin_resp.status_code == 200
    assert delete_admin_resp.json()["code"] != 0
    assert "系统内置角色不允许删除" in delete_admin_resp.json()["message"]


@pytest.mark.asyncio
async def test_admin_can_update_custom_role_permissions(app_client):
    role_resp = await _create_role(app_client, code="rbac-viewer", name="RBAC Viewer")
    assert role_resp.status_code == 200
    role_id = role_resp.json()["data"]["id"]

    update_resp = await app_client.put(
        f"/api/admin/roles/{role_id}/permissions",
        json={"permission_codes": ["user.view"]},
    )
    assert update_resp.status_code == 200
    update_body = update_resp.json()
    assert update_body["code"] == 0
    assert update_body["data"]["permission_count"] == 1
    assert [item["code"] for item in update_body["data"]["permissions"]] == ["user.view"]


@pytest.mark.asyncio
async def test_admin_cannot_update_system_role_permissions(app_client):
    roles_resp = await app_client.get("/api/admin/roles")
    admin_role_id = roles_resp.json()["data"]["items"][0]["id"]

    resp = await app_client.put(
        f"/api/admin/roles/{admin_role_id}/permissions",
        json={"permission_codes": ["user.view"]},
    )
    assert resp.status_code == 200
    assert resp.json()["code"] != 0
    assert "系统内置角色权限不允许修改" in resp.json()["message"]


@pytest.mark.asyncio
async def test_permission_placeholder_endpoints(app_client):
    permissions_resp = await app_client.get("/api/admin/permissions")
    assert permissions_resp.status_code == 200
    permissions_body = permissions_resp.json()
    assert permissions_body["code"] == 0
    assert any(item["code"] == "user.view" for item in permissions_body["data"]["items"])

    roles_resp = await app_client.get("/api/admin/roles")
    admin_role_id = roles_resp.json()["data"]["items"][0]["id"]
    role_permissions_resp = await app_client.get(f"/api/admin/roles/{admin_role_id}/permissions")
    assert role_permissions_resp.status_code == 200
    role_permissions_body = role_permissions_resp.json()
    assert role_permissions_body["code"] == 0
    assert role_permissions_body["data"]["role_code"] == "admin"
    assert len(role_permissions_body["data"]["items"]) > 0


@pytest.mark.asyncio
async def test_permission_matrix_endpoint_returns_roles_permissions_and_bindings(app_client):
    role_resp = await _create_role(app_client, code="matrix-role", name="Matrix Role")
    assert role_resp.status_code == 200
    role_id = role_resp.json()["data"]["id"]

    update_resp = await app_client.put(
        f"/api/admin/roles/{role_id}/permissions",
        json={"permission_codes": ["user.view", "role.view"]},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["code"] == 0

    matrix_resp = await app_client.get("/api/admin/permission-matrix")
    assert matrix_resp.status_code == 200
    matrix_body = matrix_resp.json()
    assert matrix_body["code"] == 0

    role_codes = {item["code"] for item in matrix_body["data"]["roles"]}
    assert {"admin", "matrix-role"}.issubset(role_codes)

    user_view_item = next(item for item in matrix_body["data"]["permissions"] if item["code"] == "user.view")
    role_view_item = next(item for item in matrix_body["data"]["permissions"] if item["code"] == "role.view")
    assert any(
        binding["role_code"] == "matrix-role" and binding["assigned"] is True
        for binding in user_view_item["role_bindings"]
    )
    assert any(
        binding["role_code"] == "matrix-role" and binding["assigned"] is True
        for binding in role_view_item["role_bindings"]
    )


@pytest.mark.asyncio
async def test_permission_linkage_endpoint_returns_route_bindings(app_client):
    linkage_resp = await app_client.get("/api/admin/permission-linkage")
    assert linkage_resp.status_code == 200
    linkage_body = linkage_resp.json()
    assert linkage_body["code"] == 0

    user_view_item = next(item for item in linkage_body["data"]["items"] if item["code"] == "user.view")
    permission_view_item = next(item for item in linkage_body["data"]["items"] if item["code"] == "permission.view")
    role_view_item = next(item for item in linkage_body["data"]["items"] if item["code"] == "role.view")
    schedule_view_item = next(item for item in linkage_body["data"]["items"] if item["code"] == "schedule.view")
    issue_view_item = next(item for item in linkage_body["data"]["items"] if item["code"] == "issue.view")

    assert any(
        route["path"] == "/api/admin/users" and "GET" in route["methods"] for route in user_view_item["linked_routes"]
    )
    assert any(
        route["path"] == "/api/admin/permission-linkage" and "GET" in route["methods"]
        for route in permission_view_item["linked_routes"]
    )
    assert any(
        route["path"] == "/api/admin/permission-matrix" and "GET" in route["methods"]
        for route in permission_view_item["linked_routes"]
    )
    assert any(
        route["path"] == "/api/admin/permission-matrix" and "GET" in route["methods"]
        for route in role_view_item["linked_routes"]
    )
    assert any(
        route["path"] == "/api/schedules" and "GET" in route["methods"] for route in schedule_view_item["linked_routes"]
    )
    assert any(
        route["path"] == "/api/dashboard/overview" and "GET" in route["methods"]
        for route in schedule_view_item["linked_routes"]
    )
    assert any(
        route["path"] == "/api/issues" and "GET" in route["methods"] for route in issue_view_item["linked_routes"]
    )
