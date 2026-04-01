from datetime import date, timedelta
from app.common.calendar_utils import subtract_workdays, add_workdays


def _make_calendar() -> dict[date, bool]:
    """Build a simple calendar: Mon-Fri workday, Sat-Sun off.
    2026-04 starts on Wednesday.
    Override: 2026-04-05 (Sun) is a workday (调休), 2026-04-06 (Mon) is off (清明).
    """
    cal = {}
    d = date(2026, 3, 1)
    end = date(2026, 5, 1)
    while d < end:
        cal[d] = d.weekday() < 5  # Mon-Fri
        d += timedelta(days=1)
    cal[date(2026, 4, 5)] = True   # Sunday override: workday
    cal[date(2026, 4, 6)] = False  # Monday override: holiday
    return cal


def test_subtract_workdays_no_weekends():
    cal = _make_calendar()
    # 2026-04-10 (Fri) - 3 workdays = 2026-04-07 (Tue)
    result = subtract_workdays(date(2026, 4, 10), 3, cal)
    assert result == date(2026, 4, 7)


def test_subtract_workdays_across_holiday():
    cal = _make_calendar()
    # 2026-04-10 (Fri) - 5 workdays
    # 4/9(Thu) 4/8(Wed) 4/7(Tue) 4/5(Sun=work) 4/3(Fri)
    # Skip 4/6(Mon=holiday) and 4/4(Sat=off)
    result = subtract_workdays(date(2026, 4, 10), 5, cal)
    assert result == date(2026, 4, 3)


def test_subtract_zero_workdays():
    cal = _make_calendar()
    result = subtract_workdays(date(2026, 4, 10), 0, cal)
    assert result == date(2026, 4, 10)


def test_add_workdays_basic():
    cal = _make_calendar()
    # 2026-04-01 (Wed) + 3 workdays
    # 4/2(Thu) 4/3(Fri) 4/5(Sun=work) → result is 4/5
    result = add_workdays(date(2026, 4, 1), 3, cal)
    assert result == date(2026, 4, 5)


def test_add_zero_workdays():
    cal = _make_calendar()
    result = add_workdays(date(2026, 4, 1), 0, cal)
    assert result == date(2026, 4, 1)
