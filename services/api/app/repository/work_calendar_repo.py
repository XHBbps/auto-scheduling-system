from datetime import date
from typing import Sequence
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work_calendar import WorkCalendar
from app.repository.base import BaseRepository


class WorkCalendarRepo(BaseRepository[WorkCalendar]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WorkCalendar)

    async def get_calendar_map(self, start: date, end: date) -> dict[date, bool]:
        stmt = select(WorkCalendar).where(
            and_(
                WorkCalendar.calendar_date >= start,
                WorkCalendar.calendar_date <= end,
            )
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return {r.calendar_date: r.is_workday for r in rows}

    async def upsert(self, calendar_date: date, is_workday: bool, remark: str | None = None) -> WorkCalendar:
        stmt = select(WorkCalendar).where(WorkCalendar.calendar_date == calendar_date)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.is_workday = is_workday
            existing.remark = remark
            await self.session.flush()
            return existing
        entity = WorkCalendar(calendar_date=calendar_date, is_workday=is_workday, remark=remark)
        return await self.add(entity)

    async def get_by_month(self, year: int, month: int) -> Sequence[WorkCalendar]:
        from calendar import monthrange
        _, last_day = monthrange(year, month)
        start = date(year, month, 1)
        end = date(year, month, last_day)
        stmt = select(WorkCalendar).where(
            and_(
                WorkCalendar.calendar_date >= start,
                WorkCalendar.calendar_date <= end,
            )
        ).order_by(WorkCalendar.calendar_date)
        result = await self.session.execute(stmt)
        return result.scalars().all()
