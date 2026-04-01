from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.config import settings

_GUANDATA_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
_DELIVERY_DATE_FIELD = "订单明细-确认交货期"
_CREATED_TIME_FIELD = "订单主表-创建时间（时分秒）"


@dataclass(frozen=True)
class SalesPlanFilterWindow:
    start_time: datetime
    end_time: datetime
    filter_payload: dict[str, Any]


def build_sales_plan_filter_window(
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    window_days: int | None = None,
    now: datetime | None = None,
) -> SalesPlanFilterWindow:
    timezone = ZoneInfo(settings.sync_scheduler_timezone)
    resolved_now = _normalize_datetime(now, timezone) if now else datetime.now(timezone).replace(tzinfo=None)
    resolved_end = _normalize_datetime(end_time, timezone) if end_time else resolved_now

    effective_window_days = window_days if window_days is not None else settings.sync_window_days
    if effective_window_days <= 0:
        raise ValueError("销售计划同步窗口天数必须大于 0。")

    resolved_start = (
        _normalize_datetime(start_time, timezone)
        if start_time
        else resolved_end - timedelta(days=effective_window_days)
    )
    if resolved_start >= resolved_end:
        raise ValueError("销售计划同步时间窗口无效：start_time 必须早于 end_time。")

    return SalesPlanFilterWindow(
        start_time=resolved_start,
        end_time=resolved_end,
        filter_payload={
            "combineType": "AND",
            "conditions": [
                {
                    "type": "condition",
                    "value": {
                        "name": _DELIVERY_DATE_FIELD,
                        "filterType": "NOT_NULL",
                    },
                },
                {
                    "type": "condition",
                    "value": {
                        "name": _CREATED_TIME_FIELD,
                        "filterType": "GE",
                        "filterValue": [resolved_start.strftime(_GUANDATA_DATETIME_FORMAT)],
                    },
                },
                {
                    "type": "condition",
                    "value": {
                        "name": _CREATED_TIME_FIELD,
                        "filterType": "LT",
                        "filterValue": [resolved_end.strftime(_GUANDATA_DATETIME_FORMAT)],
                    },
                },
            ],
        },
    )


def format_sales_plan_filter_window(window: SalesPlanFilterWindow) -> str:
    return (
        f"确认交货期非空；创建时间>={window.start_time.strftime(_GUANDATA_DATETIME_FORMAT)}；"
        f"创建时间<{window.end_time.strftime(_GUANDATA_DATETIME_FORMAT)}"
    )


def _normalize_datetime(value: datetime, timezone: ZoneInfo) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone).replace(tzinfo=None)
    return value
