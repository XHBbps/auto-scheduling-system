from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole
from app.repository.base import BaseRepository


class RoleRepo(BaseRepository[Role]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Role)

    async def find_by_code(self, code: str) -> Role | None:
        result = await self.session.execute(select(Role).where(Role.code == code).limit(1))
        return result.scalar_one_or_none()

    async def get_with_permissions(self, role_id: int) -> Role | None:
        result = await self.session.execute(
            select(Role)
            .options(selectinload(Role.permission_links).selectinload(RolePermission.permission))
            .execution_options(populate_existing=True)
            .where(Role.id == role_id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def find_by_codes(self, codes: list[str]) -> list[Role]:
        if not codes:
            return []
        result = await self.session.execute(select(Role).where(Role.code.in_(codes)))
        return list(result.scalars().all())

    async def list_with_permissions(self, include_inactive: bool = True) -> list[Role]:
        stmt = (
            select(Role)
            .options(selectinload(Role.permission_links).selectinload(RolePermission.permission))
            .order_by(Role.is_system.desc(), Role.created_at.asc(), Role.id.asc())
        )
        if not include_inactive:
            stmt = stmt.where(Role.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_assigned_users(self, role_ids: list[int]) -> dict[int, int]:
        if not role_ids:
            return {}
        result = await self.session.execute(
            select(UserRole.role_id, func.count(UserRole.user_id))
            .where(UserRole.role_id.in_(role_ids))
            .group_by(UserRole.role_id)
        )
        return {role_id: count for role_id, count in result.all()}

    async def count_permissions(self, role_ids: list[int]) -> dict[int, int]:
        if not role_ids:
            return {}
        result = await self.session.execute(
            select(RolePermission.role_id, func.count(RolePermission.permission_id))
            .where(RolePermission.role_id.in_(role_ids))
            .group_by(RolePermission.role_id)
        )
        return {role_id: count for role_id, count in result.all()}
