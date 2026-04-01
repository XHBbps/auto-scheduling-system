import pytest
from fastapi.routing import APIRoute

from app.main import app


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'path',
    [
        '/api/exports/machine-schedules',
        '/api/exports/part-schedules',
        '/api/data/sales-plan-orders',
        '/api/data/bom-relations',
        '/api/data/production-orders',
        '/api/data/machine-cycle-history',
        '/api/admin/users',
    ],
)
async def test_protected_routes_require_admin_role(app_client_no_admin_token, path):
    resp = await app_client_no_admin_token.get(path)
    assert resp.status_code == 401
    assert resp.json()['detail'] == 'User session is invalid or expired.'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'path',
    [
        '/api/dashboard/overview',
        '/api/schedules',
        '/api/schedules/options/product-series',
        '/api/part-schedules',
        '/api/part-schedules/options/assembly-names',
        '/api/issues',
        '/api/issues/options/issue-types',
    ],
)
async def test_query_routes_require_authenticated_session(app_client_no_admin_token, path):
    resp = await app_client_no_admin_token.get(path)
    assert resp.status_code == 401
    assert resp.json()['detail'] == 'User session is invalid or expired.'


@pytest.mark.asyncio
async def test_formal_auth_session_passes_admin_protection(app_client_no_admin_token):
    login_resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'Admin123456'},
    )
    assert login_resp.status_code == 200

    protected_resp = await app_client_no_admin_token.get('/api/admin/users')
    assert protected_resp.status_code == 200
    assert protected_resp.json()['code'] == 0


@pytest.mark.asyncio
async def test_non_admin_login_is_authenticated_but_blocked_from_admin_routes(app_client_no_admin_token):
    admin_login_resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'Admin123456'},
    )
    assert admin_login_resp.status_code == 200

    role_resp = await app_client_no_admin_token.post(
        '/api/admin/roles',
        json={
            'code': 'planner',
            'name': '排产员',
            'description': '非管理员边界测试角色',
            'is_active': True,
        },
    )
    assert role_resp.status_code == 200
    assert role_resp.json()['code'] == 0

    user_resp = await app_client_no_admin_token.post(
        '/api/admin/users',
        json={
            'username': 'planner-user',
            'display_name': '排产员用户',
            'password': 'Planner123456',
            'role_codes': ['planner'],
            'is_active': True,
        },
    )
    assert user_resp.status_code == 200
    assert user_resp.json()['code'] == 0

    logout_resp = await app_client_no_admin_token.post('/api/auth/logout')
    assert logout_resp.status_code == 200

    planner_login_resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'planner-user', 'password': 'Planner123456'},
    )
    assert planner_login_resp.status_code == 200
    assert planner_login_resp.json()['data']['user']['roles'][0]['code'] == 'planner'

    session_resp = await app_client_no_admin_token.get('/api/auth/session')
    assert session_resp.status_code == 200
    assert session_resp.json()['data']['authenticated'] is True
    assert session_resp.json()['data']['user']['roles'][0]['code'] == 'planner'

    for path in ('/api/admin/users', '/api/data/sales-plan-orders', '/api/exports/part-schedules'):
        protected_resp = await app_client_no_admin_token.get(path)
        assert protected_resp.status_code == 403
        assert protected_resp.json()['detail'] == 'Current user does not have the required permission.'


@pytest.mark.asyncio
async def test_custom_role_with_schedule_view_permission_can_access_schedule_queries(app_client_no_admin_token):
    admin_login_resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'Admin123456'},
    )
    assert admin_login_resp.status_code == 200

    role_resp = await app_client_no_admin_token.post(
        '/api/admin/roles',
        json={
            'code': 'schedule-viewer',
            'name': 'Schedule Viewer',
            'description': 'Can only view schedule pages',
            'is_active': True,
        },
    )
    assert role_resp.status_code == 200
    role_id = role_resp.json()['data']['id']

    permission_resp = await app_client_no_admin_token.put(
        f'/api/admin/roles/{role_id}/permissions',
        json={'permission_codes': ['schedule.view']},
    )
    assert permission_resp.status_code == 200
    assert permission_resp.json()['code'] == 0

    user_resp = await app_client_no_admin_token.post(
        '/api/admin/users',
        json={
            'username': 'schedule-viewer-1',
            'display_name': 'Schedule Viewer Account',
            'password': 'Viewer123456',
            'role_codes': ['schedule-viewer'],
            'is_active': True,
        },
    )
    assert user_resp.status_code == 200
    assert user_resp.json()['code'] == 0

    logout_resp = await app_client_no_admin_token.post('/api/auth/logout')
    assert logout_resp.status_code == 200

    viewer_login_resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'schedule-viewer-1', 'password': 'Viewer123456'},
    )
    assert viewer_login_resp.status_code == 200
    assert viewer_login_resp.json()['data']['user']['permission_codes'] == ['schedule.view']

    for allowed_path in (
        '/api/dashboard/overview',
        '/api/schedules',
        '/api/schedules/options/product-series',
        '/api/part-schedules',
        '/api/part-schedules/options/assembly-names',
    ):
        allowed_resp = await app_client_no_admin_token.get(allowed_path)
        assert allowed_resp.status_code == 200
        assert allowed_resp.json()['code'] == 0

    forbidden_resp = await app_client_no_admin_token.get('/api/issues')
    assert forbidden_resp.status_code == 403
    assert forbidden_resp.json()['detail'] == 'Current user does not have the required permission.'


