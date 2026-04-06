from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.background_task import BackgroundTask
from app.models.bom_relation import BomRelationSrc
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.part_cycle_baseline import PartCycleBaseline
from app.models.sales_plan import SalesPlanOrderLineSrc


@pytest.mark.asyncio
async def test_list_part_cycle_baselines_returns_part_type_and_plant(app_client):
    save_resp = await app_client.post(
        "/api/admin/part-cycle-baselines",
        json={
            "part_type": "右导轨总成",
            "material_desc": "右导轨总成MC1-25.1-13",
            "machine_model": "MC1-80",
            "plant": "1000",
            "ref_batch_qty": 1,
            "cycle_days": 12,
            "unit_cycle_days": 12,
            "is_active": True,
        },
    )

    assert save_resp.json()["code"] == 0

    list_resp = await app_client.get("/api/admin/part-cycle-baselines?part_type=右导轨总成&plant=1000")
    body = list_resp.json()

    assert body["code"] == 0
    assert len(body["data"]) == 1
    assert body["data"][0]["part_type"] == "右导轨总成"
    assert body["data"][0]["material_no"] == "右导轨总成"
    assert body["data"][0]["plant"] == "1000"
    assert body["data"][0]["sample_count"] == 0


@pytest.mark.asyncio
async def test_save_part_cycle_baseline_extracts_part_type_from_material_desc(app_client):
    resp = await app_client.post(
        "/api/admin/part-cycle-baselines",
        json={
            "material_desc": "左导轨总成MC1-25.1-15",
            "machine_model": "MC1-80",
            "plant": "1000",
            "ref_batch_qty": 1,
            "cycle_days": 15,
            "unit_cycle_days": 15,
            "is_active": True,
        },
    )
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["part_type"] == "左导轨总成"
    assert body["data"]["material_no"] == "左导轨总成"


@pytest.mark.asyncio
async def test_update_part_cycle_baseline_with_id_does_not_duplicate(app_client):
    create_resp = await app_client.post(
        "/api/admin/part-cycle-baselines",
        json={
            "part_type": "床身焊接件",
            "material_desc": "床身焊接件A版",
            "machine_model": "MC2-100",
            "plant": "1000",
            "ref_batch_qty": 1,
            "cycle_days": 20,
            "unit_cycle_days": 20,
            "is_active": True,
        },
    )
    created = create_resp.json()["data"]

    update_resp = await app_client.post(
        "/api/admin/part-cycle-baselines",
        json={
            "id": created["id"],
            "part_type": "床身焊接件",
            "material_desc": "床身焊接件B版",
            "machine_model": "MC2-100",
            "plant": "1000",
            "ref_batch_qty": 2,
            "cycle_days": 24,
            "unit_cycle_days": 12,
            "is_active": True,
        },
    )
    assert update_resp.json()["code"] == 0

    list_resp = await app_client.get("/api/admin/part-cycle-baselines?part_type=床身焊接件&plant=1000")
    items = list_resp.json()["data"]

    assert len(items) == 1
    assert items[0]["id"] == created["id"]
    assert items[0]["material_desc"] == "床身焊接件B版"
    assert items[0]["cycle_days"] == 24.0
    assert items[0]["cycle_source"] == "manual"


@pytest.mark.asyncio
async def test_save_part_cycle_baseline_triggers_snapshot_refresh(app_client, db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP-PART-1",
        sap_line_no="10",
        order_no="SO-PART-1",
        product_model="MC1-80",
        product_series="MC1",
        material_no="MACH-PART-1",
        delivery_plant="1000",
        quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 4, 1),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
    )
    db_session.add(order)
    db_session.add(
        BomRelationSrc(
            machine_material_no="MACH-PART-1",
            plant="1000",
            material_no="ASM-PART-1",
            bom_component_no="PART-001",
            bom_component_desc="右导轨总成MC1-25.1-13",
            bom_level=3,
            is_self_made=True,
            part_type="自产",
        )
    )
    await db_session.commit()

    resp = await app_client.post(
        "/api/admin/part-cycle-baselines",
        json={
            "part_type": "右导轨总成",
            "material_desc": "右导轨总成MC1-25.1-13",
            "machine_model": "MC1-80",
            "plant": "1000",
            "ref_batch_qty": 1,
            "cycle_days": 10,
            "unit_cycle_days": 10,
            "is_active": True,
        },
    )

    assert resp.json()["code"] == 0

    snapshot = (
        await db_session.execute(select(OrderScheduleSnapshot).where(OrderScheduleSnapshot.order_line_id == order.id))
    ).scalar_one_or_none()

    assert snapshot is not None
    assert snapshot.last_refresh_source == "admin_part_cycle"
    assert snapshot.order_line_id == order.id


@pytest.mark.asyncio
async def test_rebuild_endpoint_enqueues_background_task(app_client, db_session):
    resp = await app_client.post("/api/admin/part-cycle-baselines/rebuild")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["status"] == "queued"

    tasks = (await db_session.execute(select(BackgroundTask))).scalars().all()
    assert len(tasks) == 1
    assert tasks[0].task_type == "part_cycle_baseline_rebuild"
    assert tasks[0].dedupe_key == "baseline_rebuild:part_cycle"


@pytest.mark.asyncio
async def test_save_part_cycle_baseline_normalizes_cycle_precision(app_client):
    create_resp = await app_client.post(
        "/api/admin/part-cycle-baselines",
        json={
            "part_type": "\u5e73\u8861\u7f38",
            "material_desc": "\u5e73\u8861\u7f38\u603b\u6210",
            "machine_model": "MC1-80-PRECISION",
            "plant": "1100",
            "ref_batch_qty": 1,
            "cycle_days": 12.6,
            "unit_cycle_days": 1.26,
            "is_active": True,
        },
    )
    assert create_resp.json()["code"] == 0

    list_resp = await app_client.get(
        "/api/admin/part-cycle-baselines?part_type=\u5e73\u8861\u7f38&machine_model=MC1-80-PRECISION&plant=1100"
    )
    body = list_resp.json()

    assert body["code"] == 0
    assert len(body["data"]) == 1
    assert body["data"][0]["cycle_days"] == 13.0
    assert body["data"][0]["unit_cycle_days"] == 1.3


@pytest.mark.asyncio
async def test_list_part_cycle_baselines_rounds_existing_high_precision_values(app_client, db_session):
    db_session.add(
        PartCycleBaseline(
            material_no="\u5e73\u8861\u7f38",
            material_desc="\u5e73\u8861\u7f38\u603b\u6210",
            core_part_name="\u5e73\u8861\u7f38",
            machine_model="MC1-80-EXISTING",
            plant="1100",
            ref_batch_qty=Decimal("1"),
            cycle_days=Decimal("2.1497"),
            unit_cycle_days=Decimal("0.107485"),
            sample_count=3,
            cycle_source="history",
            match_rule="part_type_exact_with_plant",
            confidence_level="medium",
            is_default=False,
            is_active=True,
        )
    )
    await db_session.commit()

    list_resp = await app_client.get(
        "/api/admin/part-cycle-baselines?part_type=\u5e73\u8861\u7f38&machine_model=MC1-80-EXISTING&plant=1100"
    )
    body = list_resp.json()

    assert body["code"] == 0
    assert len(body["data"]) == 1
    assert body["data"][0]["cycle_days"] == 2.0
    assert body["data"][0]["unit_cycle_days"] == 0.1
