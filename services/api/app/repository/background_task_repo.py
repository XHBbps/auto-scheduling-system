from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utc_now
from app.common.enums import BackgroundTaskStatus
from app.models.background_task import BackgroundTask
from app.repository.base import BaseRepository


class BackgroundTaskRepo(BaseRepository[BackgroundTask]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, BackgroundTask)

    async def get_active_by_dedupe_key(self, dedupe_key: str | None) -> BackgroundTask | None:
        if not dedupe_key:
            return None
        stmt = (
            select(BackgroundTask)
            .where(
                BackgroundTask.dedupe_key == dedupe_key,
                BackgroundTask.status.in_([BackgroundTaskStatus.PENDING.value, BackgroundTaskStatus.RUNNING.value]),
            )
            .order_by(BackgroundTask.id.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def claim_available(self, *, worker_id: str, limit: int) -> list[BackgroundTask]:
        now = utc_now()
        stmt = (
            select(BackgroundTask)
            .where(
                BackgroundTask.status == BackgroundTaskStatus.PENDING.value,
                BackgroundTask.available_at <= now,
            )
            .order_by(BackgroundTask.available_at.asc(), BackgroundTask.id.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        tasks = (await self.session.execute(stmt)).scalars().all()
        for task in tasks:
            task.status = BackgroundTaskStatus.RUNNING.value
            task.claimed_at = now
            task.worker_id = worker_id
            task.attempt_count = int(task.attempt_count or 0) + 1
        await self.session.flush()
        return list(tasks)

    async def list_stale_running(self, *, stale_before: datetime) -> list[BackgroundTask]:
        stmt = select(BackgroundTask).where(
            BackgroundTask.status == BackgroundTaskStatus.RUNNING.value,
            BackgroundTask.claimed_at.is_not(None),
            BackgroundTask.claimed_at <= stale_before,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_dead_letter(self) -> int:
        stmt = (
            select(func.count())
            .select_from(BackgroundTask)
            .where(
                BackgroundTask.status == BackgroundTaskStatus.FAILED.value,
                BackgroundTask.dead_at.is_not(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
