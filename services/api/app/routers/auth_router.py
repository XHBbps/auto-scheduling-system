from __future__ import annotations

import contextlib
import ipaddress
from typing import Any

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import (
    build_auth_session_cookie_kwargs,
    build_auth_session_expiry,
    generate_session_token,
    get_current_user_from_cookie,
    hash_session_token,
    revoke_auth_session,
    serialize_auth_datetime,
)
from app.common.datetime_utils import utc_now
from app.common.response import ApiResponse
from app.config import settings
from app.database import get_session
from app.models.user_session import UserSession
from app.repository.user_account_repo import UserAccountRepo
from app.repository.user_session_repo import UserSessionRepo
from app.schemas.auth_schemas import AuthLoginRequest, AuthSessionInfoResponse
from app.services.user_auth_service import serialize_user_payload, verify_password

_trusted_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
for cidr in settings.trusted_proxy_cidrs:
    with contextlib.suppress(ValueError):
        _trusted_networks.append(ipaddress.ip_network(cidr, strict=False))


def _is_trusted_proxy(ip: str) -> bool:
    """Check if the direct client IP belongs to a trusted proxy network."""
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in net for net in _trusted_networks)
    except ValueError:
        return False


def _get_real_ip(request):
    """Extract real client IP. Only trust proxy headers from known proxy networks."""
    direct_ip = get_remote_address(request) or "127.0.0.1"
    if not _is_trusted_proxy(direct_ip):
        return direct_ip
    forwarded = request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return direct_ip


limiter = Limiter(key_func=_get_real_ip)
router = APIRouter(prefix="/api/auth", tags=["用户认证"])


def _build_session_response(*, user=None, expires_at=None, authenticated: bool) -> dict[str, object]:
    return {
        "authenticated": authenticated,
        "user": serialize_user_payload(user) if user is not None else None,
        "expires_at": serialize_auth_datetime(expires_at),
    }


@router.post(
    "/login",
    summary="账号密码登录",
    description="使用账号密码登录并写入 HttpOnly Cookie；同一用户再次登录时会主动撤销旧会话，仅保留最新登录态。",
    response_model=ApiResponse[AuthSessionInfoResponse],
    responses={
        401: {
            "description": "账号不存在或密码错误。",
            "content": {
                "application/json": {
                    "example": {
                        "code": status.HTTP_401_UNAUTHORIZED,
                        "message": "账号或密码错误",
                        "data": None,
                    }
                }
            },
        },
        403: {
            "description": "用户存在但已停用，禁止登录。",
            "content": {
                "application/json": {
                    "example": {
                        "code": status.HTTP_403_FORBIDDEN,
                        "message": "当前用户已停用",
                        "data": None,
                    }
                }
            },
        },
    },
)
@limiter.limit("5/minute")
async def login(
    request: Request,
    payload: AuthLoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[Any]:
    username = payload.username.strip()
    password = payload.password
    if not username or not password:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return ApiResponse.fail(status.HTTP_401_UNAUTHORIZED, "账号或密码错误")

    user_repo = UserAccountRepo(session)
    user = await user_repo.find_by_username(username, with_roles=True)
    if user is None or not verify_password(password, user.password_hash):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return ApiResponse.fail(status.HTTP_401_UNAUTHORIZED, "账号或密码错误")

    if not user.is_active:
        response.status_code = status.HTTP_403_FORBIDDEN
        return ApiResponse.fail(status.HTTP_403_FORBIDDEN, "当前用户已停用")

    session_token = generate_session_token()
    expires_at = build_auth_session_expiry()
    now = utc_now()
    await UserSessionRepo(session).revoke_active_sessions_for_user(
        user.id,
        revoked_at=now,
        now=now,
    )
    session.add(
        UserSession(
            user_id=user.id,
            session_token_hash=hash_session_token(session_token),
            expires_at=expires_at,
            last_seen_at=now,
        )
    )
    user.last_login_at = now
    await session.commit()

    refreshed_user = await user_repo.get_with_roles(user.id) or user
    response.set_cookie(value=session_token, **build_auth_session_cookie_kwargs())
    return ApiResponse.ok(data=_build_session_response(user=refreshed_user, expires_at=expires_at, authenticated=True))


@router.get(
    "/session",
    summary="获取当前登录会话",
    description="读取当前 Cookie，会话有效时返回当前用户和到期时间；否则返回未认证。",
    response_model=ApiResponse[AuthSessionInfoResponse],
)
async def get_session_info(
    auth_session_token: str | None = Cookie(
        default=None,
        alias=settings.user_session_cookie_name,
        description="用户会话 Cookie。",
    ),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[Any]:
    identity = await get_current_user_from_cookie(session, auth_session_token)
    if identity is None:
        return ApiResponse.ok(data=_build_session_response(authenticated=False))

    user = await UserAccountRepo(session).get_with_roles(identity.user_id)
    if user is None:
        return ApiResponse.ok(data=_build_session_response(authenticated=False))

    return ApiResponse.ok(data=_build_session_response(user=user, expires_at=identity.expires_at, authenticated=True))


@router.post(
    "/logout",
    summary="退出登录",
    description="撤销当前会话并清理浏览器 Cookie。",
    response_model=ApiResponse[dict[str, bool]],
)
async def logout(
    response: Response,
    auth_session_token: str | None = Cookie(
        default=None,
        alias=settings.user_session_cookie_name,
        description="用户会话 Cookie。",
    ),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[Any]:
    await revoke_auth_session(session, auth_session_token)
    await session.commit()
    response.delete_cookie(
        key=settings.user_session_cookie_name,
        path="/",
        secure=settings.user_session_cookie_secure,
        samesite="lax",
    )
    return ApiResponse.ok(data={"ok": True})