@pytest.mark.asyncio
async def test_custom_role_with_issue_view_permission_can_access_issue_queries_only(app_client_no_admin_token):
    admin_login_resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'Admin123456'},
    )
    assert admin_login_resp.status_code == 200

    role_resp = await app_client_no_admin_token.post(
        '/api/admin/roles',
        json={
            'code': 'issue-viewer',
            'name': 'Issue Viewer',
            'description': 'Can only view issue pages',
            'is_active': True,
        },
    )
    assert role_resp.status_code == 200
    role_id = role_resp.json()['data']['id']

    permission_resp = await app_client_no_admin_token.put(
        f'/api/admin/roles/{role_id}/permissions',
        json={'permission_codes': ['issue.view']},
    )
    assert permission_resp.status_code == 200
    assert permission_resp.json()['code'] == 0

    user_resp = await app_client_no_admin_token.post(
        '/api/admin/users',
        json={
            'username': 'issue-viewer-1',
            'display_name': 'Issue Viewer Account',
            'password': 'Viewer123456',
            'role_codes': ['issue-viewer'],
            'is_active': True,
        },
    )
    assert user_resp.status_code == 200
    assert user_resp.json()['code'] == 0

    logout_resp = await app_client_no_admin_token.post('/api/auth/logout')
    assert logout_resp.status_code == 200

    viewer_login_resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'issue-viewer-1', 'password': 'Viewer123456'},
    )
    assert viewer_login_resp.status_code == 200
    assert viewer_login_resp.json()['data']['user']['permission_codes'] == ['issue.view']

    for allowed_path in ('/api/issues', '/api/issues/options/issue-types'):
        allowed_resp = await app_client_no_admin_token.get(allowed_path)
        assert allowed_resp.status_code == 200
        assert allowed_resp.json()['code'] == 0

    forbidden_resp = await app_client_no_admin_token.get('/api/schedules')
    assert forbidden_resp.status_code == 403
    assert forbidden_resp.json()['detail'] == 'Current user does not have the required permission.'


@pytest.mark.asyncio
async def test_custom_role_with_user_view_permission_can_access_user_list_only(app_client, app_client_no_admin_token):
    admin_login_resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'Admin123456'},
    )
    assert admin_login_resp.status_code == 200

    role_resp = await app_client_no_admin_token.post(
        '/api/admin/roles',
        json={
            'code': 'user-viewer',
            'name': 'User Viewer',
            'description': 'Can only view user list',
            'is_active': True,
        },
    )
    assert role_resp.status_code == 200
    role_id = role_resp.json()['data']['id']

    permission_resp = await app_client_no_admin_token.put(
        f'/api/admin/roles/{role_id}/permissions',
        json={'permission_codes': ['user.view']},
    )
    assert permission_resp.status_code == 200
    assert permission_resp.json()['code'] == 0

    user_resp = await app_client_no_admin_token.post(
        '/api/admin/users',
        json={
            'username': 'user-viewer-1',
            'display_name': 'User Viewer Account',
            'password': 'Viewer123456',
            'role_codes': ['user-viewer'],
            'is_active': True,
        },
    )
    assert user_resp.status_code == 200
    assert user_resp.json()['code'] == 0

    logout_resp = await app_client_no_admin_token.post('/api/auth/logout')
    assert logout_resp.status_code == 200

    viewer_login_resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'user-viewer-1', 'password': 'Viewer123456'},
    )
    assert viewer_login_resp.status_code == 200
    assert viewer_login_resp.json()['data']['user']['permission_codes'] == ['user.view']

    allowed_resp = await app_client_no_admin_token.get('/api/admin/users')
    assert allowed_resp.status_code == 200
    assert allowed_resp.json()['code'] == 0

    forbidden_resp = await app_client_no_admin_token.get('/api/admin/roles')
    assert forbidden_resp.status_code == 403
    assert forbidden_resp.json()['detail'] == 'Current user does not have the required permission.'

    matrix_resp = await app_client_no_admin_token.get('/api/admin/permission-matrix')
    assert matrix_resp.status_code == 403
    assert matrix_resp.json()['detail'] == 'Current user does not have the required permission.'

    linkage_resp = await app_client_no_admin_token.get('/api/admin/permission-linkage')
    assert linkage_resp.status_code == 403
    assert linkage_resp.json()['detail'] == 'Current user does not have the required permission.'


