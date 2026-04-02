import re

import pytest
from sqlalchemy import select

from app.config import settings
from app.main import app
from app.models.user_session import UserSession
from app.services.user_auth_service import ensure_identity_seeded


@pytest.mark.asyncio
async def test_auth_login_sets_cookie_and_returns_user(app_client_no_admin_token):
    resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'Admin123456'},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body['code'] == 0
    assert body['data']['authenticated'] is True
    assert body['data']['user']['username'] == 'admin'
    assert body['data']['user']['display_name']
    assert body['data']['user']['roles'][0]['name'] == '管理员'
    assert 'user.view' in body['data']['user']['permission_codes']
    assert body['data']['expires_at'].endswith('Z')
    assert 'set-cookie' in resp.headers


@pytest.mark.asyncio
async def test_auth_login_persists_hashed_user_session(app_client_no_admin_token, db_session):
    resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'Admin123456'},
    )

    raw_session_token = resp.cookies.get(settings.user_session_cookie_name)
    assert raw_session_token

    result = await db_session.execute(select(UserSession).order_by(UserSession.id.desc()))
    active_session = result.scalar_one()

    assert active_session.session_token_hash != raw_session_token
    assert re.fullmatch(r'[0-9a-f]{64}', active_session.session_token_hash)


@pytest.mark.asyncio
async def test_auth_login_revokes_previous_active_session_of_same_user(app_client_no_admin_token, db_session):
    first_resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'Admin123456'},
    )
    assert first_resp.status_code == 200
    first_token = first_resp.cookies.get(settings.user_session_cookie_name)
    assert first_token

    second_resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'Admin123456'},
    )
    assert second_resp.status_code == 200
    second_token = second_resp.cookies.get(settings.user_session_cookie_name)
    assert second_token
    assert second_token != first_token

    sessions = (
        await db_session.execute(select(UserSession).where(UserSession.user_id == 1).order_by(UserSession.id.asc()))
    ).scalars().all()
    assert len(sessions) == 2
    assert sessions[0].revoked_at is not None
    assert sessions[1].revoked_at is None

    app_client_no_admin_token.cookies.set(settings.user_session_cookie_name, first_token)
    old_session_resp = await app_client_no_admin_token.get('/api/auth/session')
    assert old_session_resp.status_code == 200
    assert old_session_resp.json()['data']['authenticated'] is False


@pytest.mark.asyncio
async def test_auth_session_returns_false_without_cookie(app_client_no_admin_token):
    resp = await app_client_no_admin_token.get('/api/auth/session')

    assert resp.status_code == 200
    assert resp.json()['data']['authenticated'] is False


@pytest.mark.asyncio
async def test_auth_logout_clears_access(app_client):
    logout_resp = await app_client.post('/api/auth/logout')
    assert logout_resp.status_code == 200

    protected_resp = await app_client.get('/api/admin/sync/schedule')
    assert protected_resp.status_code == 401
    assert protected_resp.json()['detail'] == 'User session is invalid or expired.'


@pytest.mark.asyncio
async def test_auth_session_returns_authenticated_state_after_login(app_client):
    resp = await app_client.get('/api/auth/session')

    assert resp.status_code == 200
    body = resp.json()
    assert body['data']['authenticated'] is True
    assert body['data']['user']['username'] == 'admin'
    assert 'user.view' in body['data']['user']['permission_codes']
    assert body['data']['expires_at'].endswith('Z')


@pytest.mark.asyncio
async def test_auth_login_rejects_invalid_password(app_client_no_admin_token):
    resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'wrong-password'},
    )

    assert resp.status_code == 401
    body = resp.json()
    assert body['code'] != 0
    assert body['message']


