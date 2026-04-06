from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utc_now
from app.config import settings
from app.models.sync_scheduler_state import SyncSchedulerState
from app.repository.base import BaseRepository


class SyncSchedulerStateRepo(BaseRepository[SyncSchedulerState]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, SyncSchedulerState)

    async def get_singleton(self) -> SyncSchedulerState:
        entity = await self.session.get(SyncSchedulerState, 1)
        if entity is not None:
            return entity
        entity = SyncSchedulerState(
            id=1,
            enabled=settings.sync_scheduler_enabled,
            last_state="stopped",
            heartbeat_at=None,
            updated_by="bootstrap",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.session.add(entity)
        await self.session.flush()
        return entity
