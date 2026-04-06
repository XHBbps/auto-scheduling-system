import hashlib
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.datetime_utils import utc_now
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user_account import UserAccount
from app.models.user_role import UserRole
from app.models.user_session import UserSession
from app.repository.base import BaseRepository


class UserSessionRepo(BaseRepository[UserSession]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, UserSession)

    async def find_active_by_token(self, session_token: str, now: datetime | None = None) -> UserSession | None:
        current_time = now or utc_now()
        if current_time.tzinfo is not None:
            current_time = current_time.astimezone(UTC).replace(tzinfo=None)
        token_hash = hashlib.sha256(session_token.encode("utf-8")).hexdigest()
        result = await self.session.execute(
            select(UserSession)
            .options(
                selectinload(UserSession.user)
                .selectinload(UserAccount.role_links)
                .selectinload(UserRole.role)
                .selectinload(Role.permission_links)
                .selectinload(RolePermission.permission)
            )
            .where(
                UserSession.session_token_hash == token_hash,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > current_time,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def revoke_active_sessions_for_user(
        self,
        user_id: int,
        *,
        revoked_at: datetime | None = None,
        exclude_session_id: int | None = None,
        now: datetime | None = None,
    ) -> int:
        current_time = now or utc_now()
        if current_time.tzinfo is not None:
            current_time = current_time.astimezone(UTC).replace(tzinfo=None)
        revoked_time = revoked_at or current_time
        if revoked_time.tzinfo is not None:
            revoked_time = revoked_time.astimezone(UTC).replace(tzinfo=None)

        stmt = (
            update(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > current_time,
            )
            .values(revoked_at=revoked_time)
        )
        if exclude_session_id is not None:
            stmt = stmt.where(UserSession.id != exclude_session_id)

        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)
