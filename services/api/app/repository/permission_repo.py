from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission
from app.repository.base import BaseRepository


class PermissionRepo(BaseRepository[Permission]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Permission)

    async def find_by_code(self, code: str) -> Permission | None:
        result = await self.session.execute(select(Permission).where(Permission.code == code).limit(1))
        return result.scalar_one_or_none()

    async def find_by_codes(self, codes: list[str]) -> list[Permission]:
        if not codes:
            return []
        result = await self.session.execute(select(Permission).where(Permission.code.in_(codes)))
        return list(result.scalars().all())

    async def list_all_ordered(self) -> list[Permission]:
        result = await self.session.execute(
            select(Permission).order_by(Permission.module_name.asc(), Permission.sort_order.asc(), Permission.id.asc())
        )
        return list(result.scalars().all())