@pytest.mark.asyncio
async def test_user_loses_admin_access_immediately_after_admin_role_is_replaced(app_client, app_client_no_admin_token):
    role_resp = await app_client.post(
        '/api/admin/roles',
        json={
            'code': 'role-changed-planner',
            'name': '角色变更排产员',
            'description': '用于测试角色变更后的权限回收',
            'is_active': True,
        },
    )
    assert role_resp.status_code == 200
    assert role_resp.json()['code'] == 0

    create_resp = await app_client.post(
        '/api/admin/users',
        json={
            'username': 'role-changed-admin',
            'display_name': '角色变更管理员',
            'password': 'RoleChanged123456',
            'role_codes': ['admin'],
            'is_active': True,
        },
    )
    assert create_resp.status_code == 200
    assert create_resp.json()['code'] == 0
    user_id = create_resp.json()['data']['id']

    login_resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'role-changed-admin', 'password': 'RoleChanged123456'},
    )
    assert login_resp.status_code == 200
    assert {role['code'] for role in login_resp.json()['data']['user']['roles']} == {'admin'}

    protected_before_resp = await app_client_no_admin_token.get('/api/admin/users')
    assert protected_before_resp.status_code == 200
    assert protected_before_resp.json()['code'] == 0

    remove_roles_resp = await app_client.put(
        f'/api/admin/users/{user_id}/roles',
        json={'role_codes': ['role-changed-planner']},
    )
    assert remove_roles_resp.status_code == 200
    assert remove_roles_resp.json()['code'] == 0
    assert {role['code'] for role in remove_roles_resp.json()['data']['roles']} == {'role-changed-planner'}

    session_resp = await app_client_no_admin_token.get('/api/auth/session')
    assert session_resp.status_code == 200
    assert session_resp.json()['data']['authenticated'] is True
    assert {role['code'] for role in session_resp.json()['data']['user']['roles']} == {'role-changed-planner'}

    protected_after_resp = await app_client_no_admin_token.get('/api/admin/users')
    assert protected_after_resp.status_code == 403
    assert protected_after_resp.json()['detail'] == 'Current user does not have the required permission.'


def test_all_protected_routes_include_permission_dependency():
    protected_prefixes = ('/api/admin/', '/api/data/', '/api/exports/')
    protected_exact_paths = {
        '/api/dashboard/overview',
        '/api/schedules',
        '/api/schedules/options/product-series',
        '/api/schedules/{order_line_id}',
        '/api/part-schedules',
        '/api/part-schedules/options/assembly-names',
        '/api/issues',
        '/api/issues/options/issue-types',
    }
    public_exceptions = {
        '/api/auth/login',
        '/api/auth/session',
        '/api/auth/logout',
    }

    missing_protection: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path in public_exceptions:
            continue
        if not route.path.startswith(protected_prefixes) and route.path not in protected_exact_paths:
            continue

        dependency_calls = [dependency.call for dependency in route.dependant.dependencies]
        if not any(getattr(call, "__permission_dependency__", False) for call in dependency_calls):
            methods = ','.join(sorted(route.methods or []))
            missing_protection.append(f'{methods} {route.path}')

    assert missing_protection == []


def test_openapi_protected_routes_include_401_and_403_responses():
    schema = app.openapi()

    for path in ('/api/admin/users', '/api/schedules', '/api/issues'):
        responses = schema['paths'][path]['get']['responses']
        assert '401' in responses
        assert '403' in responses
        assert responses['401']['content']['application/json']['example']['detail'] == 'User session is invalid or expired.'
        assert responses['403']['content']['application/json']['example']['detail'] == 'Current user does not have the required permission.'


def test_openapi_validation_error_schema_and_query_route_descriptions_are_complete():
    schema = app.openapi()

    validation_error = schema['components']['schemas']['ValidationError']
    http_validation_error = schema['components']['schemas']['HTTPValidationError']
    product_series_operation = schema['paths']['/api/schedules/options/product-series']['get']
    assembly_name_operation = schema['paths']['/api/part-schedules/options/assembly-names']['get']
    issues_operation = schema['paths']['/api/issues']['get']
    issue_type_operation = schema['paths']['/api/issues/options/issue-types']['get']
    machine_cycle_history_operation = schema['paths']['/api/data/machine-cycle-history']['get']
    production_orders_operation = schema['paths']['/api/data/production-orders']['get']
    machine_cycle_baselines_operation = schema['paths']['/api/admin/machine-cycle-baselines']['get']
    assembly_times_operation = schema['paths']['/api/admin/assembly-times']['get']
    part_cycle_baselines_operation = schema['paths']['/api/admin/part-cycle-baselines']['get']

    assert validation_error['description']
    assert validation_error['properties']['loc']['description']
    assert validation_error['properties']['msg']['description']
    assert validation_error['properties']['type']['description']
    assert http_validation_error['description']
    assert http_validation_error['properties']['detail']['description']

    assert '筛选条件下拉选择使用' in product_series_operation['description']
    assert '筛选器使用' in assembly_name_operation['description']
    assert '关联快照字段' in issues_operation['description']
    assert '筛选器下拉选择使用' in issue_type_operation['description']
    assert '基准回溯和周期对比使用' in machine_cycle_history_operation['description']
    assert '排产回溯与历史订单核对使用' in production_orders_operation['description']
    assert '整机主周期' in machine_cycle_baselines_operation['description']
    assert '整机总装时长' in assembly_times_operation['description']
    assert '零件自身周期' in part_cycle_baselines_operation['description']

