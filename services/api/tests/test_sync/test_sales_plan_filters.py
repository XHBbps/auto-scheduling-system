from datetime import datetime

import pytest

from app.sync.sales_plan_filters import (
    build_sales_plan_filter_window,
    format_sales_plan_filter_window,
)


def test_build_sales_plan_filter_window_defaults_to_configured_window(monkeypatch):
    monkeypatch.setattr("app.sync.sales_plan_filters.settings.sync_window_days", 15)

    window = build_sales_plan_filter_window(now=datetime(2026, 3, 21, 8, 30, 0))

    assert window.start_time == datetime(2026, 3, 6, 8, 30, 0)
    assert window.end_time == datetime(2026, 3, 21, 8, 30, 0)
    assert window.filter_payload == {
        "combineType": "AND",
        "conditions": [
            {
                "type": "condition",
                "value": {"name": "订单明细-确认交货期", "filterType": "NOT_NULL"},
            },
            {
                "type": "condition",
                "value": {
                    "name": "订单主表-创建时间（时分秒）",
                    "filterType": "GE",
                    "filterValue": ["2026-03-06 08:30:00"],
                },
            },
            {
                "type": "condition",
                "value": {
                    "name": "订单主表-创建时间（时分秒）",
                    "filterType": "LT",
                    "filterValue": ["2026-03-21 08:30:00"],
                },
            },
        ],
    }


def test_build_sales_plan_filter_window_respects_manual_range():
    window = build_sales_plan_filter_window(
        start_time=datetime(2026, 3, 1, 0, 0, 0),
        end_time=datetime(2026, 3, 10, 12, 0, 0),
    )

    assert window.start_time == datetime(2026, 3, 1, 0, 0, 0)
    assert window.end_time == datetime(2026, 3, 10, 12, 0, 0)
    assert window.filter_payload["conditions"][1]["value"]["filterValue"] == ["2026-03-01 00:00:00"]
    assert window.filter_payload["conditions"][2]["value"]["filterValue"] == ["2026-03-10 12:00:00"]


def test_build_sales_plan_filter_window_rejects_invalid_range():
    with pytest.raises(ValueError, match="start_time 必须早于 end_time"):
        build_sales_plan_filter_window(
            start_time=datetime(2026, 3, 10, 12, 0, 0),
            end_time=datetime(2026, 3, 10, 12, 0, 0),
        )


def test_format_sales_plan_filter_window():
    window = build_sales_plan_filter_window(
        start_time=datetime(2026, 3, 1, 0, 0, 0),
        end_time=datetime(2026, 3, 10, 12, 0, 0),
    )

    assert (
        format_sales_plan_filter_window(window)
        == "确认交货期非空；创建时间>=2026-03-01 00:00:00；创建时间<2026-03-10 12:00:00"
    )
