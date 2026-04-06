from datetime import datetime
from decimal import Decimal

import pytest

from app.models.order_schedule_snapshot import OrderScheduleSnapshot


@pytest.mark.asyncio
async def test_update_work_calendar(app_client):
    resp = await app_client.post(
        "/api/admin/work-calendar",
        json={
            "items": [
                {"calendar_date": "2026-04-05", "is_workday": False, "remark": "清明节"},
                {"calendar_date": "2026-04-12", "is_workday": True, "remark": "调休上班"},
            ]
        },
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["updated_count"] == 2


@pytest.mark.asyncio
async def test_get_work_calendar_by_month(app_client):
    # first insert data
    await app_client.post(
        "/api/admin/work-calendar", json={"items": [{"calendar_date": "2026-04-05", "is_workday": False}]}
    )

    resp = await app_client.get("/api/admin/work-calendar?month=2026-04")
    body = resp.json()
    assert body["code"] == 0
    assert len(body["data"]) >= 1


@pytest.mark.asyncio
async def test_get_work_calendar_all(app_client):
    resp = await app_client.get("/api/admin/work-calendar")
    body = resp.json()
    assert body["code"] == 0


@pytest.mark.asyncio
async def test_get_work_calendar_distribution(app_client, db_session):
    db_session.add_all(
        [
            OrderScheduleSnapshot(
                order_line_id=1001,
                contract_no="HT1001",
                order_no="SO1001",
                product_model="MC-100",
                material_no="MAT-1001",
                quantity=Decimal("2"),
                confirmed_delivery_date=datetime(2026, 4, 10, 8, 0, 0),
                trigger_date=datetime(2026, 4, 7, 9, 0, 0),
                planned_start_date=datetime(2026, 4, 8, 10, 0, 0),
                schedule_status="scheduled",
                drawing_released=True,
            ),
            OrderScheduleSnapshot(
                order_line_id=1002,
                contract_no="HT1002",
                order_no="SO1002",
                product_model="MC-200",
                material_no="MAT-1002",
                quantity=Decimal("3"),
                confirmed_delivery_date=datetime(2026, 4, 10, 18, 0, 0),
                trigger_date=datetime(2026, 4, 7, 12, 0, 0),
                planned_start_date=datetime(2026, 4, 8, 15, 0, 0),
                schedule_status="pending_trigger",
                drawing_released=True,
            ),
            OrderScheduleSnapshot(
                order_line_id=1003,
                contract_no="HT1003",
                order_no="SO1003",
                product_model="MC-300",
                material_no="MAT-1003",
                quantity=None,
                confirmed_delivery_date=datetime(2026, 4, 11, 8, 0, 0),
                trigger_date=datetime(2026, 4, 8, 9, 0, 0),
                planned_start_date=None,
                schedule_status="schedulable",
                drawing_released=True,
            ),
        ]
    )
    await db_session.commit()

    resp = await app_client.get("/api/admin/work-calendar/distribution?month=2026-04")
    body = resp.json()

    assert body["code"] == 0
    assert len(body["data"]) == 30

    day_map = {item["calendar_date"]: item for item in body["data"]}
    assert day_map["2026-04-10"]["delivery_order_count"] == 2
    assert day_map["2026-04-10"]["delivery_quantity_sum"] == "5.0000"
    assert day_map["2026-04-07"]["trigger_order_count"] == 2
    assert day_map["2026-04-08"]["planned_start_order_count"] == 2
    assert day_map["2026-04-11"]["delivery_order_count"] == 1
    assert day_map["2026-04-11"]["delivery_quantity_sum"] == "0.0000"
    assert day_map["2026-04-01"]["delivery_order_count"] == 0
    assert day_map["2026-04-01"]["trigger_quantity_sum"] == "0"


@pytest.mark.asyncio
async def test_get_work_calendar_day_detail(app_client, db_session):
    db_session.add_all(
        [
            OrderScheduleSnapshot(
                order_line_id=1101,
                contract_no="HT1101",
                order_no="SO1101",
                product_model="MC-1101",
                material_no="MAT-1101",
                quantity=Decimal("1"),
                confirmed_delivery_date=datetime(2026, 4, 15, 9, 0, 0),
                trigger_date=datetime(2026, 4, 15, 8, 0, 0),
                planned_start_date=datetime(2026, 4, 15, 7, 0, 0),
                schedule_status="scheduled",
                drawing_released=True,
            ),
            OrderScheduleSnapshot(
                order_line_id=1102,
                contract_no="HT1102",
                order_no="SO1102",
                product_model="MC-1102",
                material_no="MAT-1102",
                quantity=Decimal("2"),
                confirmed_delivery_date=datetime(2026, 4, 15, 20, 0, 0),
                trigger_date=datetime(2026, 4, 14, 8, 0, 0),
                planned_start_date=datetime(2026, 4, 15, 13, 0, 0),
                schedule_status="pending_trigger",
                drawing_released=True,
            ),
        ]
    )
    await db_session.commit()

    resp = await app_client.get("/api/admin/work-calendar/day-detail?date=2026-04-15")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["summary"]["calendar_date"] == "2026-04-15"
    assert body["data"]["summary"]["delivery_order_count"] == 2
    assert body["data"]["summary"]["delivery_quantity_sum"] == "3.0000"
    assert body["data"]["summary"]["trigger_order_count"] == 1
    assert body["data"]["summary"]["planned_start_order_count"] == 2
    assert [item["order_line_id"] for item in body["data"]["delivery_orders"]] == [1101, 1102]
    assert [item["order_line_id"] for item in body["data"]["trigger_orders"]] == [1101]
    assert [item["order_line_id"] for item in body["data"]["planned_start_orders"]] == [1101, 1102]
