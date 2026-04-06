"""Initialize work calendar for 2026-2027. Run once after DB setup.

Usage: python -m scripts.init_work_calendar
"""

import asyncio
from datetime import date, timedelta

from app.database import async_session_factory, engine
from app.models.base import Base
from app.models.work_calendar import WorkCalendar


async def init_calendar():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        start = date(2026, 1, 1)
        end = date(2027, 12, 31)
        current = start
        batch = []
        while current <= end:
            batch.append(
                WorkCalendar(
                    calendar_date=current,
                    is_workday=current.weekday() < 5,
                    remark=None,
                )
            )
            current += timedelta(days=1)

        session.add_all(batch)
        await session.commit()
        print(f"Initialized {len(batch)} calendar days ({start} to {end})")


if __name__ == "__main__":
    asyncio.run(init_calendar())
