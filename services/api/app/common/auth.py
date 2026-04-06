from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyCookie
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utc_now
from app.config import settings
from app.database import get_session
from app.repository.user_session_repo import UserSessionRepo

AUTH_SESSION_SECURITY_SCHEME_NAME = "UserSessionCookie"


auth_session_cookie_scheme = APIKeyCookie(
    name=settings.user_session_cookie_name,
    scheme_name=AUTH_SESSION_SECURITY_SCHEME_NAME,
    description=(
        f"用户登录成功后写入浏览器的会话 Cookie。调用受保护接口时请携带 `{settings.user_session_cookie_name}`。"
    ),
    auto_error=False,
)


@dataclass(slots=True)
class CurrentUserIdentity:
    user_id: int | None
    username: str | None
    display_name: str
    role_codes: tuple[str, ...]
    role_names: tuple[str, ...]
    permission_codes: tuple[str, ...]
    session_id: int | None
    expires_at: datetime
    auth_source: str = "user_session"

    @property
    def operator_name(self) -> str:
        return self.display_name

    @property
    def is_admin(self) -> bool:
        return "admin" in self.role_codes

    def has_permission(self, permission_code: str) -> bool:
        normalized = permission_code.strip().lower()
        if not normalized:
            return False
        return self.is_admin or normalized in self.permission_codes


def ensure_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def serialize_auth_datetime(value: datetime | None) -> str | None:
    normalized = ensure_utc_datetime(value)
    if normalized is None:
        return None
    return normalized.isoformat().replace("+00:00", "Z")


def hash_session_token(session_token: str) -> str:
    return hashlib.sha256(session_token.encode("utf-8")).hexdigest()


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def build_auth_session_cookie_kwargs() -> dict[str, object]:
    max_age = max(settings.user_session_ttl_minutes, 1) * 60
    return {
        "key": settings.user_session_cookie_name,
        "httponly": True,
        "samesite": "lax",
        "secure": settings.user_session_cookie_secure,
        "max_age": max_age,
        "path": "/",
    }


async def get_current_user_from_cookie(
    session: AsyncSession,
    auth_session_token: str | None,
) -> CurrentUserIdentity | None:
    if not auth_session_token:
        return None

    user_session = await UserSessionRepo(session).find_active_by_token(auth_session_token)
    if user_session and user_session.user and user_session.user.is_active:
        role_pairs = sorted(
            {
                (link.role.code, link.role.name)
                for link in user_session.user.role_links
                if getattr(link, "role", None) is not None and getattr(link.role, "is_active", True)
            }
        )
        permission_codes = sorted(
            {
                link.permission.code
                for role_link in user_session.user.role_links
                if getattr(role_link, "role", None) is not None and getattr(role_link.role, "is_active", True)
                for link in getattr(role_link.role, "permission_links", [])
                if getattr(link, "permission", None) is not None and getattr(link.permission, "is_active", True)
            }
        )
        return CurrentUserIdentity(
            user_id=user_session.user.id,
            username=user_session.user.username,
            display_name=user_session.user.display_name,
            role_codes=tuple(code for code, _ in role_pairs),
            role_names=tuple(name for _, name in role_pairs),
            permission_codes=tuple(permission_codes),
            session_id=user_session.id,
            expires_at=ensure_utc_datetime(user_session.expires_at) or ensure_utc_datetime(utc_now()) or utc_now(),
            auth_source="user_session",
        )
    return None


async def require_authenticated_user(
    session: AsyncSession = Depends(get_session),
    auth_session_token: str | None = Security(auth_session_cookie_scheme),
) -> CurrentUserIdentity:
    identity = await get_current_user_from_cookie(session, auth_session_token)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User session is invalid or expired.",
        )
    return identity


async def require_admin_role(
    identity: CurrentUserIdentity = Depends(require_authenticated_user),
) -> CurrentUserIdentity:
    if not identity.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Current user does not have the required role.",
        )
    return identity


def require_permission(permission_code: str):
    normalized_permission_code = permission_code.strip().lower()

    async def dependency(
        identity: CurrentUserIdentity = Depends(require_authenticated_user),
    ) -> CurrentUserIdentity:
        if not identity.has_permission(normalized_permission_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Current user does not have the required permission.",
            )
        return identity

    dependency.__name__ = f"require_permission_{normalized_permission_code.replace('.', '_')}"
    dependency.__permission_dependency__ = True
    dependency.__required_permission_codes__ = (normalized_permission_code,)
    return dependency


async def revoke_auth_session(
    session: AsyncSession,
    auth_session_token: str | None,
) -> None:
    if not auth_session_token:
        return

    user_session = await UserSessionRepo(session).find_active_by_token(auth_session_token)
    if user_session is not None:
        user_session.revoked_at = utc_now()
        await session.flush()


def build_auth_session_expiry() -> datetime:
    return utc_now() + timedelta(minutes=max(settings.user_session_ttl_minutes, 1))
