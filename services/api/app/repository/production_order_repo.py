from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.production_order import ProductionOrderHistorySrc
from app.repository.base import BaseRepository


class ProductionOrderRepo(BaseRepository[ProductionOrderHistorySrc]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ProductionOrderHistorySrc)

    async def upsert_by_order_no(self, production_order_no: str, data: dict[str, Any]) -> ProductionOrderHistorySrc:
        stmt = select(ProductionOrderHistorySrc).where(
            ProductionOrderHistorySrc.production_order_no == production_order_no
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            await self.session.flush()
            return existing
        entity = ProductionOrderHistorySrc(production_order_no=production_order_no, **data)
        return await self.add(entity)
