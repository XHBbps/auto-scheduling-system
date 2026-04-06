from datetime import date

import pytest

from app.models import WorkCalendar


@pytest.mark.asyncio
async def test_db_session_works(db_session):
    cal = WorkCalendar(calendar_date=date(2026, 1, 1), is_workday=False, remark="元旦")
    db_session.add(cal)
    await db_session.commit()
    await db_session.refresh(cal)
    assert cal.id is not None
    assert cal.calendar_date == date(2026, 1, 1)
    assert cal.is_workday is False
