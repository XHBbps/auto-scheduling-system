from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.machine_cycle_history import MachineCycleHistorySrc
from app.repository.base import BaseRepository


class MachineCycleHistoryRepo(BaseRepository[MachineCycleHistorySrc]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, MachineCycleHistorySrc)

    async def upsert_by_detail_id(self, detail_id: str, data: dict[str, Any]) -> MachineCycleHistorySrc:
        stmt = select(MachineCycleHistorySrc).where(MachineCycleHistorySrc.detail_id == detail_id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            await self.session.flush()
            return existing
        entity = MachineCycleHistorySrc(detail_id=detail_id, **data)
        return await self.add(entity)
