from datetime import UTC, datetime


def utc_now() -> datetime:
    """返回当前 UTC 时间（naive，无 tzinfo）。全系统唯一的时间获取入口。"""
    return datetime.now(UTC).replace(tzinfo=None)


def to_utc_naive(value: datetime) -> datetime:
    """任意 datetime 转为 UTC naive。naive 输入视为已是 UTC。"""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)