@pytest.mark.asyncio
async def test_auth_login_rejects_disabled_user(app_client_no_admin_token):
    login_resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'Admin123456'},
    )
    assert login_resp.status_code == 200

    role_resp = await app_client_no_admin_token.post(
        '/api/admin/roles',
        json={
            'code': 'planner',
            'name': '排产员',
            'description': '用于测试停用用户登录',
            'is_active': True,
        },
    )
    assert role_resp.status_code == 200
    assert role_resp.json()['code'] == 0

    create_resp = await app_client_no_admin_token.post(
        '/api/admin/users',
        json={
            'username': 'disabled-user',
            'display_name': '停用用户',
            'password': 'Disabled123456',
            'role_codes': ['planner'],
            'is_active': False,
        },
    )
    assert create_resp.status_code == 200
    assert create_resp.json()['code'] == 0

    logout_resp = await app_client_no_admin_token.post('/api/auth/logout')
    assert logout_resp.status_code == 200

    disabled_login_resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'disabled-user', 'password': 'Disabled123456'},
    )
    assert disabled_login_resp.status_code == 403
    assert disabled_login_resp.json()['message'] == '当前用户已停用'


@pytest.mark.asyncio
async def test_auth_session_turns_unauthenticated_after_user_is_disabled(app_client, app_client_no_admin_token, db_session):
    role_resp = await app_client.post(
        '/api/admin/roles',
        json={
            'code': 'session-planner',
            'name': '会话排产员',
            'description': '用于测试停用用户后的会话失效',
            'is_active': True,
        },
    )
    assert role_resp.status_code == 200
    assert role_resp.json()['code'] == 0

    create_resp = await app_client.post(
        '/api/admin/users',
        json={
            'username': 'session-disabled-user',
            'display_name': '会话停用用户',
            'password': 'SessionDisabled123456',
            'role_codes': ['session-planner'],
            'is_active': True,
        },
    )
    assert create_resp.status_code == 200
    assert create_resp.json()['code'] == 0
    user_id = create_resp.json()['data']['id']

    login_resp = await app_client_no_admin_token.post(
        '/api/auth/login',
        json={'username': 'session-disabled-user', 'password': 'SessionDisabled123456'},
    )
    assert login_resp.status_code == 200

    before_disable_session_resp = await app_client_no_admin_token.get('/api/auth/session')
    assert before_disable_session_resp.status_code == 200
    assert before_disable_session_resp.json()['data']['authenticated'] is True
    assert before_disable_session_resp.json()['data']['user']['username'] == 'session-disabled-user'

    disable_resp = await app_client.patch(
        f'/api/admin/users/{user_id}/status',
        json={'is_active': False},
    )
    assert disable_resp.status_code == 200
    assert disable_resp.json()['code'] == 0
    assert disable_resp.json()['data']['is_active'] is False

    after_disable_session_resp = await app_client_no_admin_token.get('/api/auth/session')
    assert after_disable_session_resp.status_code == 200
    assert after_disable_session_resp.json()['data']['authenticated'] is False
    assert after_disable_session_resp.json()['data']['user'] is None

    disabled_user_sessions = (
        await db_session.execute(select(UserSession).where(UserSession.user_id == user_id).order_by(UserSession.id.asc()))
    ).scalars().all()
    assert disabled_user_sessions
    assert all(item.revoked_at is not None for item in disabled_user_sessions)

    protected_resp = await app_client_no_admin_token.get('/api/admin/users')
    assert protected_resp.status_code == 401
    assert protected_resp.json()['detail'] == 'User session is invalid or expired.'


@pytest.mark.asyncio
async def test_identity_seed_requires_explicit_bootstrap_password(db_session):
    original_password = settings.bootstrap_admin_password
    original_username = settings.bootstrap_admin_username
    original_display_name = settings.bootstrap_admin_display_name
    try:
        settings.bootstrap_admin_password = ''
        settings.bootstrap_admin_username = 'admin'
        settings.bootstrap_admin_display_name = '系统管理员'

        with pytest.raises(RuntimeError, match='BOOTSTRAP_ADMIN_PASSWORD'):
            await ensure_identity_seeded(db_session)
    finally:
        settings.bootstrap_admin_password = original_password
        settings.bootstrap_admin_username = original_username
        settings.bootstrap_admin_display_name = original_display_name


def test_openapi_login_route_includes_error_responses():
    schema = app.openapi()
    responses = schema['paths']['/api/auth/login']['post']['responses']

    assert '401' in responses
    assert '403' in responses
    assert responses['401']['content']['application/json']['example']['message'] == '账号或密码错误'
    assert responses['403']['content']['application/json']['example']['message'] == '当前用户已停用'
