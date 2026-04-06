from collections.abc import Sequence
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sales_plan import SalesPlanOrderLineSrc
from app.repository.base import BaseRepository


class SalesPlanRepo(BaseRepository[SalesPlanOrderLineSrc]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, SalesPlanOrderLineSrc)

    async def upsert_by_sap_key(self, sap_code: str, sap_line_no: str, data: dict[str, Any]) -> SalesPlanOrderLineSrc:
        stmt = select(SalesPlanOrderLineSrc).where(
            and_(
                SalesPlanOrderLineSrc.sap_code == sap_code,
                SalesPlanOrderLineSrc.sap_line_no == sap_line_no,
            )
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            await self.session.flush()
            return existing
        entity = SalesPlanOrderLineSrc(sap_code=sap_code, sap_line_no=sap_line_no, **data)
        return await self.add(entity)

    async def find_by_detail_id(self, detail_id: str) -> SalesPlanOrderLineSrc | None:
        stmt = select(SalesPlanOrderLineSrc).where(SalesPlanOrderLineSrc.detail_id == detail_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_ids(self, ids: Sequence[int]) -> Sequence[SalesPlanOrderLineSrc]:
        unique_ids = list(dict.fromkeys(int(item_id) for item_id in ids))
        if not unique_ids:
            return []
        stmt = (
            select(SalesPlanOrderLineSrc)
            .where(SalesPlanOrderLineSrc.id.in_(unique_ids))
            .order_by(SalesPlanOrderLineSrc.id.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def paginate(
        self, page_no: int = 1, page_size: int = 20, **filters: Any
    ) -> tuple[Sequence[SalesPlanOrderLineSrc], int]:
        base = select(SalesPlanOrderLineSrc)
        count_stmt = select(func.count()).select_from(SalesPlanOrderLineSrc)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = base.offset((page_no - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        return items, total
