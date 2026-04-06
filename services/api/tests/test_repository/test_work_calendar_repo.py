from datetime import date

import pytest

from app.models import WorkCalendar
from app.repository.work_calendar_repo import WorkCalendarRepo


@pytest.mark.asyncio
async def test_get_calendar_map(db_session):
    db_session.add_all(
        [
            WorkCalendar(calendar_date=date(2026, 4, 1), is_workday=True),
            WorkCalendar(calendar_date=date(2026, 4, 4), is_workday=False, remark="Sat"),
            WorkCalendar(calendar_date=date(2026, 4, 5), is_workday=True, remark="调休"),
        ]
    )
    await db_session.commit()

    repo = WorkCalendarRepo(db_session)
    cal_map = await repo.get_calendar_map(date(2026, 4, 1), date(2026, 4, 5))
    assert cal_map[date(2026, 4, 1)] is True
    assert cal_map[date(2026, 4, 4)] is False
    assert cal_map[date(2026, 4, 5)] is True


@pytest.mark.asyncio
async def test_upsert_calendar(db_session):
    repo = WorkCalendarRepo(db_session)
    await repo.upsert(date(2026, 1, 1), is_workday=False, remark="元旦")
    await db_session.commit()

    cal_map = await repo.get_calendar_map(date(2026, 1, 1), date(2026, 1, 1))
    assert cal_map[date(2026, 1, 1)] is False

    # upsert again — change to workday
    await repo.upsert(date(2026, 1, 1), is_workday=True, remark="调休")
    await db_session.commit()

    cal_map = await repo.get_calendar_map(date(2026, 1, 1), date(2026, 1, 1))
    assert cal_map[date(2026, 1, 1)] is True


@pytest.mark.asyncio
async def test_get_month(db_session):
    db_session.add_all(
        [
            WorkCalendar(calendar_date=date(2026, 3, 1), is_workday=True),
            WorkCalendar(calendar_date=date(2026, 3, 15), is_workday=True),
            WorkCalendar(calendar_date=date(2026, 4, 1), is_workday=True),
        ]
    )
    await db_session.commit()

    repo = WorkCalendarRepo(db_session)
    items = await repo.get_by_month(2026, 3)
    assert len(items) == 2
