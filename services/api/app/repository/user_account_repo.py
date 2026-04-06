from sqlalchemy import distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user_account import UserAccount
from app.models.user_role import UserRole
from app.repository.base import BaseRepository

_USER_WITH_ROLES_OPTIONS = (
    selectinload(UserAccount.role_links)
    .selectinload(UserRole.role)
    .selectinload(Role.permission_links)
    .selectinload(RolePermission.permission),
)


class UserAccountRepo(BaseRepository[UserAccount]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, UserAccount)

    async def find_by_username(self, username: str, with_roles: bool = False) -> UserAccount | None:
        stmt = (
            select(UserAccount)
            .execution_options(populate_existing=True)
            .where(func.lower(UserAccount.username) == username.strip().lower())
            .limit(1)
        )
        if with_roles:
            stmt = stmt.options(*_USER_WITH_ROLES_OPTIONS)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_roles(self, user_id: int) -> UserAccount | None:
        result = await self.session.execute(
            select(UserAccount)
            .execution_options(populate_existing=True)
            .options(*_USER_WITH_ROLES_OPTIONS)
            .where(UserAccount.id == user_id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def is_username_taken(self, username: str, exclude_user_id: int | None = None) -> bool:
        stmt = select(UserAccount.id).where(func.lower(UserAccount.username) == username.strip().lower()).limit(1)
        if exclude_user_id is not None:
            stmt = stmt.where(UserAccount.id != exclude_user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_with_roles(
        self,
        *,
        keyword: str | None = None,
        role_code: str | None = None,
        is_active: bool | None = None,
        page_no: int = 1,
        page_size: int = 20,
    ) -> tuple[list[UserAccount], int]:
        stmt = select(UserAccount).execution_options(populate_existing=True).options(*_USER_WITH_ROLES_OPTIONS)
        count_stmt = select(func.count(distinct(UserAccount.id))).select_from(UserAccount)

        if role_code:
            stmt = stmt.join(UserAccount.role_links).join(UserRole.role).where(Role.code == role_code)
            count_stmt = (
                count_stmt.join(UserRole, UserRole.user_id == UserAccount.id)
                .join(Role, Role.id == UserRole.role_id)
                .where(Role.code == role_code)
            )

        if keyword:
            normalized_keyword = f"%{keyword.strip().lower()}%"
            keyword_condition = or_(
                func.lower(UserAccount.username).like(normalized_keyword),
                func.lower(UserAccount.display_name).like(normalized_keyword),
            )
            stmt = stmt.where(keyword_condition)
            count_stmt = count_stmt.where(keyword_condition)

        if is_active is not None:
            stmt = stmt.where(UserAccount.is_active == is_active)
            count_stmt = count_stmt.where(UserAccount.is_active == is_active)

        total = (await self.session.execute(count_stmt)).scalar_one()
        result = await self.session.execute(
            stmt.order_by(UserAccount.created_at.desc(), UserAccount.id.desc())
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total
