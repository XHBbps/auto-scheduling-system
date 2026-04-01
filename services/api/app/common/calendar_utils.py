import math
from datetime import date, timedelta

MAX_WORKDAY_ITERATIONS = 1000


def _is_workday(d: date, calendar: dict[date, bool]) -> bool:
    if d in calendar:
        return calendar[d]
    return d.weekday() < 5  # fallback: Mon-Fri


def subtract_workdays(from_date: date, n: int | float, calendar: dict[date, bool]) -> date:
    """从 from_date 往前减 n 个工作日。n 为小数时向上取整。"""
    days = math.ceil(n) if isinstance(n, float) else n
    if days <= 0:
        return from_date
    current = from_date
    count = 0
    iterations = 0
    while count < days:
        current -= timedelta(days=1)
        if _is_workday(current, calendar):
            count += 1
        iterations += 1
        if iterations > MAX_WORKDAY_ITERATIONS:
            break
    return current


def add_workdays(from_date: date, n: int | float, calendar: dict[date, bool]) -> date:
    """从 from_date 往后加 n 个工作日。n 为小数时向上取整。"""
    days = math.ceil(n) if isinstance(n, float) else n
    if days <= 0:
        return from_date
    current = from_date
    count = 0
    iterations = 0
    while count < days:
        current += timedelta(days=1)
        if _is_workday(current, calendar):
            count += 1
        iterations += 1
        if iterations > MAX_WORKDAY_ITERATIONS:
            break
    return current
